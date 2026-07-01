# Changelog

## 0.3.5

### Added

- Candidate details drawer: clicking Details on any Best Guess candidate opens a side panel with pass count, sensor count, latest event date, observed models and protocols, pressure range, average RSSI/SNR, and pattern hint pills with caveats.
- Pattern hint pills on candidate rows and in the drawer show educated-guess vehicle type labels (e.g. likely TPMS, possible sedan) with distinct confidence styling.
- Add/rename modal replaces `window.prompt()` for adding candidates to the watchlist or ignoring them. The modal accepts a name (required, max 120 characters) and notes/description (optional, max 500 characters) with live character counters and inline validation.
- Edit modal for saved Known and Watch vehicles lets users update the vehicle name and notes without changing the category or sensor IDs.
- Loading overlay displayed while the report renders; dismissed automatically once the page is fully loaded.
- Back-to-top button appears after scrolling past one viewport height and smoothly scrolls back to the top.

### Changed

- Report HTML, CSS, and JavaScript are now generated from separate `report.py`, `report_css.py`, `report_js.py`, and `report_templates.py` source modules, reducing report file size and improving load time.
- Candidate sections reorganized into a Candidates tab with clearer Best Guess explanations and a dedicated Exact Repeats sub-section.
- Action URL for the vehicle-map-edit webhook is now resolved via `getServiceBaseUrl()`, which returns `http://<host>:8099` when the report is served under `/local/`, fixing button actions when accessed directly on port 8099.

## 0.3.4

### Added

- Four advanced tuning options exposed in the add-on configuration: `enable_pruning`, `unknown_sensor_retention_days`, `pass_window_seconds`, and `min_repeat_cluster_count`. All default to their previous hard-coded values, so existing installs are unaffected.

### Changed

- The report summary note now describes the active matching settings (pass window, minimum repeat count, sensor cap, and "Very strong" threshold) instead of displaying a fixed "Busy road mode is enabled" message.
- The "Very strong" confidence label is more conservative and now requires 4 or more sensors repeating across at least 5 separate passes. Candidates that previously showed "Very strong" with only 2 passes will now show "Strong" until they reach the higher bar.

## 0.3.3

### Changed

- Recommended `convert customary` in the rtl_433 example configuration so TPMS pressure values are reported in customary units such as PSI.

## 0.3.2

### Changed

- Documented the required rtl_433 add-on setup.
- Clarified that TPMS Analyzer reads from the configured rtl_433 JSONL log path.

## 0.3.0

### Added

- Persistent add-on service with report serving, refresh endpoint, vehicle-label edit endpoint, and health endpoint.
- Home Assistant Ingress/sidebar support.
- Internal scheduled refresh controlled by add-on options.

### Changed

- Made the add-on package the canonical runtime source.
- Simplified README and add-on documentation for the current service workflow.

### Removed

- Removed duplicate root Python source files.
- Removed need for external Home Assistant helper bridge.
