# rtl_433 TPMS Analyzer for Home Assistant

A local TPMS analyzer for `rtl_433` JSONL logs.

It reads TPMS radio events, stores them in SQLite, groups repeated tire sensor IDs into likely vehicle/pass candidates, matches known/watch/ignored vehicles, and generates a visual HTML report that can be displayed inside Home Assistant.

This was designed for a Home Assistant VM setup with the `rtl_433` add-on writing JSON Lines logs to `/config`.

## What it does

* Reads `rtl_433` JSONL output.
* Filters likely TPMS events.
* Stores parsed events in SQLite with deduplication.
* Preserves raw JSON for later backfills and diagnostics.
* Groups nearby detections into possible vehicle passes.
* Uses busy-road tuning to reduce accidental merging of multiple passing vehicles.
* Caps synthetic overlap candidates so noisy windows do not become fake 6–9 sensor “vehicles.”
* Matches known/watch/ignore vehicles from `vehicles.json`.
* Labels crowded raw passes when too many sensors appear in one pass window.
* Generates a Home Assistant-served HTML report.
* Generates a small status JSON file.
* Backs up `vehicles.json`.
* Prunes old unknown road-noise events while preserving labeled vehicle events.
* Generates charts for event volume, pressure, temperature, model distribution, confirmed battery status, unconfirmed battery hints, and signal quality.

## Important privacy note

TPMS IDs can act like vehicle fingerprints. Keep the generated data local, do not publish the report publicly, and treat the data similarly to camera, Bluetooth tracking, or license-plate-reader telemetry.

## Expected project layout

Recommended path inside Home Assistant:

```text
/config/rtl_433/tpms_analyzer/
├── analyze_tpms.py
├── analysis.py
├── db.py
├── report.py
├── tpms_config.py
├── utils.py
├── vehicle_map.py
├── vehicle_map_editor.py
├── vehicles.json
├── output/
└── tpms.sqlite
```

Generated Home Assistant web files:

```text
/config/www/rtl_433/tpms_report.html
/config/www/rtl_433/tpms_status.json
```

Served by Home Assistant as:

```text
/local/rtl_433/tpms_report.html
/local/rtl_433/tpms_status.json
```

## rtl_433 configuration

Your `rtl_433.conf.template` should include JSON output to a writable path:

```conf
output json:/config/rtl_433/logs/rtl_433.jsonl
```

Useful supporting lines:

```conf
report_meta time:iso:usec:tz
report_meta level
report_meta protocol
report_meta noise:10
report_meta stats:60

frequency 433.92M
convert si
verbose 6
```

If you previously disabled TPMS protocols with many `protocol -...` lines, remove or comment those out if you want TPMS analysis.

## Configuration files

### `tpms_config.py`

This contains paths and tuning values.

Important values:

```python
LOG_PATH = Path("/config/rtl_433/logs/rtl_433.jsonl")
BASE_DIR = Path("/config/rtl_433/tpms_analyzer")
DB_PATH = BASE_DIR / "tpms.sqlite"
VEHICLE_MAP_PATH = BASE_DIR / "vehicles.json"

REPORT_PATH = Path("/config/www/rtl_433/tpms_report.html")
STATUS_PATH = Path("/config/www/rtl_433/tpms_status.json")
```

Matching and report tuning:

```python
PASS_WINDOW_SECONDS = 5
MIN_REPEAT_CLUSTER_COUNT = 3
POSSIBLE_SENSOR_COUNT = 3
STRONG_SENSOR_COUNT = 4
MAX_CANDIDATE_SENSOR_COUNT = 5
MAX_RECENT_PASSES = 500
MAX_RECENT_EVENTS = 750
```

### Busy-road pass window

`PASS_WINDOW_SECONDS` controls how close consecutive TPMS detections can be before they are grouped into the same raw pass.

For a busy road, a shorter window is safer:

```python
PASS_WINDOW_SECONDS = 5
```

