import os
from pathlib import Path


def env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default))


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


LOG_PATH = env_path("TPMS_LOG_PATH", "/config/rtl_433/logs/rtl_433.jsonl")

BASE_DIR = env_path("TPMS_BASE_DIR", "/config/rtl_433/tpms_analyzer")
OUT_DIR = env_path("TPMS_OUT_DIR", str(BASE_DIR / "output"))
DB_PATH = env_path("TPMS_DB_PATH", str(BASE_DIR / "tpms.sqlite"))
VEHICLE_MAP_PATH = env_path("TPMS_VEHICLE_MAP_PATH", str(BASE_DIR / "vehicles.json"))

# Retention / pruning
ENABLE_PRUNING = True

# Unknown single-sensor road noise gets old fast.
UNKNOWN_SINGLE_SENSOR_RETENTION_DAYS = 180

# Unknown multi-sensor candidates are more useful, so keep longer.
UNKNOWN_MULTI_SENSOR_RETENTION_DAYS = 180

# Never prune events tied to known/watch/ignore vehicles.
PRESERVE_LABELED_SENSOR_EVENTS = True

SERVICE_PORT = env_int("TPMS_SERVICE_PORT", 8099)

# Home Assistant serves /config/www as /local
REPORT_PATH = env_path("TPMS_REPORT_PATH", "/config/www/rtl_433/tpms_report.html")
STATUS_PATH = env_path("TPMS_STATUS_PATH", "/config/www/rtl_433/tpms_status.json")

# Busy road mode: short window prevents merging several passing cars.
PASS_WINDOW_SECONDS = 5

MIN_REPEAT_CLUSTER_COUNT = 3
POSSIBLE_SENSOR_COUNT = 3
STRONG_SENSOR_COUNT = 4
MAX_CANDIDATE_SENSOR_COUNT = 5

MAX_RECENT_PASSES = 500
MAX_RECENT_EVENTS = 750

TPMS_HINTS = [
    "tpms",
    "schrader",
    "toyota",
    "ford",
    "gm",
    "chevrolet",
    "subaru",
    "nissan",
    "hyundai",
    "kia",
    "porsche",
    "citroen",
    "renault",
]


def ensure_dirs():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)