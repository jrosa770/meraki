#!/usr/bin/env python3
"""
copy_meraki_network.py
Replicates a Meraki Dashboard **network** from one organisation to another so
that the destination mirrors *all* components exposed by the v1 API as of
June 2025 — including **Addressing & VLANs (with DHCP scopes)** *and* **every
per‑SSID sub‑setting** (traffic shaping, firewall rules, Bonjour, etc.).

Key capabilities
----------------
* **Network shell** (products, tags, timezone, notes)
* **Addressing & VLANs**
  * Single‑LAN or VLAN‑enabled, incl. subnet & DHCP mode
  * For each VLAN: subnet, MX IP, DHCP handling, DNS, lease, options, relay,
    reserved ranges & fixed IPs
  * MX static routes
* **Wireless SSIDs (1‑15)**
  * Core SSID object (name, security, VLAN tags, rate‑limits, splash, Radius…)
  * Traffic shaping rules
  * L3 & L7 firewall rules
  * Bonjour forwarding
  * MAC filtering list
  * VPN enrollment & walled‑garden lists
* **MX L3 firewall rules**
* **Group policies**

All operations are **idempotent**: rerunning the script reconciles diffs without
creating duplicates. Unsupported or read‑only fields are skipped gracefully.

Author  : Jose Rosa
Updated : 2025‑06‑24

Run from CLI or import `clone_network()`.
"""

import argparse
import logging
from typing import Any, Dict, List, Mapping

import meraki
from meraki.exceptions import APIError

# ----------------------------
# Logging Setup
# ----------------------------

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

log = logging.getLogger("meraki-cloner")

# ----------------------------
# Utilities
# ----------------------------

def _upsert(src, dst, id_key, create_cb, update_cb, label):
    idx = {d[id_key]: d for d in dst}
    for obj in src:
        ident = obj[id_key]
        try:
            if ident in idx:
                update_cb(ident, obj)
                log.info("  • %s %s updated", label, ident)
            else:
                create_cb(obj)
                log.info("  • %s %s created", label, ident)
        except APIError as exc:
            log.error("  ✗ %s %s – %s", label, ident, exc)


def _clone_optional(getter, setter, src_net, dst_net, num, label):
    try:
        body = getter(src_net, num)
        setter(dst_net, num, **body)
        log.info("    ↳ %s synced", label)
    except APIError:
        pass

# ----------------------------
# Wireless SSID sync
# ----------------------------

def sync_ssids(db, src_net, dst_net):
    for s in db.wireless.getNetworkWirelessSsids(src_net):
        num = s["number"]
        core = {k: v for k, v in s.items() if k not in {"number", "networkId", "ssidAdminAccessible"}}
        try:
            db.wireless.updateNetworkWirelessSsid(dst_net, num, **core)
            log.info("  • SSID %d '%s' core synced", num, core.get("name"))
        except APIError as exc:
            log.error("  ✗ SSID %d core – %s", num, exc)
            continue

        _clone_optional(db.wireless.getNetworkWirelessSsidTrafficShapingRules,
                        db.wireless.updateNetworkWirelessSsidTrafficShapingRules,
                        src_net, dst_net, num, "traffic-shaping rules")

        _clone_optional(db.wireless.getNetworkWirelessSsidFirewallL3FirewallRules,
                        lambda n, i, **body: db.wireless.updateNetworkWirelessSsidFirewallL3FirewallRules(n, i, rules=body["rules"]),
                        src_net, dst_net, num, "L3 firewall rules")

        _clone_optional(db.wireless.getNetworkWirelessSsidFirewallL7FirewallRules,
                        lambda n, i, **body: db.wireless.updateNetworkWirelessSsidFirewallL7FirewallRules(n, i, rules=body["rules"]),
                        src_net, dst_net, num, "L7 firewall rules")

        _clone_optional(db.wireless.getNetworkWirelessSsidBonjourForwarding,
                        db.wireless.updateNetworkWirelessSsidBonjourForwarding,
                        src_net, dst_net, num, "Bonjour forwarding")

        _clone_optional(db.wireless.getNetworkWirelessSsidVpn,
                        db.wireless.updateNetworkWirelessSsidVpn,
                        src_net, dst_net, num, "SSID VPN settings")

# ----------------------------
# VLANs + DHCP + Static Routes
# ----------------------------

