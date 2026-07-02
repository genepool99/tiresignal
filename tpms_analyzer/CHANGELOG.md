# Changelog

## 0.3.12

### Added

- Added rule-based unknown-candidate tags for recurring behavior patterns:
  - "Poss. Stalker" for persistent unknown signals seen across multiple days and still recently active.
  - "Weekend Warrior" for unknown signals seen mostly on weekends.
  - "Commuter" for unknown signals seen mostly on weekdays.
- Added quick filters to the Candidates page for confidence levels and signal/pattern tags.
- Added a reusable read-only info modal for report explanations.
- Added "How this works" help links to all three candidate sections.

### Changed

- Moved the Best Guess confidence explanation out of the page body and into a modal triggered by an inline help link.
- Cleaned up candidate section intro text by moving examples and details into help modals.
- Improved inline help-link styling so it feels less like a default blue link and more like a subtle report affordance.

### Compatibility

- Kept existing report generation, candidate matching thresholds, row actions, drawer behavior, vehicle map actions, database schema, runtime paths, and output filenames unchanged.
- Candidate tags are additive and do not change existing matching or classification behavior.

## 0.3.11

### Added

- Added per-sensor Signal Quality labels based on rtl_433 RSSI/SNR averages.
- Added Signal Quality counts to the Overview summary cards.
- Added exploratory signal behavior tags for unknown candidate groups, including Loud Stranger, Quiet Regular, Radio Ghost, Close Pass Candidate, Background Regular, High-Confidence Unknown, Blink-and-Gone, and Signal Lurker.
- Added hover descriptions and accessible labels for signal behavior tags.

### Fixed

- Fixed the Signal Quality chart noise trace by passing stored noise values into the report timeline data.
- Fixed candidate drawer focus handling so closing the drawer no longer leaves focus inside an aria-hidden element.

## 0.3.10

### Fixed

- Skipped rtl_433 protocol statistics/status packets during ingest so they no longer inflate the "TPMS lines without sensor ID" count.
- Hid rtl_433 protocol statistics/status packets from the Raw Packets table so large protocol summary JSON blobs do not disrupt the report.

## 0.3.9

### Fixed

- Fixed the Refresh Report button when TireSignal is opened through Home Assistant ingress or Nabu Casa.
- Corrected client-side refresh URL construction so `/api/hassio_ingress/<token>/...` paths post to the add-on ingress refresh endpoint instead of Home Assistant's root `/api/refresh`.

### Compatibility

- Kept direct `:8099` access and `/local/rtl_433/tpms_report.html` behavior unchanged.
- Kept backend routes, add-on slug, runtime paths, output filenames, health response service identifier, and `TPMS_*` environment variables unchanged.

## 0.3.8

### Changed

- Switched generated report logo/favicon handling from embedded base64 to served PNG assets.
- Added transparent report-specific TireSignal PNG assets for the generated report.
- Added startup publishing of report PNG assets into the Home Assistant `/local/rtl_433/` report directory.
- Added strict allowlisted PNG serving for direct `:8099/report` access so the direct report and Home Assistant `/local/rtl_433/tpms_report.html` view render consistently.
- Removed the generated base64 report asset module now that report assets are served as PNG files.
- Updated TireSignal logo and favicon PNG assets to use real transparency.

### Compatibility

- Kept the existing Home Assistant add-on slug, runtime data paths, output filenames, health response service identifier, and `TPMS_*` environment variables unchanged for existing installs and automations.

## 0.3.7

### Changed

- Renamed the project branding from TPMS Analyzer to TireSignal.
- Updated Home Assistant add-on metadata, repository metadata, documentation, and generated report branding for TireSignal.
- Added TireSignal logo and icon assets for Home Assistant presentation.
- Embedded the TireSignal logo and favicon in the generated report.
- Polished the generated report header metadata styling.

### Compatibility

- Kept the existing Home Assistant add-on slug, internal paths, output filenames, health response service identifier, and `TPMS_*` environment variables unchanged for install and automation compatibility.

## 0.3.6

### Added

- Row action menus (`⋮`) for saved vehicles and candidate rows, replacing clusters of inline action buttons with a consistent Actions column.
- Edit and Delete actions for ignored vehicles.
- A visible report version in the report header.
- A "Mixed sensor types" signal on candidate rows when sensors in a group show more than one observed model or protocol. This is an explainability warning only and does not change confidence scoring.
- Hover and screen-reader descriptions for confidence, signal/pattern, and vehicle status pills.
- Visible error messages for failed direct vehicle-map actions.

### Changed

- Candidate tables now separate Confidence from Signals so behavior/caution tags no longer share the confidence cell.
- Best Guess and Exact Repeat candidate tables now use a clearer "Saved Match" column instead of separate Known Name, Category, and Known Match columns.
- Saved vehicle, ignored vehicle, and candidate row actions now live at the far-right end of each table row.
- Vehicle edit modal focus handling now restores focus more reliably after closing.
- Candidate Details drawer now closes any open row action menu before opening.
- Pill spacing was improved for stacked or wrapped tags.

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
- Clarified that TireSignal reads from the configured rtl_433 JSONL log path.

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
