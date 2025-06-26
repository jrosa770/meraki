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

## Script as a Native Python Application

The script can be installed as a native application when the PIP package copy_meraki_network-0.1.0.tar.gz is installed.

### Install Example:

1. Clone or download file from Git 

2. Install via Python pip using the command `pip install copy_meraki_network-0.1.0.tar.gz`

> Example Intall:

```sh
$ pip install copy_meraki_network-0.1.0.tar.gz 
Processing ./copy_meraki_network-0.1.0.tar.gz
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Requirement already satisfied: meraki in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from copy-meraki-network==0.1.0) (2.0.3)
Requirement already satisfied: requests<3.0.0,>=2.32.2 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from meraki->copy-meraki-network==0.1.0) (2.32.4)
Requirement already satisfied: aiohttp<4.0.0,>=3.11.18 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from meraki->copy-meraki-network==0.1.0) (3.12.13)
Requirement already satisfied: jinja2==3.1.6 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from meraki->copy-meraki-network==0.1.0) (3.1.6)
Requirement already satisfied: pytest<9.0.0,>=8.3.5 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from meraki->copy-meraki-network==0.1.0) (8.4.1)
Requirement already satisfied: setuptools<79.0.0,>=78.1.1 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from meraki->copy-meraki-network==0.1.0) (78.1.1)
Requirement already satisfied: build<2.0.0,>=1.2.2.post1 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from meraki->copy-meraki-network==0.1.0) (1.2.2.post1)
Requirement already satisfied: wheel<0.46.0,>=0.45.1 in /opt/homebrew/lib/python3.13/site-packages (from meraki->copy-meraki-network==0.1.0) (0.45.1)
Requirement already satisfied: MarkupSafe>=2.0 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from jinja2==3.1.6->meraki->copy-meraki-network==0.1.0) (3.0.2)
Requirement already satisfied: aiohappyeyeballs>=2.5.0 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from aiohttp<4.0.0,>=3.11.18->meraki->copy-meraki-network==0.1.0) (2.6.1)
Requirement already satisfied: aiosignal>=1.1.2 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from aiohttp<4.0.0,>=3.11.18->meraki->copy-meraki-network==0.1.0) (1.3.2)
Requirement already satisfied: attrs>=17.3.0 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from aiohttp<4.0.0,>=3.11.18->meraki->copy-meraki-network==0.1.0) (25.3.0)
Requirement already satisfied: frozenlist>=1.1.1 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from aiohttp<4.0.0,>=3.11.18->meraki->copy-meraki-network==0.1.0) (1.7.0)
Requirement already satisfied: multidict<7.0,>=4.5 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from aiohttp<4.0.0,>=3.11.18->meraki->copy-meraki-network==0.1.0) (6.5.1)
Requirement already satisfied: propcache>=0.2.0 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from aiohttp<4.0.0,>=3.11.18->meraki->copy-meraki-network==0.1.0) (0.3.2)
Requirement already satisfied: yarl<2.0,>=1.17.0 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from aiohttp<4.0.0,>=3.11.18->meraki->copy-meraki-network==0.1.0) (1.20.1)
Requirement already satisfied: packaging>=19.1 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from build<2.0.0,>=1.2.2.post1->meraki->copy-meraki-network==0.1.0) (25.0)
Requirement already satisfied: pyproject_hooks in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from build<2.0.0,>=1.2.2.post1->meraki->copy-meraki-network==0.1.0) (1.2.0)
Requirement already satisfied: iniconfig>=1 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from pytest<9.0.0,>=8.3.5->meraki->copy-meraki-network==0.1.0) (2.1.0)
Requirement already satisfied: pluggy<2,>=1.5 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from pytest<9.0.0,>=8.3.5->meraki->copy-meraki-network==0.1.0) (1.6.0)
Requirement already satisfied: pygments>=2.7.2 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from pytest<9.0.0,>=8.3.5->meraki->copy-meraki-network==0.1.0) (2.19.2)
Requirement already satisfied: charset_normalizer<4,>=2 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from requests<3.0.0,>=2.32.2->meraki->copy-meraki-network==0.1.0) (3.4.2)
Requirement already satisfied: idna<4,>=2.5 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from requests<3.0.0,>=2.32.2->meraki->copy-meraki-network==0.1.0) (3.10)
Requirement already satisfied: urllib3<3,>=1.21.1 in /Users/joserosa/.venv_native/lib/python3.13/site-packages (from requests<3.0.0,>=2.32.2->meraki->copy-meraki-network==0.1.0) (2.5.0)
Requirement already satisfied: certifi>=2017.4.17 in /opt/homebrew/lib/python3.13/site-packages (from requests<3.0.0,>=2.32.2->meraki->copy-meraki-network==0.1.0) (2025.1.31)
Building wheels for collected packages: copy-meraki-network
  Building wheel for copy-meraki-network (pyproject.toml) ... done
  Created wheel for copy-meraki-network: filename=copy_meraki_network-0.1.0-py3-none-any.whl size=5830 sha256=dc23ba446da6f44644d8f82466588f0444096d6b3281ca2718b151890d9b5d9c
  Stored in directory: /Users/joserosa/Library/Caches/pip/wheels/0e/b9/61/4102e209e423fa2049c954cdf1c9e9c00fc238b5f5182c3e15
Successfully built copy-meraki-network
Installing collected packages: copy-meraki-network
Successfully installed copy-meraki-network-0.1.0
```