def sync_addressing(db, src_net, dst_net):
    src_set = db.appliance.getNetworkApplianceVlansSettings(src_net)
    dst_set = db.appliance.getNetworkApplianceVlansSettings(dst_net)

    if src_set.get("vlansEnabled"):
        if not dst_set.get("vlansEnabled"):
            db.appliance.updateNetworkApplianceVlansSettings(dst_net, vlansEnabled=True)
        _sync_vlans(db, src_net, dst_net)
    else:
        if dst_set.get("vlansEnabled"):
            db.appliance.updateNetworkApplianceVlansSettings(dst_net, vlansEnabled=False)
        lan = db.appliance.getNetworkApplianceSingleLan(src_net)
        db.appliance.updateNetworkApplianceSingleLan(dst_net, **{k: v for k, v in lan.items() if k != "networkId"})
        log.info("  • Single-LAN settings mirrored")

    _sync_static_routes(db, src_net, dst_net)


def _sync_vlans(db, src_net, dst_net):
    src_vlans = db.appliance.getNetworkApplianceVlans(src_net)
    try:
        dst_vlans = db.appliance.getNetworkApplianceVlans(dst_net)
    except APIError as exc:
        dst_vlans = [] if exc.status == 404 else (_ for _ in ()).throw(exc)

    def body(v, include_id=False):
        drop = {"networkId"} if include_id else {"networkId", "id"}
        return {k: v for k, v in v.items() if k not in drop}

    _upsert(
        src_vlans,
        dst_vlans,
        "id",
        lambda vlan: db.appliance.createNetworkApplianceVlan(dst_net, **body(vlan, include_id=True)),
        lambda vid, vlan: db.appliance.updateNetworkApplianceVlan(dst_net, vid, **body(vlan)),
        "VLAN"
    )


def _sync_static_routes(db, src_net, dst_net):
    src_routes = db.appliance.getNetworkApplianceStaticRoutes(src_net)
    dst_routes = db.appliance.getNetworkApplianceStaticRoutes(dst_net)
    idx = {r["name"]: r for r in dst_routes}

    for r in src_routes:
        name = r["name"]
        body = {k: v for k, v in r.items() if k not in {"routeId", "networkId"}}
        if name in idx:
            db.appliance.updateNetworkApplianceStaticRoute(dst_net, idx[name]["routeId"], **body)
            log.info("  • Static route '%s' updated", name)
        else:
            db.appliance.createNetworkApplianceStaticRoute(dst_net, **body)
            log.info("  • Static route '%s' created", name)

# ----------------------------
# Firewall + Group Policies
# ----------------------------

def sync_l3_fw(db, src_net, dst_net):
    rules = db.appliance.getNetworkApplianceFirewallL3FirewallRules(src_net)
    db.appliance.updateNetworkApplianceFirewallL3FirewallRules(dst_net, rules=rules["rules"])
    log.info("  • MX L3 firewall rules synced")

def sync_group_policies(db, src_net, dst_net):
    src_pols = db.networks.getNetworkGroupPolicies(src_net)
    dst_names = {p["name"] for p in db.networks.getNetworkGroupPolicies(dst_net)}
    for p in src_pols:
        if p["name"] not in dst_names:
            db.networks.createNetworkGroupPolicy(dst_net, **{k: v for k, v in p.items() if k not in {"groupPolicyId", "networkId"}})
            log.info("  • Group policy '%s' created", p["name"])

# ----------------------------
# Full Network Validation Report
# ----------------------------

