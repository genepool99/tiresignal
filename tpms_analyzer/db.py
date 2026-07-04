import json
import sqlite3
from datetime import datetime, timedelta, timezone

from tpms_config import (
    DB_PATH,
    ENABLE_PRUNING,
    LOG_PATH,
    PRESERVE_LABELED_SENSOR_EVENTS,
    TPMS_HINTS,
    UNKNOWN_MULTI_SENSOR_RETENTION_DAYS,
    UNKNOWN_SINGLE_SENSOR_RETENTION_DAYS,
)

from utils import as_float, first_present, normalize_sensor_id, parse_time


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tpms_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TEXT,
            sensor_id TEXT NOT NULL,
            model TEXT,
            protocol TEXT,
            pressure_kpa REAL,
            pressure_psi REAL,
            temperature_c REAL,
            battery_ok TEXT,
            maybe_battery REAL,
            rssi REAL,
            snr REAL,
            noise REAL,
            raw_json TEXT NOT NULL,
            raw_hash TEXT UNIQUE
        )
    """)

    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(tpms_events)").fetchall()
    }

    if "maybe_battery" not in columns:
        conn.execute("ALTER TABLE tpms_events ADD COLUMN maybe_battery REAL")

    conn.commit()


def is_tpms(event):
    model = str(event.get("model", "")).lower()
    protocol = str(event.get("protocol", "")).lower()
    raw = json.dumps(event, default=str).lower()

    if "tpms" in model or "tpms" in protocol or "tpms" in raw:
        return True

    return any(hint in model for hint in TPMS_HINTS)


def extract_temperature_c(event):
    celsius = as_float(first_present(
        event,
        ["temperature_C", "temperature_Celsius", "temp_C", "temp_Celsius"],
    ))

    if celsius is not None:
        return celsius

    fahrenheit = as_float(first_present(
        event,
        ["temperature_F", "temperature_Fahrenheit", "temp_F", "temp_Fahrenheit"],
    ))

    if fahrenheit is not None:
        return (fahrenheit - 32) * 5 / 9

    return None


def ingest_log(conn):
    stats = {
        "imported": 0,
        "skipped": 0,
        "malformed": 0,
        "non_tpms": 0,
        "no_sensor_id": 0,
        "duplicate": 0,
    }

    if not LOG_PATH.exists():
        print(f"Log does not exist: {LOG_PATH}")
        return stats

    with LOG_PATH.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()

            if not line:
                stats["skipped"] += 1
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                stats["skipped"] += 1
                stats["malformed"] += 1
                continue

            if isinstance(event.get("rows"), list) and "frames" in event:
                stats["skipped"] += 1
                stats["non_tpms"] += 1
                continue

            if not is_tpms(event):
                stats["skipped"] += 1
                stats["non_tpms"] += 1
                continue

            sensor_id = normalize_sensor_id(
                first_present(event, ["id", "ID", "sensor_id", "code"])
            )

            if not sensor_id:
                stats["skipped"] += 1
                stats["no_sensor_id"] += 1
                continue

            event_time = parse_time(event.get("time"))
            event_time_text = event_time.isoformat() if event_time else str(event.get("time", ""))

            pressure_kpa = as_float(first_present(event, ["pressure_kPa", "pressure_kpa"]))
            pressure_psi = as_float(first_present(event, ["pressure_PSI", "pressure_psi"]))
            temperature_c = extract_temperature_c(event)
            battery_value = first_present(event, ["battery_ok", "battery"])
            maybe_battery = as_float(first_present(event, ["maybe_battery"]))

            raw_json = json.dumps(event, sort_keys=True, separators=(",", ":"), default=str)
            raw_hash = f"{event_time_text}|{sensor_id}|{event.get('model', '')}|{raw_json}"

            try:
                conn.execute("""
                    INSERT INTO tpms_events (
                        event_time,
                        sensor_id,
                        model,
                        protocol,
                        pressure_kpa,
                        pressure_psi,
                        temperature_c,
                        battery_ok,
                        maybe_battery,
                        rssi,
                        snr,
                        noise,
                        raw_json,
                        raw_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_time_text,
                    sensor_id,
                    event.get("model"),
                    event.get("protocol"),
                    pressure_kpa,
                    pressure_psi,
                    temperature_c,
                    str(battery_value) if battery_value is not None else None,
                    maybe_battery,
                    as_float(event.get("rssi")),
                    as_float(event.get("snr")),
                    as_float(event.get("noise")),
                    raw_json,
                    raw_hash,
                ))

                stats["imported"] += 1

            except sqlite3.IntegrityError:
                stats["skipped"] += 1
                stats["duplicate"] += 1

    conn.commit()
    return stats


def backfill_temperature_c(conn):
    rows = conn.execute("""
        SELECT id, raw_json
        FROM tpms_events
        WHERE temperature_c IS NULL
          AND (
            raw_json LIKE '%temperature_C%'
            OR raw_json LIKE '%temperature_Celsius%'
            OR raw_json LIKE '%temp_C%'
            OR raw_json LIKE '%temp_Celsius%'
            OR raw_json LIKE '%temperature_F%'
            OR raw_json LIKE '%temperature_Fahrenheit%'
            OR raw_json LIKE '%temp_F%'
            OR raw_json LIKE '%temp_Fahrenheit%'
          )
    """).fetchall()

    updates = []

    for row in rows:
        try:
            event = json.loads(row["raw_json"])
        except (TypeError, json.JSONDecodeError):
            continue

        temperature_c = extract_temperature_c(event)

        if temperature_c is None:
            continue

        updates.append((temperature_c, row["id"]))

    if updates:
        conn.executemany(
            "UPDATE tpms_events SET temperature_c = ? WHERE id = ?",
            updates,
        )

    conn.commit()
    return len(updates)


