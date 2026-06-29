import json
import os
import shutil
import sys
from datetime import datetime

from tpms_config import OUT_DIR, VEHICLE_MAP_PATH
from utils import normalize_sensor_id
from vehicle_map import VALID_CATEGORIES, normalize_category


VALID_ACTIONS = {"add", "update_category", "remove"}
MAX_NAME_LENGTH = 120
MAX_NOTES_LENGTH = 500
MAX_SENSOR_IDS = 12


class VehicleMapEditError(Exception):
    pass


def main():
    try:
        payload = read_payload()
        result = apply_payload(payload)
        print(json.dumps({"ok": True, **result}, indent=2))
        return 0
    except VehicleMapEditError as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2), file=sys.stderr)
        return 1
    except Exception as error:
        print(
            json.dumps({"ok": False, "error": f"Unexpected error: {error}"}, indent=2),
            file=sys.stderr,
        )
        return 1


def read_payload():
    raw_payload = sys.stdin.read().strip()

    if not raw_payload:
        raise VehicleMapEditError("No JSON payload provided on stdin.")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as error:
        raise VehicleMapEditError(f"Invalid JSON payload: {error}") from error

    if not isinstance(payload, dict):
        raise VehicleMapEditError("Payload must be a JSON object.")

    return payload


def apply_payload(payload):
    action = validate_action(payload.get("action"))
    sensor_ids = validate_sensor_ids(payload.get("sensor_ids"))
    data = read_vehicle_map()
    vehicles = data.setdefault("vehicles", [])

    if not isinstance(vehicles, list):
        raise VehicleMapEditError('vehicles.json field "vehicles" must be a list.')

    write_pre_edit_backup()

    if action == "add":
        result = add_or_update_vehicle(payload, vehicles, sensor_ids)
    elif action == "update_category":
        result = update_vehicle_category(payload, vehicles, sensor_ids)
    elif action == "remove":
        result = remove_vehicle(vehicles, sensor_ids)
    else:
        raise VehicleMapEditError(f"Unsupported action: {action}")

    write_vehicle_map(data)
    return result


def validate_action(value):
    action = clean_text(value).lower()

    if action not in VALID_ACTIONS:
        valid_actions = ", ".join(sorted(VALID_ACTIONS))
        raise VehicleMapEditError(f"Invalid action. Expected one of: {valid_actions}.")

    return action


def validate_category(value):
    category = normalize_category(value)

    if category not in VALID_CATEGORIES:
        valid_categories = ", ".join(sorted(VALID_CATEGORIES))
        raise VehicleMapEditError(
            f"Invalid category. Expected one of: {valid_categories}."
        )

    return category


def validate_name(value):
    name = clean_text(value)

    if not name:
        raise VehicleMapEditError("Name is required.")

    if len(name) > MAX_NAME_LENGTH:
        raise VehicleMapEditError(f"Name must be {MAX_NAME_LENGTH} characters or less.")

    return name


def validate_notes(value):
    notes = clean_text(value)

    if len(notes) > MAX_NOTES_LENGTH:
        raise VehicleMapEditError(
            f"Notes must be {MAX_NOTES_LENGTH} characters or less."
        )

    return notes


def validate_sensor_ids(value):
    if not isinstance(value, list):
        raise VehicleMapEditError("sensor_ids must be a list.")

    if not value:
        raise VehicleMapEditError("At least one sensor ID is required.")

    if len(value) > MAX_SENSOR_IDS:
        raise VehicleMapEditError(f"No more than {MAX_SENSOR_IDS} sensor IDs allowed.")

    normalized_ids = []

    for sensor_id in value:
        normalized_id = normalize_sensor_id(sensor_id)

        if not normalized_id:
            raise VehicleMapEditError("Sensor IDs cannot be blank.")

        normalized_ids.append(normalized_id)

    deduped_ids = list(dict.fromkeys(normalized_ids))

    if not deduped_ids:
        raise VehicleMapEditError("At least one valid sensor ID is required.")

    return deduped_ids


def clean_text(value):
    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    cleaned = value.replace("\x00", "").strip()
    return cleaned


