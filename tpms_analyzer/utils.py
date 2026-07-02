from datetime import datetime, timezone
from html import escape

from tpms_config import STRONG_SENSOR_COUNT, VERY_STRONG_PASS_COUNT


def parse_time(value):
    if not value:
        return None

    text = str(value).strip()

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        pass

    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue

    return None


def human_dt(dt, now=None):
    if not dt:
        return "—"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    delta_seconds = (now - dt).total_seconds()
    local_dt = dt.astimezone()
    local_now = now.astimezone()

    if delta_seconds < 0:
        return local_dt.strftime("%b %-d, %Y, %-I:%M %p")

    if delta_seconds < 60:
        return "just now"

    if delta_seconds < 3600:
        minutes = int(delta_seconds // 60)
        return f"{minutes} min ago"

    if local_dt.date() == local_now.date():
        hours = int(delta_seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    return local_dt.strftime("%b %-d, %Y, %-I:%M %p")


def display_time(value):
    dt = parse_time(value)

    if not dt:
        return "—"

    return safe_text(human_dt(dt))


def display_dt(dt):
    if not dt:
        return "—"

    return safe_text(human_dt(dt))


def safe_text(value):
    if value is None:
        return ""

    return escape(str(value))


def as_float(value):
    if value in ("", None):
        return None

    try:
        return float(value)
    except Exception:
        return None


def first_present(event, keys):
    for key in keys:
        if key in event:
            return event[key]

    return None


def normalize_sensor_id(value):
    if value is None:
        return None

    return str(value).strip()


def confidence_label(sensor_count, pass_count):
    if sensor_count >= STRONG_SENSOR_COUNT and pass_count >= VERY_STRONG_PASS_COUNT:
        return "Very strong"

    if sensor_count >= STRONG_SENSOR_COUNT and pass_count >= 2:
        return "Strong"

    if sensor_count >= 3 and pass_count >= 2:
        return "Strong"

    if sensor_count >= 2 and pass_count >= 2:
        return "Possible"

    if sensor_count >= 2:
        return "Weak"

    return "Single sensor"


def signal_quality_label(avg_rssi, avg_snr, rssi_count):
    if rssi_count == 0 or avg_rssi is None:
        return "Unknown"

    if avg_snr is not None:
        if avg_snr >= 13.0:
            return "Strong"
        if avg_snr >= 9.0:
            return "Normal"
        return "Weak"

    if avg_rssi >= -4.0:
        return "Strong"
    if avg_rssi >= -8.0:
        return "Normal"
    return "Weak"


def compute_signal_tags(candidate, sensor_lookup):
    if candidate.get("category"):
        return []
    if candidate.get("known_vehicle"):
        return []

    sensor_ids = candidate.get("sensor_ids") or []
    pass_count = candidate.get("pass_count") or 0
    confidence = candidate.get("confidence") or ""
    weekend_pass_count = candidate.get("weekend_pass_count") or 0
    weekday_pass_count = candidate.get("weekday_pass_count") or 0

    sensor_rows = [
        sensor_lookup[sid]
        for sid in sensor_ids
        if sid in sensor_lookup
    ]

    qualities = [row.get("signal_quality", "Unknown") for row in sensor_rows]

    def majority_quality():
        if not qualities:
            return "Unknown"
        counts = {}
        for q in qualities:
            counts[q] = counts.get(q, 0) + 1
        return max(counts, key=counts.get)

    majority = majority_quality()

    snr_values = [row["avg_snr"] for row in sensor_rows if row.get("avg_snr") is not None]
    rssi_values = [row["avg_rssi"] for row in sensor_rows if row.get("avg_rssi") is not None]
    max_snr = max(snr_values) if snr_values else None
    max_rssi = max(rssi_values) if rssi_values else None

    first_seen = parse_time(candidate.get("first_seen"))
    last_seen = parse_time(candidate.get("last_seen"))
    duration_seconds = None
    if first_seen is not None and last_seen is not None:
        duration_seconds = max(0, (last_seen - first_seen).total_seconds())

    tags = []

    def add_tag(text, class_name, description):
        tags.append({"text": text, "class": class_name, "description": description})

    if confidence in ("Very strong", "Strong"):
        add_tag(
            "High-Confidence Unknown",
            "known",
            "Unknown group has a strong repeat pattern and may be worth mapping.",
        )

    if pass_count == 3 and duration_seconds is not None and duration_seconds < 2 * 60 * 60:
        add_tag(
            "Blink-and-Gone",
            "pattern-fluke",
            "Barely repeated and only seen in a short time window.",
        )

    if majority == "Strong" and pass_count <= 5:
        add_tag(
            "Loud Stranger",
            "info",
            "Unknown group has a strong signal but has not repeated many times.",
        )

    if (max_snr is not None and max_snr >= 15.0) or (max_rssi is not None and max_rssi >= -2.0):
        add_tag(
            "Close Pass Candidate",
            "known",
            "One or more sensors had an unusually strong decode for this receiver.",
        )

    if majority == "Weak" and pass_count >= 10:
        add_tag(
            "Quiet Regular",
            "pattern-fluke",
            "Weak signal, but it repeats often enough to be interesting.",
        )

    if majority in ("Weak", "Unknown") and pass_count >= 20:
        add_tag(
            "Background Regular",
            "pattern-fluke",
            "Weak or unknown signal that appears repeatedly over many passes.",
        )

    if majority == "Unknown":
        add_tag(
            "Radio Ghost",
            "unknown",
            "No reliable signal quality measurements were available for this group.",
        )

    if majority in ("Normal", "Weak") and 3 <= pass_count < 10:
        add_tag(
            "Signal Lurker",
            "info",
            "Mid-strength or weak unknown that has repeated but not enough to call regular.",
        )

    if (
        pass_count >= 6
        and first_seen is not None
        and last_seen is not None
        and (last_seen - first_seen).days >= 7
        and (datetime.now(timezone.utc) - last_seen).days <= 14
    ):
        add_tag(
            "Poss. Stalker",
            "pattern-stalker",
            "Repeated unknown signal seen across multiple days and still recently active.",
        )

    if pass_count >= 4 and weekend_pass_count / pass_count >= 0.70:
        add_tag(
            "Weekend Warrior",
            "pattern-weekend",
            "Unknown signal appears mostly on weekends.",
        )

    if pass_count >= 4 and weekday_pass_count / pass_count >= 0.70:
        add_tag(
            "Commuter",
            "pattern-commuter",
            "Unknown signal appears mostly on weekdays.",
        )

    return tags


def category_label(category):
    category = str(category or "").lower()

    if category == "known":
        return "Known"

    if category == "watch":
        return "Watch"

    if category == "ignore":
        return "Ignored"

    return "Unknown"
