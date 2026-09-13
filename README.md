<p align="center">
  <img src="tpms_analyzer/tiresignal-logo.png" alt="TireSignal logo" width="420">
</p>

# TireSignal

TireSignal is a Home Assistant add-on for `rtl_433` TPMS JSONL logs. It imports tire-pressure sensor events, groups likely vehicle passes, and helps you label sensors as Known, Watchlist, or Ignored vehicles while surfacing recurring unlabeled sensor groups as candidates worth reviewing, all through a Home Assistant-friendly report.

## Features

* Reads `rtl_433` JSONL log output and stores TPMS events in SQLite with deduplication and configurable retention.
* Groups nearby detections into likely vehicle passes and surfaces exact-repeat and overlap candidates for recurring unlabeled sensors.
* Lets you label sensors as Known, Watchlist, or Ignored vehicles.
* Presence timeline and 7-day traffic heatmap for home-security and traffic-awareness use cases.
* Analytics tab with event, signal, and decoded TPMS field charts.
* Diagnostics tab with import/pruning stats and report & database health.
* Recent Events, Recent Passes, and Raw Packets views for deeper investigation.
* Serves the report through Home Assistant Ingress/sidebar, with direct web access on port `8099` when exposed.
* Runs manual and scheduled refreshes inside the add-on.

![TireSignal report screenshot](assets/tiresignal-report-screenshot.png)

![TireSignal report screenshot](assets/tiresignal-report-screenshot2.png)

## Requirements

* Home Assistant with add-on support.
* `rtl_433` producing a JSONL log at the path configured in TireSignal.

## rtl_433 requirement

TireSignal does not receive radio traffic directly. It reads TPMS events from an `rtl_433` JSONL log file.

Install and start `rtl_433` before using TireSignal. In Home Assistant, one common option is the `rtl_433` add-on repository:

<a href="https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fpbkhrv%2Frtl_433-hass-addons" target="_blank" rel="noreferrer noopener">
  <img src="https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg" alt="Open your Home Assistant instance and add the rtl_433 add-on repository.">
</a>

```text
https://github.com/pbkhrv/rtl_433-hass-addons
```

Install the `rtl_433` add-on from that repository, then configure `rtl_433` to use customary units and write JSON output. `convert customary` is recommended so TPMS pressure values are reported in customary units such as PSI.

```text
convert customary
output json:/config/rtl_433/logs/rtl_433.jsonl
```

The TireSignal add-on `log_path` option must match the `rtl_433` output path.

## Install

1. Add this repository to the Home Assistant Add-on Store:

   <a href="https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fgenepool99%2Ftiresignal" target="_blank" rel="noreferrer noopener">
     <img src="https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg" alt="Open your Home Assistant instance and add the TireSignal add-on repository.">
   </a>

   ```text
   https://github.com/genepool99/tiresignal
   ```

2. Install **TireSignal**.
3. Configure the add-on options if needed.
4. Start the add-on.
5. Open TireSignal from the Home Assistant sidebar or click **Open Web UI** on the add-on page.

## Configuration

| Option | Default | Description |
|---|---|---|
| `log_path` | `/config/rtl_433/logs/rtl_433.jsonl` | Path to the `rtl_433` JSONL log file. |
| `vehicle_map_path` | `/data/vehicles.json` | Persistent vehicle-label map used by the report UI. |
| `scheduled_refresh_enabled` | `true` | Enables the internal daily scheduled refresh. |
| `scheduled_refresh_time` | `03:10` | Daily refresh time in `HH:MM` using the add-on local time. |

### Advanced tuning

These options are safe to leave at their defaults for most installs.

| Option | Default | Description |
|---|---|---|
| `enable_pruning` | `true` | Prunes old events from unrecognized sensors. Disable to retain all events permanently. |
| `unknown_sensor_retention_days` | `180` | Days to keep events from unrecognized sensors before pruning. Lower on busy roads to save disk space. |
| `pass_window_seconds` | `5` | Seconds within which readings are grouped as a single vehicle pass. Lower for busy roads, higher for quiet driveways. |
| `min_repeat_cluster_count` | `3` | Minimum times a sensor must repeat within a pass window to be treated as a vehicle sensor rather than road noise. |

## Usage

* Open the report from the Home Assistant sidebar or **Open Web UI**.
* Click **Refresh** in the report to rerun analysis.
* Use the report labeling controls to add sensors to the vehicle map.
* Leave scheduled refresh enabled to refresh the report daily.
* Direct access is available on port `8099` when exposed by the add-on configuration.

### Report tabs

* **Overview** — summary cards, presence overview, presence timeline, and traffic heatmap.
* **Vehicles** — manage Known, Watchlist, and Ignored vehicles.
* **Candidates** — review exact-repeat and overlap candidates that may point to a recurring unlabeled vehicle. Use the row action menu (`⋮`) on each row to label, ignore, move, or inspect candidates. Mixed sensor type warnings are informational only and do not affect scoring.
* **Analytics** — event, signal, and decoded TPMS field charts.
* **Details** — Recent Passes, sensor summaries, and Recent Events.
* **Raw Packets** — recent rtl_433 log entries for troubleshooting.
* **Diagnostics** — import/pruning stats and report & database health.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Checks service health. |
| GET | `/` | Serves the HTML report. |
| GET | `/report` | Serves the HTML report. |
| POST | `/refresh` | Runs analysis and regenerates the report. |
| POST | `/vehicle-map-edit` | Applies report UI vehicle-labeling changes and refreshes the report. |

## Data Locations

| Path | Purpose |
|---|---|
| `/data/vehicles.json` | Persistent vehicle labels. |
| `/data/tpms.sqlite` | SQLite event database. |
| `/data/output/` | Vehicle-map backups and support output. |
| `/config/www/rtl_433/tpms_report.html` | Published HTML report. |
| `/config/www/rtl_433/tpms_status.json` | Published status JSON. |

## Troubleshooting

**No report**
Check `log_path`, confirm the file exists, then click **Refresh** in the report UI.

**No data**
Confirm `rtl_433` is writing JSONL records to the configured log path.

**Vehicle labels are not saving**
Check `vehicle_map_path` and review the add-on logs for write or validation errors.

**Update not appearing**
Reload the Home Assistant Add-on Store, then check for add-on updates again.

## License
MIT License. See [LICENSE](LICENSE).