If detections from the same vehicle are split too often, try a slightly larger value. If multiple vehicles are being merged into one pass, lower it.

### Candidate sensor cap

`MAX_CANDIDATE_SENSOR_COUNT` limits synthetic candidate clusters:

```python
MAX_CANDIDATE_SENSOR_COUNT = 5
```

This prevents overlap matching from turning noisy/chained traffic into fake 6–9 sensor “vehicles.” Raw passes can still show more than 5 sensors, but the report labels those as crowded windows instead of promoting them as likely vehicle candidates.

## `vehicles.json`

This is your labeling file.

Categories:

* `known`: vehicles you recognize or care about.
* `watch`: recurring unknowns worth watching.
* `ignore`: road noise or recurring clusters you do not care about.

Example:

```json
{
  "vehicles": [
    {
      "name": "Avi car",
      "category": "known",
      "notes": "Confirmed from driveway arrival",
      "sensor_ids": [
        "19123456",
        "19234567",
        "19345678",
        "19456789"
      ]
    },
    {
      "name": "Possible delivery vehicle",
      "category": "watch",
      "notes": "Recurring midday cluster",
      "sensor_ids": [
        "55555555",
        "66666666"
      ]
    },
    {
      "name": "Ignored road noise",
      "category": "ignore",
      "notes": "Uninteresting recurring drive-by",
      "sensor_ids": [
        "99999999"
      ]
    }
  ]
}
```

## Running manually

From Home Assistant Terminal:

```bash
cd /config/rtl_433/tpms_analyzer
python3 analyze_tpms.py
```

Then open:

```text
/local/rtl_433/tpms_report.html
```

## Home Assistant shell command

Add this under the existing top-level `shell_command:` block in `configuration.yaml`:

```yaml
shell_command:
  analyze_tpms_log: >
    sh -c 'cd /config/rtl_433/tpms_analyzer && python3 analyze_tpms.py'
```

If you already have `shell_command:` for log rotation, do not create a second one. Add `analyze_tpms_log` under the same block.

## Manual refresh script

Because `configuration.yaml` usually has:

```yaml
script: !include scripts.yaml
```

add this to `/config/scripts.yaml`:

```yaml
refresh_tpms_report:
  alias: Refresh TPMS Report
  sequence:
    - service: shell_command.analyze_tpms_log
```

Reload scripts or restart Home Assistant Core.

## Optional webpage refresh button

The static HTML report can call a Home Assistant webhook to trigger the refresh script.

Example automation in `automations.yaml`:

```yaml
- alias: TPMS report webpage refresh webhook
  id: tpms_report_webpage_refresh_webhook
  mode: single
  trigger:
    - platform: webhook
      webhook_id: tpms-refresh-report-change-this-to-a-long-random-value
      allowed_methods:
        - POST
      local_only: false
  action:
    - service: script.refresh_tpms_report
```

Use a long random webhook ID. If you access Home Assistant through Nabu Casa, assume the webhook can be reached externally by anyone who knows the ID.

Then set the same webhook ID in `tpms_config.py`:

```python
REFRESH_WEBHOOK_ID = "tpms-refresh-report-change-this-to-a-long-random-value"
```

## Add as a Home Assistant dashboard

In Home Assistant:

1. Go to **Settings → Dashboards**.
2. Click **Add Dashboard**.
3. Choose **Webpage**.
4. Use:

```text
Title: TPMS Monitor
Icon: mdi:car-tire-alert
URL: /local/rtl_433/tpms_report.html
```

## Data flow

The analyzer works roughly like this:

```text
rtl_433 JSONL log
        ↓
db.py ingest_log()
        ↓
SQLite tpms_events table
        ↓
backfills / pruning
        ↓
analysis.py grouping and matching
        ↓
report.py HTML report
        ↓
Home Assistant /local/rtl_433/tpms_report.html
```

## Stored event fields

The SQLite database stores normalized event fields including:

