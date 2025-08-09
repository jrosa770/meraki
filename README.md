# copy_meraki_network.py
Replicates a Meraki Dashboard **network** from one organisation to another so
that the destination mirrors *all* components exposed by the v1 API as of
June 2025 — including **Addressing & VLANs (with DHCP scopes)** *and* **every
per‑SSID sub‑setting** (traffic shaping, firewall rules, Bonjour, etc.).

# copy_meraki_network.pip
Same as `# copy_meraki_network.py` but as a Pythoin pip package

# Meraki Switch Config CLI

A simple CLI tool to **backup and restore** Cisco Meraki **switch port configurations**.

## Features
- ✅ Backup individual Meraki switch port configurations to JSON
- 🔁 Restore those configurations to another switch
- 🏷️ Auto-renames the restored switch with `_restored` suffix
- 📦 Lightweight CLI (requires only `meraki` SDK)

## 👤 Author
Jose Rosa

## 📘 License
MIT License 