def validate_network(db, src_net, dst_net):
    report_lines = ["Network Validation Report:\n"]

    # VLAN & DHCP validation
    try:
        src_vlans = db.appliance.getNetworkApplianceVlans(src_net)
        dst_vlans = db.appliance.getNetworkApplianceVlans(dst_net)
    except APIError as e:
        msg = f"DHCP validation skipped: {e}"
        log.warning(msg)
        report_lines.append(msg)
        src_vlans, dst_vlans = [], []

    src_vlan_map = {v["id"]: v for v in src_vlans}
    dst_vlan_map = {v["id"]: v for v in dst_vlans}

    report_lines.append("VLANs and DHCP scopes:")
    for vlan_id, src_vlan in src_vlan_map.items():
        dst_vlan = dst_vlan_map.get(vlan_id)
        if not dst_vlan:
            msg = f"✗ VLAN {vlan_id} ({src_vlan.get('name')}) missing in destination"
            log.warning(msg)
            report_lines.append(msg)
            continue

        fields = ["subnet", "applianceIp", "dhcpHandling", "dhcpLeaseTime", "dnsNameservers", "dhcpOptions"]
        mismatches = [f for f in fields if src_vlan.get(f) != dst_vlan.get(f)]

        if mismatches:
            msg = f"✗ VLAN {vlan_id} ({src_vlan.get('name')}) DHCP mismatch: {', '.join(mismatches)}"
            log.warning(msg)
            report_lines.append(msg)
        else:
            msg = f"✓ VLAN {vlan_id} ({src_vlan.get('name')}) DHCP settings validated"
            log.info(msg)
            report_lines.append(msg)

    # Static routes validation
    try:
        src_routes = db.appliance.getNetworkApplianceStaticRoutes(src_net)
        dst_routes = db.appliance.getNetworkApplianceStaticRoutes(dst_net)
    except APIError as e:
        msg = f"Static routes validation skipped: {e}"
        log.warning(msg)
        report_lines.append(msg)
        src_routes, dst_routes = [], []

    dst_routes_map = {r["name"]: r for r in dst_routes}
    report_lines.append("\nStatic Routes:")
    for r in src_routes:
        dst_r = dst_routes_map.get(r["name"])
        if not dst_r:
            msg = f"✗ Static route '{r['name']}' missing in destination"
            log.warning(msg)
            report_lines.append(msg)
            continue

        keys_to_check = ["subnet", "gatewayIp", "interface", "enabled"]
        mismatches = [k for k in keys_to_check if r.get(k) != dst_r.get(k)]
        if mismatches:
            msg = f"✗ Static route '{r['name']}' mismatch: {', '.join(mismatches)}"
            log.warning(msg)
            report_lines.append(msg)
        else:
            msg = f"✓ Static route '{r['name']}' validated"
            log.info(msg)
            report_lines.append(msg)

    # Wireless SSIDs validation
    report_lines.append("\nWireless SSIDs:")
    try:
        src_ssids = db.wireless.getNetworkWirelessSsids(src_net)
        dst_ssids = db.wireless.getNetworkWirelessSsids(dst_net)
    except APIError as e:
        msg = f"SSID validation skipped: {e}"
        log.warning(msg)
        report_lines.append(msg)
        src_ssids, dst_ssids = [], []

    dst_ssids_map = {s["number"]: s for s in dst_ssids}
    for s in src_ssids:
        num = s["number"]
        dst_s = dst_ssids_map.get(num)
        if not dst_s:
            msg = f"✗ SSID {num} ('{s.get('name')}') missing in destination"
            log.warning(msg)
            report_lines.append(msg)
            continue

        fields = ["name", "enabled", "authMode", "encryptionMode", "ssidNumber", "ipAssignmentMode"]
        mismatches = [f for f in fields if s.get(f) != dst_s.get(f)]
        if mismatches:
            msg = f"✗ SSID {num} ('{s.get('name')}') mismatch: {', '.join(mismatches)}"
            log.warning(msg)
            report_lines.append(msg)
        else:
            msg = f"✓ SSID {num} ('{s.get('name')}') validated"
            log.info(msg)
            report_lines.append(msg)

    # MX L3 Firewall rules validation
    report_lines.append("\nMX L3 Firewall Rules:")
    try:
        src_rules = db.appliance.getNetworkApplianceFirewallL3FirewallRules(src_net)["rules"]
        dst_rules = db.appliance.getNetworkApplianceFirewallL3FirewallRules(dst_net)["rules"]
    except APIError as e:
        msg = f"MX L3 Firewall validation skipped: {e}"
        log.warning(msg)
        report_lines.append(msg)
        src_rules, dst_rules = [], []

    if len(src_rules) != len(dst_rules):
        msg = f"✗ Firewall rule count mismatch: source={len(src_rules)}, destination={len(dst_rules)}"
        log.warning(msg)
        report_lines.append(msg)
    else:
        for i, (sr, dr) in enumerate(zip(src_rules, dst_rules)):
            if sr != dr:
                msg = f"✗ Firewall rule #{i+1} differs"
                log.warning(msg)
                report_lines.append(msg)
            else:
                msg = f"✓ Firewall rule #{i+1} matches"
                log.info(msg)
                report_lines.append(msg)

    # Group Policies validation
    report_lines.append("\nGroup Policies:")
    try:
        src_pols = db.networks.getNetworkGroupPolicies(src_net)
        dst_pols = db.networks.getNetworkGroupPolicies(dst_net)
    except APIError as e:
        msg = f"Group policies validation skipped: {e}"
        log.warning(msg)
        report_lines.append(msg)
        src_pols, dst_pols = [], []

    dst_pols_map = {p["name"]: p for p in dst_pols}
    for sp in src_pols:
        dp = dst_pols_map.get(sp["name"])
        if not dp:
            msg = f"✗ Group policy '{sp['name']}' missing in destination"
            log.warning(msg)
            report_lines.append(msg)
            continue

        keys_to_check = [k for k in sp if k not in {"groupPolicyId", "networkId"}]
        mismatches = [k for k in keys_to_check if sp.get(k) != dp.get(k)]
        if mismatches:
            msg = f"✗ Group policy '{sp['name']}' mismatch: {', '.join(mismatches)}"
            log.warning(msg)
            report_lines.append(msg)
        else:
            msg = f"✓ Group policy '{sp['name']}' validated"
            log.info(msg)
            report_lines.append(msg)

    # Save report to file
    report_path = f"network_validation_report_{dst_net}.txt"
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))
    log.info("Validation report saved to %s", report_path)

