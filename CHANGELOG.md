# Changelog

## 0.1.2

### Changed

- Vehicle-edit bridge now runs `vehicle_map_editor.py` inside the add-on container instead of on the Home Assistant host.
- `shell_command.tpms_edit_vehicle_map` now only writes a staging payload file to `/config/rtl_433/tpms_edit_payload.json`; no TPMS Python files are required on the host.
- `vehicle_map_path` no longer needs to be set to `/config/rtl_433/tpms_analyzer/vehicles.json` for vehicle labeling to work. The default `/data/vehicles.json` is sufficient.
- The add-on detects the staging payload file at startup, applies the edit, removes the file, and then runs the full analysis.

## 0.1.1

### Added

- Added `vehicle_map_path` add-on option.
- Documented Home Assistant automation setup for scheduled analysis, report refresh, and vehicle labeling.
- Documented the required `rtl_433` add-on prerequisite and JSONL output configuration.

### Changed

- TPMS Analyzer can now run as a Home Assistant add-on while sharing the existing `/config/rtl_433/tpms_analyzer/vehicles.json` vehicle map when `vehicle_map_path` is configured.
- Report refresh and scheduled analysis can be migrated to `hassio.addon_start`.

### Known limitations

- The add-on does not automatically create Home Assistant automations, scripts, shell commands, or `rtl_433` configuration.
- Vehicle labeling currently uses a Home Assistant webhook and shell command bridge. A future version may replace this with a native add-on endpoint or Ingress-backed service.
- The report is still written to `/config/www/rtl_433/tpms_report.html` and served by Home Assistant at `/local/rtl_433/tpms_report.html`; Ingress is not implemented yet.

## 0.1.0

### Added

- Initial Home Assistant add-on package.
- Add-on metadata, Dockerfile, run script, and add-on documentation.
- Environment-variable path configuration for add-on runtime paths.
- Static HTML report generation from `rtl_433` JSONL logs.
