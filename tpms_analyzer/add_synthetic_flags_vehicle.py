#!/usr/bin/env python3
"""
Add or remove a synthetic TireSignal test vehicle with decoded rtl_433 flags.

Adds:
- Vehicle: Test Vehicle - Decoded Flags
- Sensors: TESTFLAG01, TESTFLAG02, TESTFLAG03, TESTFLAG04
- Synthetic tpms_events rows with raw_json["flags"] values

Rollback:
  python3 add_synthetic_flags_vehicle.py --cleanup
"""

import argparse
import json
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


DB_PATH = Path("/config/rtl_433/tpms_analyzer/tpms.sqlite")
VEHICLES_PATH = Path("/config/rtl_433/tpms_analyzer/vehicles.json")

TEST_VEHICLE_NAME = "Test Vehicle - Decoded Flags"
TEST_SENSOR_IDS = ["TESTFLAG01", "TESTFLAG02", "TESTFLAG03", "TESTFLAG04"]
RAW_HASH_PREFIX = "synthetic-test-decoded-flags"


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def backup_file(path: Path) -> Path:
    backup_path = path.with_name(f"{path.name}.bak-{timestamp()}")
    shutil.copy2(path, backup_path)
    return backup_path


def load_vehicle_map() -> dict:
    if not VEHICLES_PATH.exists():
        return {"vehicles": []}

    with VEHICLES_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"{VEHICLES_PATH} does not contain a JSON object")

    vehicles = data.get("vehicles")
    if not isinstance(vehicles, list):
        data["vehicles"] = []

    return data


def save_vehicle_map(data: dict) -> None:
    tmp_path = VEHICLES_PATH.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)
        f.write("\n")
    tmp_path.replace(VEHICLES_PATH)


def remove_test_vehicle(data: dict) -> int:
    vehicles = data.get("vehicles", [])
    before = len(vehicles)
    data["vehicles"] = [
        vehicle for vehicle in vehicles
        if vehicle.get("name") != TEST_VEHICLE_NAME
    ]
    return before - len(data["vehicles"])


def add_test_vehicle() -> None:
    data = load_vehicle_map()
    remove_test_vehicle(data)

    data["vehicles"].append({
        "name": TEST_VEHICLE_NAME,
        "category": "watch",
        "notes": "Temporary synthetic test vehicle for decoded flags drawer testing.",
        "sensor_ids": TEST_SENSOR_IDS,
    })

    save_vehicle_map(data)


def delete_synthetic_events(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        "DELETE FROM tpms_events WHERE raw_hash LIKE ?",
        (f"{RAW_HASH_PREFIX}%",),
    )
    return cur.rowcount


def insert_synthetic_events(conn: sqlite3.Connection) -> int:
    base_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=20)

    # 28 events total:
    # - 24 with flags
    # - 4 without flags, so the drawer can show Missing > 0
    flag_sequence = [
        "0", "0", "0", "0", "0", "0",
        "12", "12", "12", "12",
        "26", "26",
    ]

    rows = []
    row_index = 0

    for sensor_index, sensor_id in enumerate(TEST_SENSOR_IDS):
        for event_index, flag_value in enumerate(flag_sequence):
            event_time = base_time + timedelta(
                minutes=event_index,
                seconds=sensor_index * 8,
            )

            pressure_psi = 34.0 + sensor_index + (event_index * 0.05)
            pressure_kpa = round(pressure_psi * 6.894757, 2)
            temperature_c = 21.0 + sensor_index

            raw = {
                "time": event_time.isoformat(),
                "model": "Test-TPMS",
                "protocol": "999",
                "id": sensor_id,
                "pressure_kPa": pressure_kpa,
                "pressure_PSI": round(pressure_psi, 2),
                "temperature_C": temperature_c,
                "flags": flag_value,
                "mic": "CRC",
            }

            rows.append((
                event_time.isoformat(),
                sensor_id,
                "Test-TPMS",
                "999",
                pressure_kpa,
                round(pressure_psi, 2),
                temperature_c,
                "1",
                None,
                -45.0 - sensor_index,
                20.0,
                -70.0,
                json.dumps(raw, sort_keys=True),
                f"{RAW_HASH_PREFIX}|flags|{row_index}",
            ))
            row_index += 1

        # One event per sensor with no flags to exercise the Missing count.
        event_time = base_time + timedelta(minutes=30, seconds=sensor_index * 8)
        pressure_psi = 34.0 + sensor_index
        pressure_kpa = round(pressure_psi * 6.894757, 2)

        raw_without_flags = {
            "time": event_time.isoformat(),
            "model": "Test-TPMS",
            "protocol": "999",
            "id": sensor_id,
            "pressure_kPa": pressure_kpa,
            "pressure_PSI": round(pressure_psi, 2),
            "temperature_C": 22.0 + sensor_index,
            "mic": "CRC",
        }

        rows.append((
            event_time.isoformat(),
            sensor_id,
            "Test-TPMS",
            "999",
            pressure_kpa,
            round(pressure_psi, 2),
            22.0 + sensor_index,
            "1",
            None,
            -47.0 - sensor_index,
            19.5,
            -70.0,
            json.dumps(raw_without_flags, sort_keys=True),
            f"{RAW_HASH_PREFIX}|missing|{sensor_index}",
        ))

    conn.executemany(
        """
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
        """,
        rows,
    )

    return len(rows)


def add() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)
    if not VEHICLES_PATH.exists():
        raise FileNotFoundError(VEHICLES_PATH)

    db_backup = backup_file(DB_PATH)
    vehicles_backup = backup_file(VEHICLES_PATH)

    with sqlite3.connect(DB_PATH) as conn:
        deleted = delete_synthetic_events(conn)
        inserted = insert_synthetic_events(conn)
        conn.commit()

    add_test_vehicle()

    print("Added synthetic decoded-flags test data.")
    print(f"DB backup:       {db_backup}")
    print(f"Vehicle backup:  {vehicles_backup}")
    print(f"Deleted old synthetic rows: {deleted}")
    print(f"Inserted synthetic rows:    {inserted}")
    print(f"Vehicle name: {TEST_VEHICLE_NAME}")
    print(f"Sensor IDs: {', '.join(TEST_SENSOR_IDS)}")
    print()
    print("Next: regenerate the TireSignal report and open Details for the test vehicle.")
    print()
    print("Cleanup command:")
    print(f"  python3 {Path(__file__).name} --cleanup")


def cleanup() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)
    if not VEHICLES_PATH.exists():
        raise FileNotFoundError(VEHICLES_PATH)

    db_backup = backup_file(DB_PATH)
    vehicles_backup = backup_file(VEHICLES_PATH)

    with sqlite3.connect(DB_PATH) as conn:
        deleted_rows = delete_synthetic_events(conn)
        conn.commit()

    data = load_vehicle_map()
    removed_vehicles = remove_test_vehicle(data)
    save_vehicle_map(data)

    print("Removed synthetic decoded-flags test data.")
    print(f"DB backup before cleanup:      {db_backup}")
    print(f"Vehicle backup before cleanup: {vehicles_backup}")
    print(f"Deleted synthetic DB rows:     {deleted_rows}")
    print(f"Removed vehicle entries:       {removed_vehicles}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove the synthetic vehicle and synthetic DB rows.",
    )
    args = parser.parse_args()

    if args.cleanup:
        cleanup()
    else:
        add()


if __name__ == "__main__":
    main()