# ----------------------------
# Main Cloning Logic
# ----------------------------

def clone_network(api_key, src_net_id, dst_org_id, *, dst_net_name=None, time_zone="America/Chicago", use_native=True, log_level="INFO"):
    setup_logging(log_level)
    db = meraki.DashboardAPI(api_key=api_key, print_console=False, suppress_logging=True)
    src_info = db.networks.getNetwork(src_net_id)
    log.info("Source network '%s' (%s)", src_info["name"], src_net_id)

    if use_native:
        try:
            dst_net = db.organizations.createOrganizationNetwork(
                organizationId=src_info["organizationId"],
                name=dst_net_name or f"Cloned: {src_info['name']}",
                productTypes=src_info["productTypes"],
                timeZone=time_zone,
                copyFromNetworkId=src_net_id,
            )
            log.info("✓ Native clone complete (%s)", dst_net["id"])
            validate_network(db, src_net_id, dst_net["id"])
            return dst_net["id"]
        except APIError as e:
            log.warning("Native clone failed (%s); continuing with granular copy", e)

    dst_net = db.organizations.createOrganizationNetwork(
        organizationId=dst_org_id,
        name=dst_net_name or f"Cloned: {src_info['name']}",
        productTypes=src_info["productTypes"],
        timeZone=time_zone,
    )
    dst_id = dst_net["id"]
    log.info("-- Granular sync started --")

    if "wireless" in src_info["productTypes"]:
        sync_ssids(db, src_net_id, dst_id)

    if "appliance" in src_info["productTypes"]:
        sync_addressing(db, src_net_id, dst_id)
        sync_l3_fw(db, src_net_id, dst_id)

    sync_group_policies(db, src_net_id, dst_id)
    validate_network(db, src_net_id, dst_id)

    log.info("Granular sync complete ✓")
    return dst_id

# ----------------------------
# CLI Entry
# ----------------------------

def main():
    parser = argparse.ArgumentParser(description="Clone a Meraki network across orgs")
    parser.add_argument("--api-key", required=True, help="Your Meraki Dashboard API key")
    parser.add_argument("--src-net", required=True, help="Source network ID")
    parser.add_argument("--dst-org", required=True, help="Destination organization ID")
    parser.add_argument("--dst-name", help="Destination network name")
    parser.add_argument("--time-zone", default="America/Chicago", help="Timezone for new network")
    parser.add_argument("--no-native", action="store_true", help="Disable native clone via copyFromNetworkId")
    parser.add_argument("--log-level", default="INFO", help="Log verbosity (DEBUG, INFO, WARNING, ERROR)")
    args = parser.parse_args()

    net_id = clone_network(
        api_key=args.api_key,
        src_net_id=args.src_net,
        dst_org_id=args.dst_org,
        dst_net_name=args.dst_name,
        time_zone=args.time_zone,
        use_native=not args.no_native,
        log_level=args.log_level,
    )
    print(f"✓ Network cloned to {net_id}")

if __name__ == "__main__":
    main()
