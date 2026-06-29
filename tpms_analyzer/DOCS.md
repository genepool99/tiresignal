# TPMS Analyzer

Reads `rtl_433` JSONL log data, stores TPMS events in SQLite, groups repeated sensor IDs into vehicle pass candidates, matches known/watch/ignored vehicles, and generates an HTML report served by Home Assistant.

## Before installing

Install and configure the `rtl_433` Home Assistant add-on first. TPMS Analyzer reads the JSONL log written by `rtl_433`; it does not run `rtl_433` itself.

The expected `rtl_433.conf.template` output is:

```text
output json:/config/rtl_433/logs/rtl_433.jsonl
convert customary
```

## Home Assistant automation setup

This add-on does not automatically create Home Assistant automations, scripts, shell commands, or rtl_433 configuration.

For scheduled analysis, the report Refresh button, and vehicle labeling actions, follow the copy-paste YAML setup in the project README.

For the current vehicle-labeling bridge, set this add-on option:

```yaml
vehicle_map_path: /config/rtl_433/tpms_analyzer/vehicles.json
```

This lets the legacy shell_command write to the same `vehicles.json` the add-on reads. Future versions may replace this bridge with a native add-on endpoint.

## Requirements

The `rtl_433` add-on must be installed and configured to write JSON Lines output to a file. The default expected path is:

```
/config/rtl_433/logs/rtl_433.jsonl
```

Add the following to your `rtl_433.conf.template`:

```
output json:/config/rtl_433/logs/rtl_433.jsonl
```

## Add-on options

| Option | Default | Description |
|---|---|---|
| `log_path` | `/config/rtl_433/logs/rtl_433.jsonl` | Path to the rtl_433 JSONL log file. |
| `refresh_webhook_id` | `tpms-refresh-report-a8f3c91b7d22` | Webhook ID used by the report's Refresh button to trigger re-analysis. Must match the webhook ID in your HA automation. |
| `vehicle_map_edit_webhook_id` | `tpms-vehicle-map-edit-b8f41c6a9e73` | Webhook ID used by the report's vehicle labeling actions. Must match the webhook ID in your HA automation. |
| `vehicle_map_path` | `/data/vehicles.json` | Path to the vehicle map used by the add-on. Keep the default for add-on-private state, or set to `/config/rtl_433/tpms_analyzer/vehicles.json` when using the vehicle-labeling bridge. |

## Viewing the report

After the add-on runs, the HTML report is available at:

```
http://your-ha-instance/local/rtl_433/tpms_report.html
```

To add it as a Home Assistant dashboard panel:

1. Go to **Settings → Dashboards**.
2. Click **Add Dashboard**.
3. Choose **Webpage**.
4. Set the URL to `/local/rtl_433/tpms_report.html`.

## Scheduling

This version of the add-on runs once and exits (`startup: once`, `boot: manual`). It does not replace your existing Home Assistant automations. Continue triggering analysis via your existing shell command or HA automation, or start the add-on manually from the add-on panel.

Persistent state (SQLite database, vehicle map, backups) is stored inside the add-on's `/data` volume and survives add-on restarts and updates.

## Troubleshooting

**Report not found at `/local/rtl_433/tpms_report.html`**
Check that `/config/www/rtl_433/tpms_report.html` exists. If `/config/www/` was newly created, restart Home Assistant Core once.

**No TPMS events imported**
Verify the `log_path` option points to an existing file with content. Check the add-on log output for `Log does not exist` warnings.

**Webhook buttons not working**
Confirm the `refresh_webhook_id` and `vehicle_map_edit_webhook_id` options match the webhook IDs defined in your HA automations.

**Vehicle map is missing or blank after install**
On first run the add-on creates `vehicles.json` in its `/data` volume if it does not already exist. Populate it using the labeling actions in the report, or copy your existing `vehicles.json` into the add-on data directory.
