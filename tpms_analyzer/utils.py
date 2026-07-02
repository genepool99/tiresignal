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


def category_label(category):
    category = str(category or "").lower()

    if category == "known":
        return "Known"

    if category == "watch":
        return "Watch"

    if category == "ignore":
        return "Ignored"

    return "Unknown"
