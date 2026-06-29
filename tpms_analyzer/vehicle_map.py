import json
from tpms_config import VEHICLE_MAP_PATH


DEFAULT_VEHICLE_MAP = {
    "vehicles": [
        {
            "name": "Example Known Vehicle",
            "category": "known",
            "notes": "Replace these IDs with real TPMS IDs once identified.",
            "sensor_ids": [
                "12345678",
                "23456789",
                "34567890",
                "45678901"
            ]
        }
    ]
}


VALID_CATEGORIES = {"known", "watch", "ignore"}


def create_default_vehicle_map_if_missing():
    if VEHICLE_MAP_PATH.exists():
        return

    VEHICLE_MAP_PATH.write_text(
        json.dumps(DEFAULT_VEHICLE_MAP, indent=2),
        encoding="utf-8",
    )


def normalize_category(value):
    value = str(value or "known").strip().lower()
    if value not in VALID_CATEGORIES:
        return "known"
    return value


def load_vehicle_map():
    create_default_vehicle_map_if_missing()

    try:
        data = json.loads(VEHICLE_MAP_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Could not read vehicle map {VEHICLE_MAP_PATH}: {exc}")
        return [], {}, []

    raw_vehicles = data.get("vehicles", [])
    sensor_to_vehicle = {}
    normalized_vehicles = []

    for vehicle in raw_vehicles:
        name = str(vehicle.get("name", "Unnamed vehicle")).strip()
        category = normalize_category(vehicle.get("category", "known"))
        notes = str(vehicle.get("notes", "")).strip()
        sensor_ids = [
            str(sensor_id).strip()
            for sensor_id in vehicle.get("sensor_ids", [])
            if str(sensor_id).strip()
        ]

        if not sensor_ids:
            continue

        normalized = {
            "name": name,
            "category": category,
            "notes": notes,
            "sensor_ids": sensor_ids,
            "sensor_set": set(sensor_ids),
        }

        normalized_vehicles.append(normalized)

        for sensor_id in sensor_ids:
            sensor_to_vehicle[sensor_id] = {
                "name": name,
                "category": category,
                "notes": notes,
            }

    return raw_vehicles, sensor_to_vehicle, normalized_vehicles


def match_known_vehicle(sensor_ids, normalized_vehicles):
    observed = set(sensor_ids)

    if not observed:
        return empty_match()

    best = None

    for vehicle in normalized_vehicles:
        overlap = observed.intersection(vehicle["sensor_set"])
        matched = len(overlap)

        if matched == 0:
            continue

        total = len(vehicle["sensor_set"])
        ratio = matched / total if total else 0

        candidate = {
            "name": vehicle["name"],
            "category": vehicle["category"],
            "notes": vehicle.get("notes", ""),
            "matched": matched,
            "total": total,
            "ratio": ratio,
        }

        if best is None:
            best = candidate
            continue

        if (candidate["matched"], candidate["ratio"]) > (best["matched"], best["ratio"]):
            best = candidate

    if not best:
        return empty_match()

    if best["matched"] >= 4:
        confidence = "Confirmed"
    elif best["matched"] >= 3:
        confidence = "Likely"
    elif best["matched"] >= 2:
        confidence = "Possible"
    else:
        confidence = "Weak"

    best["confidence"] = confidence
    return best


def empty_match():
    return {
        "name": "",
        "category": "",
        "notes": "",
        "matched": 0,
        "total": 0,
        "ratio": 0,
        "confidence": "",
    }