def read_vehicle_map():
    if not VEHICLE_MAP_PATH.exists():
        return {"vehicles": []}

    try:
        data = json.loads(VEHICLE_MAP_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise VehicleMapEditError(f"vehicles.json is invalid JSON: {error}") from error

    if not isinstance(data, dict):
        raise VehicleMapEditError("vehicles.json must contain a JSON object.")

    return data


def write_pre_edit_backup():
    if not VEHICLE_MAP_PATH.exists():
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    rolling_backup_path = OUT_DIR / "vehicles.pre-edit.json"
    timestamped_backup_path = OUT_DIR / f"vehicles.pre-edit.{timestamp}.json"

    shutil.copy2(VEHICLE_MAP_PATH, rolling_backup_path)
    shutil.copy2(VEHICLE_MAP_PATH, timestamped_backup_path)


def write_vehicle_map(data):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    VEHICLE_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)

    temp_path = VEHICLE_MAP_PATH.with_name(f"{VEHICLE_MAP_PATH.name}.tmp")
    temp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, VEHICLE_MAP_PATH)


def add_or_update_vehicle(payload, vehicles, sensor_ids):
    name = validate_name(payload.get("name"))
    category = validate_category(payload.get("category"))
    notes = validate_notes(payload.get("notes"))
    match = find_vehicle_by_sensor_overlap(vehicles, sensor_ids)

    if match:
        vehicle = match["vehicle"]
        existing_ids = validate_existing_sensor_ids(vehicle)
        merged_ids = list(dict.fromkeys([*existing_ids, *sensor_ids]))

        vehicle["name"] = name
        vehicle["category"] = category
        vehicle["notes"] = notes
        vehicle["sensor_ids"] = merged_ids

        return {
            "action": "updated",
            "name": name,
            "category": category,
            "matched_sensor_ids": match["matched_sensor_ids"],
            "sensor_ids": merged_ids,
        }

    vehicle = {
        "name": name,
        "category": category,
        "notes": notes,
        "sensor_ids": sensor_ids,
    }
    vehicles.append(vehicle)

    return {
        "action": "added",
        "name": name,
        "category": category,
        "sensor_ids": sensor_ids,
    }


def update_vehicle_category(payload, vehicles, sensor_ids):
    category = validate_category(payload.get("category"))
    notes = validate_notes(payload.get("notes"))
    match = find_vehicle_by_sensor_overlap(vehicles, sensor_ids)

    if not match:
        raise VehicleMapEditError("No existing vehicle matched those sensor IDs.")

    vehicle = match["vehicle"]
    vehicle["category"] = category

    if notes:
        vehicle["notes"] = notes

    return {
        "action": "updated_category",
        "name": clean_text(vehicle.get("name")),
        "category": category,
        "matched_sensor_ids": match["matched_sensor_ids"],
    }


def remove_vehicle(vehicles, sensor_ids):
    match = find_vehicle_by_sensor_overlap(vehicles, sensor_ids)

    if not match:
        raise VehicleMapEditError("No existing vehicle matched those sensor IDs.")

    vehicle = match["vehicle"]
    vehicles.remove(vehicle)

    return {
        "action": "removed",
        "name": clean_text(vehicle.get("name")),
        "matched_sensor_ids": match["matched_sensor_ids"],
    }


def find_vehicle_by_sensor_overlap(vehicles, sensor_ids):
    requested_ids = set(sensor_ids)

    for vehicle in vehicles:
        existing_ids = set(validate_existing_sensor_ids(vehicle))
        matched_ids = sorted(requested_ids & existing_ids)

        if matched_ids:
            return {
                "vehicle": vehicle,
                "matched_sensor_ids": matched_ids,
            }

    return None


def validate_existing_sensor_ids(vehicle):
    if not isinstance(vehicle, dict):
        return []

    sensor_ids = vehicle.get("sensor_ids", [])

    if not isinstance(sensor_ids, list):
        return []

    normalized_ids = []

    for sensor_id in sensor_ids:
        normalized_id = normalize_sensor_id(sensor_id)

        if normalized_id:
            normalized_ids.append(normalized_id)

    return list(dict.fromkeys(normalized_ids))


if __name__ == "__main__":
    raise SystemExit(main())