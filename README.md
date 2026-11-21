# Shellies Script Updater

Shellies Script Updater brings updates for the Shellies Discovery Python scripts back to **Settings → System → Updates** after migrating from HACS to the Home Assistant Marketplace. It supports Home Assistant 2026.11.0 and later.

| Upstream project | File managed in your Home Assistant configuration |
| --- | --- |
| [Shellies Discovery](https://github.com/bieniu/ha-shellies-discovery) | `python_scripts/shellies_discovery.py` |
| [Shellies Discovery Gen2+](https://github.com/bieniu/ha-shellies-discovery-gen2) | `python_scripts/shellies_discovery_gen2.py` |

## Install from Marketplace

1. Open **Settings → Marketplace**. If the integration is available in the catalog, search for **Shellies Script Updater** and install it. When using the published GitHub repository directly, add it as a custom repository in the **Integration** category, then install it.
2. Go to **Settings → Devices & services** and select **Add integration → Shellies Script Updater**.
3. Open **Settings → System → Updates** to see available releases. Select an update to review its release notes, then choose **Install** when ready. To check the detected version at any time, open the script's update entity from the integration page.

[![Open Shellies Script Updater in Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=emkookmer&repository=shellies-script-updater&category=integration)
[![Set up Shellies Script Updater in Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=shellies_script_updater)

## Install manually

1. Copy the `custom_components/shellies_script_updater` folder from this project into your Home Assistant configuration folder. The resulting path should be `custom_components/shellies_script_updater/manifest.json`.
2. Restart Home Assistant.
3. Add **Shellies Script Updater** from **Settings → Devices & services**.

## Existing and new script installations

When you add the integration, it reads each script's embedded `VERSION` and saves the detected version in Home Assistant. Scripts previously installed from HACS release ZIPs are picked up automatically. Your existing MQTT configuration and automations can continue using the same script actions.

A missing file shows **Not installed**. A script without a recognizable version, such as a direct GitHub source copy with the placeholder `0.0.0`, shows **Untracked**. Installing a published release gives it a version the integration can track.

For a new setup, install the script you need from **Settings → System → Updates**. Enable Home Assistant's [Python Scripts integration](https://www.home-assistant.io/integrations/python_script/) and follow the corresponding upstream project's MQTT and automation instructions. If the script is missing from the action picker, reload Python Scripts or restart Home Assistant.

## How updates work

The integration checks the two GitHub repositories at startup and every six hours. Each script has its own update entry. Choosing **Install** downloads the selected stable release archive, verifies its SHA-256 digest, and replaces the matching script file. Updates preserve the file’s existing read, write, and execute permissions. New script files use `0644` (owner read and write, everyone else read). Earlier versions are available from the upstream release pages.

- [Shellies Discovery releases](https://github.com/bieniu/ha-shellies-discovery/releases)
- [Shellies Discovery Gen2+ releases](https://github.com/bieniu/ha-shellies-discovery-gen2/releases)

Removing the updater leaves the downloaded scripts in `python_scripts`.

## Publishing to the Marketplace catalog

The [Marketplace catalog guide](https://contributors.home-assistant.io/marketplace/guides/catalog/) requires a public GitHub repository with a description, topics, and issues enabled. Once the HACS and hassfest checks pass, publish a full GitHub release whose tag matches the integration manifest. Then submit the repository to the `integration` list in [hacs/default](https://github.com/hacs/default).