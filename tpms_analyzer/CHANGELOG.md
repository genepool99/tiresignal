# Changelog

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