def backfill_maybe_battery(conn):
    rows = conn.execute("""
        SELECT id, raw_json
        FROM tpms_events
        WHERE maybe_battery IS NULL
          AND raw_json LIKE '%maybe_battery%'
    """).fetchall()

    updates = []

    for row in rows:
        try:
            event = json.loads(row["raw_json"])
        except (TypeError, json.JSONDecodeError):
            continue

        maybe_battery = as_float(first_present(event, ["maybe_battery"]))

        if maybe_battery is None:
            continue

        updates.append((maybe_battery, row["id"]))

    if updates:
        conn.executemany(
            "UPDATE tpms_events SET maybe_battery = ? WHERE id = ?",
            updates,
        )

    conn.commit()
    return len(updates)


def load_events(conn):
    rows = conn.execute("""
        SELECT
            event_time,
            sensor_id,
            model,
            protocol,
            pressure_kpa,
            pressure_psi,
            temperature_c,
            battery_ok,
            maybe_battery,
            rssi,
            snr,
            noise,
            raw_json
        FROM tpms_events
        ORDER BY event_time ASC
    """).fetchall()

    events = []

    for row in rows:
        event_time = parse_time(row["event_time"])

        try:
            raw_packet = json.loads(row["raw_json"])
        except (json.JSONDecodeError, TypeError):
            raw_packet = {}
        if not isinstance(raw_packet, dict):
            raw_packet = {}

        events.append({
            "event_time": event_time,
            "event_time_text": row["event_time"],
            "sensor_id": row["sensor_id"],
            "model": row["model"] or "",
            "protocol": row["protocol"] or "",
            "pressure_kpa": row["pressure_kpa"],
            "pressure_psi": row["pressure_psi"],
            "temperature_c": row["temperature_c"],
            "battery_ok": row["battery_ok"],
            "maybe_battery": row["maybe_battery"],
            "rssi": row["rssi"],
            "snr": row["snr"],
            "noise": row["noise"],
            "raw": raw_packet,
        })

    return events
    
def prune_events(conn, normalized_vehicles):
    """
    Prune old raw TPMS events so the SQLite DB does not grow forever.

    Conservative behavior:
    - Preserve all events for sensors listed in vehicles.json.
    - Prune unknown single-sensor events after UNKNOWN_SINGLE_SENSOR_RETENTION_DAYS.
    - Prune unknown multi-sensor/candidate-like events after UNKNOWN_MULTI_SENSOR_RETENTION_DAYS.

    Since the DB stores raw events, not pass groups, we approximate:
    - Any unknown sensor that has only ever appeared alone/rarely is treated as road noise.
    - Unknown sensors that appear frequently are kept longer.
    """

    if not ENABLE_PRUNING:
        return {
            "enabled": False,
            "deleted": 0,
            "single_cutoff": "",
            "multi_cutoff": "",
            "preserved_labeled_sensors": 0,
        }

    now = datetime.now(timezone.utc)

    single_cutoff = now - timedelta(days=UNKNOWN_SINGLE_SENSOR_RETENTION_DAYS)
    multi_cutoff = now - timedelta(days=UNKNOWN_MULTI_SENSOR_RETENTION_DAYS)

    labeled_sensor_ids = set()

    if PRESERVE_LABELED_SENSOR_EVENTS:
        for vehicle in normalized_vehicles:
            labeled_sensor_ids.update(vehicle.get("sensor_set", set()))

    # Build observed counts per sensor. Frequent unknowns get the longer retention.
    rows = conn.execute("""
        SELECT sensor_id, COUNT(*) AS event_count
        FROM tpms_events
        GROUP BY sensor_id
    """).fetchall()

    sensor_counts = {
        row["sensor_id"]: row["event_count"]
        for row in rows
    }

    deleted = 0

    all_rows = conn.execute("""
        SELECT id, event_time, sensor_id
        FROM tpms_events
    """).fetchall()

    ids_to_delete = []

    for row in all_rows:
        event_id = row["id"]
        sensor_id = row["sensor_id"]
        event_time = parse_time(row["event_time"])

        if not event_time:
            continue

        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        if sensor_id in labeled_sensor_ids:
            continue

        event_count = sensor_counts.get(sensor_id, 0)

        # Simple heuristic:
        # - unknown sensors seen fewer than 3 times are probably drive-by noise
        # - unknown sensors seen 3+ times are more interesting and kept longer
        if event_count < 3:
            if event_time < single_cutoff:
                ids_to_delete.append(event_id)
        else:
            if event_time < multi_cutoff:
                ids_to_delete.append(event_id)

    if ids_to_delete:
        conn.executemany(
            "DELETE FROM tpms_events WHERE id = ?",
            [(event_id,) for event_id in ids_to_delete],
        )
        deleted = len(ids_to_delete)

    conn.execute("VACUUM")
    conn.commit()

    return {
        "enabled": True,
        "deleted": deleted,
        "single_cutoff": single_cutoff.isoformat(),
        "multi_cutoff": multi_cutoff.isoformat(),
        "preserved_labeled_sensors": len(labeled_sensor_ids),
    }