* event time
* sensor ID
* model
* protocol
* pressure kPa
* pressure PSI
* normalized temperature Celsius
* confirmed battery status
* unconfirmed `maybe_battery`
* RSSI
* SNR
* noise
* raw JSON
* raw hash

Raw JSON is preserved so older rows can be backfilled when new fields are supported later.

## Temperature handling

The analyzer stores temperature as normalized Celsius in `temperature_c`.

Supported raw Celsius fields include:

```text
temperature_C
temperature_Celsius
temp_C
temp_Celsius
```

Supported raw Fahrenheit fields include:

```text
temperature_F
temperature_Fahrenheit
temp_F
temp_Fahrenheit
```

Fahrenheit values are converted to Celsius using:

```text
(F - 32) * 5 / 9
```

Historical rows can be backfilled from stored `raw_json`, so the temperature chart can use old events after the analyzer is run with the updated code.

## Battery handling

There are two different battery-related concepts in the report.

### Confirmed battery status

Confirmed battery status uses only fields like:

```text
battery_ok
battery
```

These are normalized for charting as:

```text
Battery OK
Battery Low
Unknown / no confirmed battery field
```

The report does not treat missing battery fields as a battery problem. Many TPMS decoders simply do not emit confirmed battery status.

### Unconfirmed `maybe_battery`

Some rtl_433 TPMS decoders emit:

```text
maybe_battery
```

This is stored separately as a numeric diagnostic decoder hint.

Important:

* `maybe_battery` is not mapped to Battery OK or Battery Low.
* It is not treated as a probability.
* It is not interpreted as confirmed battery health.
* It is shown separately as **Unconfirmed Battery Signal**.
* It appears to be model/protocol-specific and should be treated as raw diagnostic data.

This keeps the report useful without pretending the decoder hint has a known universal meaning.

## Signal quality

The report can chart signal-related fields when available:

```text
rssi
snr
noise
```

These are useful for antenna placement, receiver tuning, and identifying weak reception patterns.

## Vehicle matching

The analyzer creates raw passes by grouping nearby TPMS detections within `PASS_WINDOW_SECONDS`.

It then produces candidate summaries:

### Raw passes

Raw passes are the immediate time-window grouping of sensor events.

If a raw pass contains more sensors than `MAX_CANDIDATE_SENSOR_COUNT`, the report labels it as:

```text
Crowded window
```

This usually means multiple vehicles were probably detected in the same short time window.

### Exact repeat sensor groups

Exact candidates are repeated groups with the same sensor set.

These are stricter but can miss vehicles when only some sensors are heard during each pass.

### Best Guess Vehicle Candidates

Overlap candidates merge repeated passes that share at least two sensor IDs.

To prevent chain contamination, overlap candidates are capped by `MAX_CANDIDATE_SENSOR_COUNT`. This avoids creating giant fake vehicle candidates from overlapping traffic.

### Known / watch / ignore matching

Known vehicles are matched by sensor overlap against `vehicles.json`.

Ignored vehicles are not promoted as useful candidates, but their labeled sensor events can still be preserved during pruning.

## Report tabs

The generated report has clean top-level tabs:

```text
Overview
Charts
Details
Raw Packets
```

The tabs intentionally do not show counts because the report now contains multiple kinds of summaries, charts, and diagnostics.

## Overview tab

The Overview tab includes:

* Summary cards
* Known / Watchlist Vehicle Summary
* Ignored Vehicles
* New Repeat Unknowns
* Best Guess Vehicle Candidates
* Exact Repeat Sensor Groups

Long/noisy sections are collapsible so the report remains navigable.

## Charts tab

The Charts tab includes a time-range filter:

```text
All data
Last 24 hours
Last 7 days
Last 30 days
```

The filter is relative to the newest event timestamp in the report, not the browser’s current time. This makes saved/old reports behave consistently.

Charts include:

### Detection Timeline

Shows TPMS detections over time by sensor ID.

