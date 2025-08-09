# Meraki Switch Config CLI

A simple CLI tool to **backup and restore** Cisco Meraki **switch port configurations**.

## Features
- ✅ Backup individual Meraki switch port configurations to JSON
- 🔁 Restore those configurations to another switch
- 🏷️ Auto-renames the restored switch with `_restored` suffix
- 📦 Lightweight CLI (requires only `meraki` SDK)

## Installation

```bash
pip install .
```

## Usage

```bash
meraki-switch-config --api-key <API_KEY> backup --serial <SWITCH_SERIAL>
meraki-switch-config --api-key <API_KEY> restore --serial <TARGET_SERIAL> --input <BACKUP_JSON>
```

If `--api-key` is not provided, it will default to the environment variable:

```bash
export MERAKI_DASHBOARD_API_KEY=<your_key>
```

### Example

```bash
# Backup
meraki-switch-config --api-key $MERAKI_KEY backup --serial Q2XX-AAAA-BBBB

# Restore
meraki-switch-config --api-key $MERAKI_KEY restore --serial Q2XX-CCCC-DDDD --input backups/Q2XX-AAAA-BBBB_backup.json
```

## Development

1. Clone this repo:
   ```bash
   git clone https://github.com/your-org/meraki-switch-config-cli.git
   cd meraki-switch-config-cli
   ```

2. Install locally:
   ```bash
   pip install -e .
   ```

## Packaging for PyPI

```bash
python -m build
twine upload dist/*
```

## License
MIT © 2024

## Disclaimer
This tool is not officially affiliated with Cisco or the Meraki team. Use responsibly and test in lab environments before production use.