> Now the script can be run natively from the shell:
```
$ copy-meraki-network --api-key FILTERED-MERAKI_ADMIN_API_KEY --src-net L_90000000000000912 --dst-org 123456 --dst-name "Test_Transfer_Net" --time-zone "America/Chicago" --no-native
2025-06-26 11:08:44 INFO: Source 'Test_Transfer_Net' (L_90000000000000912)
2025-06-26 11:08:46 INFO: Created blank network L_90000000000000913 – starting granular sync
2025-06-26 11:08:47 INFO: Enabled VLANs on destination network L_90000000000000913
2025-06-26 11:08:48 INFO: ✓ VLAN 1 updated
2025-06-26 11:08:49 INFO: ✓ VLAN 999 created
2025-06-26 11:08:50 INFO: ✓ VLAN 1000 created
2025-06-26 11:08:51 INFO: ✓ VLAN 2000 created
2025-06-26 11:08:52 INFO: ✓ VLAN 2002 created
2025-06-26 11:08:53 INFO: ✓ VLAN 2004 created
2025-06-26 11:08:54 INFO: ✓ VLAN 2008 created
2025-06-26 11:08:54 INFO: ✓ VLAN 2010 created
2025-06-26 11:08:56 INFO: ✓ VLAN 2012 created
2025-06-26 11:08:57 INFO: ✓ VLAN 2014 created
2025-06-26 11:08:57 INFO: ✓ VLAN 2016 created
2025-06-26 11:08:58 INFO: ✓ VLAN 2018 created
2025-06-26 11:08:59 INFO: ✓ VLAN 2020 created
2025-06-26 11:09:00 INFO: ✓ VLAN 2022 created
2025-06-26 11:09:01 INFO: ✓ VLAN 2024 created
2025-06-26 11:09:02 INFO: ✓ VLAN 2100 created
2025-06-26 11:09:03 INFO: ✓ VLAN 2104 created
2025-06-26 11:09:04 INFO: ✓ VLAN 2108 created
2025-06-26 11:09:05 INFO: ✓ VLAN 2112 created
2025-06-26 11:09:06 INFO: ✓ VLAN 2116 created
2025-06-26 11:09:07 INFO: ✓ VLAN 2118 created
2025-06-26 11:09:08 INFO: ✓ VLAN 2200 created
2025-06-26 11:09:09 INFO: ✓ VLAN 2201 created
2025-06-26 11:09:10 INFO: ✓ VLAN 2202 created
2025-06-26 11:09:11 INFO: ✓ VLAN 2300 created
2025-06-26 11:09:12 INFO: ✓ VLAN 3000 created
2025-06-26 11:09:13 INFO: ✓ VLAN 4000 created
2025-06-26 11:09:15 INFO: ✓ SSID 0 synced
2025-06-26 11:09:15 INFO: ✓ SSID 1 synced
2025-06-26 11:09:16 INFO: ✓ SSID 2 synced
2025-06-26 11:09:16 INFO: ✓ SSID 3 synced
2025-06-26 11:09:17 INFO: ✓ SSID 4 synced
2025-06-26 11:09:17 INFO: ✓ SSID 5 synced
2025-06-26 11:09:18 INFO: ✓ SSID 6 synced
2025-06-26 11:09:18 INFO: ✓ SSID 7 synced
2025-06-26 11:09:19 INFO: ✓ SSID 8 synced
2025-06-26 11:09:19 INFO: ✓ SSID 9 synced
2025-06-26 11:09:20 INFO: ✓ SSID 10 synced
2025-06-26 11:09:20 INFO: ✓ SSID 11 synced
2025-06-26 11:09:21 INFO: ✓ SSID 12 synced
2025-06-26 11:09:21 INFO: ✓ SSID 13 synced
2025-06-26 11:09:22 INFO: ✓ SSID 14 synced
2025-06-26 11:09:23 INFO: Validation report saved to dhcp_validation_report_L_90000000000000913.txt
2025-06-26 11:09:23 INFO: Granular sync complete ✓
✓ Network cloned to L_90000000000000913
```

## 👤 Author
Jose Rosa

## 📘 License
MIT License 