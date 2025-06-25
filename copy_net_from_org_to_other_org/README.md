# copy_meraki_network.py
Replicates a Meraki Dashboard **network** from one organisation to another so
that the destination mirrors *all* components exposed by the v1 API as of
June 2025 — including **Addressing & VLANs (with DHCP scopes)** *and* **every
per‑SSID sub‑setting** (traffic shaping, firewall rules, Bonjour, etc.).

## Key capabilities
--
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

> Author  : Jose Rosa
> Updated : 2025‑06‑24

Run from CLI or import `clone_network()`.

### Prerequisite: Python3

> From A shell in Linux/ Unix
1. Install the official SDK
`pip install meraki`

2. Run it
```python
python3 copy_meraki_network.py \
  --api-key $MERAKI_DASHBOARD_API_KEY \
  --src-net N_1234 \
  --dst-org 987654 \
  --dst-name "Lab‑clone" \
  --time-zone "America/Chicago" \
  --no-native         # optional: skip Dashboard‑side copyFromNetworkId
```
## 👤 Author
Jose Rosa

## 📘 License
MIT License 