#!/usr/bin/env python3
"""
meraki_switch_config_cli.py
Backup and restore Cisco Meraki switch **port** configurations (no config file).

Features
- Backup all port settings for a given switch serial to JSON
- Restore those settings to another switch
- Automatically renames the target switch to "<original_name>_restored"
- API key via --api-key or MERAKI_DASHBOARD_API_KEY

Usage
  Backup:
    python meraki_switch_config_cli.py --api-key $MERAKI_KEY backup --serial Q2XX-AAAA-BBBB

  Restore:
    python meraki_switch_config_cli.py --api-key $MERAKI_KEY restore \
      --serial Q2XX-CCCC-DDDD \
      --input backups/Q2XX-AAAA-BBBB_backup.json
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from datetime import datetime
from typing import Any, Dict

try:
    import meraki  # Meraki Dashboard SDK
except ImportError:  # pragma: no cover
    print("[!] Missing dependency: pip install meraki", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Meraki helpers
# ---------------------------------------------------------------------------

def dashboard_from_key(api_key: str) -> "meraki.DashboardAPI":
    """Return an authenticated Meraki DashboardAPI instance."""
    return meraki.DashboardAPI(api_key, suppress_logging=True)


# ---------------------------------------------------------------------------
# Backup / Restore functions
# ---------------------------------------------------------------------------

def backup_switch(dashboard: "meraki.DashboardAPI", serial: str, out_dir: pathlib.Path) -> None:
    """
    Back up all port settings for *serial* to JSON in *out_dir*.
    Output file: <out_dir>/<serial>_backup.json
    """
    try:
        dev = dashboard.devices.getDevice(serial)
    except meraki.APIError as e:
        print(f"[!!] Device lookup failed: {e}", file=sys.stderr)
        sys.exit(1)

    ports = dashboard.switch.getDeviceSwitchPorts(serial)

    payload: Dict[str, Any] = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "source_serial": serial,
            "model": dev.get("model"),
            "name": dev.get("name"),
        },
        "ports": ports,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    outfile = out_dir / f"{serial}_backup.json"
    with outfile.open("w") as fh:
        json.dump(payload, fh, indent=4)
    print(f"[✓] Backup saved → {outfile}")


def restore_switch(dashboard: "meraki.DashboardAPI", target_serial: str, infile: pathlib.Path) -> None:
    """
    Restore port settings from *infile* onto *target_serial*.
    Also renames the target switch to "<original_name>_restored" when available.
    """
    if not infile.exists():
        print(f"[!] Backup file not found: {infile}", file=sys.stderr)
        sys.exit(1)

    with infile.open() as fh:
        data = json.load(fh)

    # Rename the target switch first (if original name is available)
    original_name = data.get("metadata", {}).get("name")
    if original_name:
        restored_name = f"{original_name}_restored"
        try:
            dashboard.devices.updateDevice(target_serial, name=restored_name)
            print(f"[*] Switch renamed to '{restored_name}'")
        except meraki.APIError as exc:
            print(f"[!] Failed to rename switch: {exc}", file=sys.stderr)

    ports: list[Dict[str, Any]] = data.get("ports", [])
    if not ports:
        print("[!] No 'ports' key in backup JSON", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Restoring configuration of {len(ports)} ports onto {target_serial}…")

    # Only send keys that Meraki allows on updateDeviceSwitchPort
    allowed_keys = {
        "name",
        "tags",
        "enabled",
        "type",
        "vlan",
        "voiceVlan",
        "allowedVlans",
        "poeEnabled",
        "isolationEnabled",
        "rstpEnabled",
        "stpGuard",
        "linkNegotiation",
    }

    for port in ports:
        port_id = port["portId"]
        body = {k: port[k] for k in allowed_keys if k in port and port[k] is not None}
        try:
            dashboard.switch.updateDeviceSwitchPort(target_serial, port_id, **body)
            print(f"  • Port {port_id}: OK")
        except meraki.APIError as exc:
            print(f"  x Port {port_id}: {exc}", file=sys.stderr)

    print("[✓] Restore complete")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_args() -> argparse.Namespace:
    backup_dir_default = pathlib.Path("backups")

    p = argparse.ArgumentParser(
        description="Backup and restore Cisco Meraki switch port configs (no config file)."
    )
    p.add_argument(
        "--api-key",
        dest="api_key",
        help="Meraki Dashboard API key (falls back to env MERAKI_DASHBOARD_API_KEY)",
    )

    sp = p.add_subparsers(dest="command", required=True, metavar="{backup,restore}")

    # backup
    p_b = sp.add_parser("backup", help="Back up a switch’s port configuration")
    p_b.add_argument("--serial", required=True, help="Switch serial to back up")
    p_b.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=backup_dir_default,
        help="Destination directory for backup JSON (default: ./backups)",
    )

    # restore
    p_r = sp.add_parser("restore", help="Restore config from a backup JSON")
    p_r.add_argument("--serial", required=True, help="Target switch serial")
    p_r.add_argument("--input", type=pathlib.Path, required=True, help="Backup JSON path")

    return p.parse_args()


def main() -> None:  # pragma: no cover
    args = get_args()

    api_key = args.api_key or os.getenv("MERAKI_DASHBOARD_API_KEY")
    if not api_key:
        print(
            "[!] Provide --api-key or set MERAKI_DASHBOARD_API_KEY in the environment",
            file=sys.stderr,
        )
        sys.exit(1)

    dashboard = dashboard_from_key(api_key)

    if args.command == "backup":
        backup_switch(dashboard, args.serial, args.out_dir)
    elif args.command == "restore":
        restore_switch(dashboard, args.serial, args.input)
    else:  # pragma: no cover
        print("[!] Unknown command", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
