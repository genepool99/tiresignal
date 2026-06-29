from datetime import datetime, timezone
from html import escape


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


def display_time(value):
    dt = parse_time(value)

    if not dt:
        return safe_text(value or "")

    return safe_text(dt.strftime("%Y-%m-%d %H:%M:%S"))


def display_dt(dt):
    if not dt:
        return ""

    return safe_text(dt.strftime("%Y-%m-%d %H:%M:%S"))


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
    if sensor_count >= 4 and pass_count >= 2:
        return "Very strong"

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