### Daily TPMS Event Volume

Shows event counts grouped by day.

### Hourly TPMS Event Volume

Shows event counts by hour of day.

### Pressure Over Time

Shows pressure readings over time.

Pressure currently prefers PSI when available and falls back to kPa. No PSI/kPa conversion is performed in the chart, so mixed-unit data should be interpreted carefully.

### Temperature Over Time

Shows normalized Celsius temperature over time.

This chart uses `temperature_c`, including values converted from Fahrenheit during ingest/backfill.

### Events by Model

Shows TPMS event counts by rtl_433 model.

Protocol details are best treated as metadata because numeric rtl_433 protocol IDs are less readable than model names.

### Confirmed Battery Status

Shows only confirmed battery fields such as `battery_ok` or `battery`.

It does not interpret `maybe_battery`.

### Unconfirmed Battery Signal

Shows raw `maybe_battery` values over time as a diagnostic decoder hint.

This is useful for exploration, but it is not confirmed battery health.

### Signal Quality Over Time

Shows available RSSI, SNR, and noise data over time.

## Details tab

The Details tab includes:

* Recent Passes
* Unique TPMS Sensor IDs
* Recent Raw Events
* Import / Pruning Stats

Long tables are collapsible.

## Raw Packets tab

The Raw Packets tab shows recent raw rtl_433 JSONL packets from the active log file.

This can include packets that are not parsed as TPMS events.

## Pruning behavior

The analyzer can prune old unknown events while preserving labeled vehicle events.

Recommended defaults for busy-road use:

```python
ENABLE_PRUNING = True
UNKNOWN_SINGLE_SENSOR_RETENTION_DAYS = 30
UNKNOWN_MULTI_SENSOR_RETENTION_DAYS = 90
PRESERVE_LABELED_SENSOR_EVENTS = True
```

This keeps random drive-by noise under control while preserving useful known/watch/ignore history.

## Backfill behavior

The analyzer can backfill normalized fields from stored `raw_json`.

Current backfills include:

* `temperature_c` from Celsius or Fahrenheit raw temperature fields
* `maybe_battery` from raw `maybe_battery`

Backfills run before `load_events()`, so recovered historical values are visible in the same report run.

## Practical workflow

1. Let the system collect TPMS data.
2. Run the analyzer.
3. Open the report.
4. Review **Best Guess Vehicle Candidates** and **New Repeat Unknowns**.
5. Use the action buttons or JSON snippets to label vehicles as known/watch/ignore.
6. Re-run:

```bash
cd /config/rtl_433/tpms_analyzer
python3 analyze_tpms.py
```

7. Refresh the report.

## Backups

The analyzer can copy `vehicles.json` to:

```text
/config/rtl_433/tpms_analyzer/output/vehicles.backup.json
/config/rtl_433/tpms_analyzer/output/vehicles.backup.YYYYMMDD-HHMMSS.json
```

Back up `vehicles.json` somewhere safe. It contains the work you put into identifying vehicles.

## Suggested `.gitignore`

Avoid committing:

* TPMS logs
* SQLite databases
* generated HTML/status files
* backups
* real `vehicles.json`

Create and commit a sanitized `vehicles.example.json` instead.

## Log rotation

For the active JSONL log, use a Home Assistant shell command or automation. Prefer copy-and-truncate behavior so `rtl_433` keeps writing to the same file handle:

```bash
cp "$LOG" "$LOG.1"
: > "$LOG"
```

Avoid simply moving the active log file unless the `rtl_433` add-on is restarted afterward.

## Verification commands

Compile changed Python files:

```bash
cd /config/rtl_433/tpms_analyzer
python3 -m py_compile analyze_tpms.py analysis.py db.py report.py vehicle_map.py vehicle_map_editor.py utils.py
```

Run the analyzer:

```bash
python3 analyze_tpms.py
```

Check database counts:

```bash
python3 - <<'PY'
import sqlite3

conn = sqlite3.connect("tpms.sqlite")
print(conn.execute("select count(*), count(temperature_c), count(maybe_battery) from tpms_events").fetchone())
PY
```

## Troubleshooting

### Home Assistant returns 404 for `/local/rtl_433/tpms_report.html`

Check that the file exists:

```bash
ls -lah /config/www/rtl_433/tpms_report.html
```

If `/config/www` was newly created, restart Home Assistant Core once.

### `shell_command.analyze_tpms_log` not found

Check YAML indentation. `analyze_tpms_log` must be aligned with other shell commands:

```yaml
shell_command:
  rotate_rtl433_log: >
    sh -c '...'

  analyze_tpms_log: >
    sh -c 'cd /config/rtl_433/tpms_analyzer && python3 analyze_tpms.py'
```

Then restart Home Assistant Core.

### Report generation fails after CSS/HTML edits

Compile the report file:

```bash
cd /config/rtl_433/tpms_analyzer
python3 -m py_compile report.py
python3 analyze_tpms.py
```

If Python reports a name like `display` is undefined, CSS was likely pasted outside a triple-quoted HTML string.

### Temperature chart is empty

Check whether `temperature_c` is populated:

```bash
python3 - <<'PY'
import sqlite3

conn = sqlite3.connect("tpms.sqlite")
print(conn.execute("select count(*), count(temperature_c) from tpms_events").fetchone())
PY
```

If the second number is zero, run:

```bash
python3 analyze_tpms.py
```

The analyzer should backfill `temperature_c` from stored raw JSON if supported temperature fields are present.

### Unconfirmed Battery Signal chart is empty

Check whether `maybe_battery` is populated:

```bash
python3 - <<'PY'
import sqlite3

conn = sqlite3.connect("tpms.sqlite")
print(conn.execute("select count(*), count(maybe_battery) from tpms_events").fetchone())
PY
```

If the second number is zero, run:

```bash
python3 analyze_tpms.py
```

If it remains zero, your current rtl_433 data may not include `maybe_battery`.

### Confirmed Battery Status shows many unknown/missing values

That is normal for many TPMS decoders.

Confirmed Battery Status only uses confirmed `battery_ok` or `battery` fields. Many models do not emit those fields. `maybe_battery` is shown separately and is not interpreted as OK/Low.

### Too many cars are grouped together

Lower the busy-road window in `tpms_config.py`:

```python
PASS_WINDOW_SECONDS = 5
```

If you still see oversized raw passes, look for the **Crowded window** label in Recent Passes.

### One car is split into too many passes

Increase the pass window slightly:

```python
PASS_WINDOW_SECONDS = 10
```

Use caution on busy roads. Larger windows can accidentally merge multiple vehicles.

### Best Guess candidates have too many sensors

Check:

```python
MAX_CANDIDATE_SENSOR_COUNT = 5
```

Best Guess overlap candidates should not exceed this cap. Raw Recent Passes can still exceed it, but should be labeled as crowded windows.

## Limitations

* TPMS grouping is heuristic, not identity-proof.
* A vehicle may be heard with only one or two tire sensors depending on range, antenna placement, and traffic.
* Busy roads can produce overlapping detections from multiple vehicles.
* Some TPMS decoders expose confirmed battery status; many do not.
* `maybe_battery` is useful diagnostic data but not confirmed battery health.
* Pressure charts may mix PSI and kPa if different decoders report different units.
* Directionality is not available with a single receiver.
* The HTML report uses Plotly from a CDN unless you modify it to serve Plotly locally.

## Future improvements

Useful next additions:

* Local copy of Plotly instead of CDN.
* HA REST sensor for `/local/rtl_433/tpms_status.json`.
* Watchlist notifications.
* Database size card.
* CSV export.
* More diagnostic charts for model-specific decoder hints.
* Multi-radio support for rough directionality.
* Add-on packaging with Home Assistant Ingress.
* Optional Home Assistant integration/entities.
