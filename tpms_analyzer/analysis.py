from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from tpms_config import (
    MAX_RECENT_EVENTS,
    MAX_RECENT_PASSES,
    MAX_CANDIDATE_SENSOR_COUNT,
    MIN_REPEAT_CLUSTER_COUNT,
    PASS_WINDOW_SECONDS,
    POSSIBLE_SENSOR_COUNT,
)
from utils import confidence_label, signal_quality_label
from vehicle_map import match_known_vehicle


def summarize_sensors(events, sensor_to_vehicle):
    by_id = defaultdict(list)

    for event in events:
        by_id[event["sensor_id"]].append(event)

    summaries = []

    for sensor_id, rows in by_id.items():
        times = [r["event_time"] for r in rows if r["event_time"]]
        models = sorted(set(r["model"] for r in rows if r["model"]))

        pressures_psi = [r["pressure_psi"] for r in rows if r["pressure_psi"] is not None]
        pressures_kpa = [r["pressure_kpa"] for r in rows if r["pressure_kpa"] is not None]
        temps = [r["temperature_c"] for r in rows if r["temperature_c"] is not None]
        rssi_values = [r["rssi"] for r in rows if r["rssi"] is not None]
        snr_values = [r["snr"] for r in rows if r["snr"] is not None]
        avg_rssi = avg(rssi_values)
        avg_snr = avg(snr_values)

        vehicle_info = sensor_to_vehicle.get(sensor_id, {})

        summaries.append({
            "sensor_id": sensor_id,
            "vehicle_name": vehicle_info.get("name", ""),
            "category": vehicle_info.get("category", ""),
            "count": len(rows),
            "first_seen": min(times).isoformat() if times else "",
            "last_seen": max(times).isoformat() if times else "",
            "models": ", ".join(models),
            "avg_pressure_psi": avg(pressures_psi),
            "avg_pressure_kpa": avg(pressures_kpa),
            "avg_temperature_c": avg(temps),
            "avg_rssi": avg_rssi,
            "avg_snr": avg_snr,
            "signal_quality": signal_quality_label(avg_rssi, avg_snr, len(rssi_values)),
        })

    summaries.sort(key=lambda r: r["last_seen"], reverse=True)
    return summaries


def avg(values):
    if not values:
        return None

    return round(sum(values) / len(values), 2)


def group_vehicle_passes(events, normalized_vehicles, window_seconds=PASS_WINDOW_SECONDS):
    timed = [e for e in events if e["event_time"]]
    timed.sort(key=lambda e: e["event_time"])

    groups = []
    current = []

    for event in timed:
        if not current:
            current = [event]
            continue

        gap = (event["event_time"] - current[-1]["event_time"]).total_seconds()

        if gap <= window_seconds:
            current.append(event)
        else:
            groups.append(current)
            current = [event]

    if current:
        groups.append(current)

    vehicle_passes = []

    for group in groups:
        sensor_ids = sorted(set(e["sensor_id"] for e in group))

        if not sensor_ids:
            continue

        start = min(e["event_time"] for e in group)
        end = max(e["event_time"] for e in group)

        known_match = match_known_vehicle(sensor_ids, normalized_vehicles)

        vehicle_passes.append({
            "start": start,
            "end": end,
            "duration_seconds": int((end - start).total_seconds()),
            "sensor_ids": sensor_ids,
            "sensor_count": len(sensor_ids),
            "event_count": len(group),
            "models": sorted(set(e["model"] for e in group if e["model"])),
            "candidate_key": ",".join(sensor_ids),
            "known_vehicle": known_match["name"],
            "category": known_match["category"],
            "known_match": known_match,
            "confidence": confidence_label(len(sensor_ids), 1),
        })

    vehicle_passes.sort(key=lambda r: r["start"], reverse=True)
    return vehicle_passes


def classify_presence_event(vehicle_pass):
    """
    Classify a single vehicle_pass into a mutually exclusive presence
    event_type: "known" takes priority, then "lingering", else "pass_by".
    """

    vehicle_pass = vehicle_pass or {}
    known_vehicle = vehicle_pass.get("known_vehicle")
    duration_seconds = vehicle_pass.get("duration_seconds") or 0

    if known_vehicle:
        return "known"

    if duration_seconds >= 300:
        return "lingering"

    return "pass_by"


def normalized_vehicle_passes(vehicle_passes):
    """
    Normalize vehicle_passes for the presence/traffic helpers below:
    skips falsy entries and entries without a usable start timestamp,
    normalizes naive start/end datetimes to UTC, and falls back to
    start for a missing end. Returns a new list of shallow-copied
    dicts; the input list/dicts are left untouched.
    """

    normalized = []

    for vehicle_pass in vehicle_passes or []:
        start = vehicle_pass.get("start") if vehicle_pass else None

        if not start:
            continue

        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        end = vehicle_pass.get("end") or start

        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        normalized.append({**vehicle_pass, "start": start, "end": end})

    return normalized


def summarize_presence(vehicle_passes, now=None):
    """
    Derive a rolling 24-hour presence/traffic summary from vehicle_passes.

    Pure and read-only: takes the same vehicle_passes shape produced by
    group_vehicle_passes() and does not query the database or touch
    rendering. Passes without a usable start timestamp are ignored.
    """

    valid_passes = normalized_vehicle_passes(vehicle_passes)

    if now is None:
        latest = None

        for vehicle_pass in valid_passes:
            candidate = max(vehicle_pass["start"], vehicle_pass["end"])
            if latest is None or candidate > latest:
                latest = candidate

        now = latest or datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    window_start = now - timedelta(hours=24)

    window_passes = [
        vehicle_pass for vehicle_pass in valid_passes
        if window_start <= vehicle_pass["start"] <= now
    ]

    known_24h = 0
    unknown_24h = 0
    lingering_24h = 0
    hour_counts = Counter()

    for vehicle_pass in window_passes:
        known_vehicle = vehicle_pass.get("known_vehicle")
        duration_seconds = vehicle_pass.get("duration_seconds") or 0

        if known_vehicle:
            known_24h += 1
        else:
            unknown_24h += 1

        if duration_seconds >= 300:
            lingering_24h += 1

        hour_counts[vehicle_pass["start"].astimezone().strftime("%H:00")] += 1

    if hour_counts:
        busiest_hour, busiest_hour_count = sorted(
            hour_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[0]
    else:
        busiest_hour, busiest_hour_count = None, 0

    window_passes.sort(key=lambda p: p["start"], reverse=True)

    recent_events = []

    for vehicle_pass in window_passes[:25]:
        sensor_ids = vehicle_pass.get("sensor_ids") or []
        duration_seconds = vehicle_pass.get("duration_seconds") or 0
        known_vehicle = vehicle_pass.get("known_vehicle") or ""
        sensor_count = vehicle_pass.get("sensor_count")

        if sensor_count is None:
            sensor_count = len(sensor_ids)

        event_type = classify_presence_event(vehicle_pass)

        recent_events.append({
            "start": vehicle_pass["start"].isoformat(),
            "end": vehicle_pass["end"].isoformat(),
            "duration_seconds": duration_seconds,
            "sensor_ids": sensor_ids,
            "sensor_count": sensor_count,
            "known_vehicle": known_vehicle,
            "category": vehicle_pass.get("category") or "",
            "confidence": vehicle_pass.get("confidence") or "",
            "event_type": event_type,
        })

    return {
        "total_24h": len(window_passes),
        "known_24h": known_24h,
        "unknown_24h": unknown_24h,
        "lingering_24h": lingering_24h,
        "busiest_hour": busiest_hour,
        "busiest_hour_count": busiest_hour_count,
        "recent_events": recent_events,
    }


def build_presence_timeline(vehicle_passes, now=None):
    """
    Build a fixed-size, trailing 24-hour hourly bucket summary from
    vehicle_passes, for a static Presence Timeline view.

    Pure and read-only: same input shape and windowing behavior as
    summarize_presence(). Always returns exactly 24 buckets, oldest to
    newest, regardless of how many passes fall in the window.
    """

    valid_passes = normalized_vehicle_passes(vehicle_passes)

    if now is None:
        latest = None

        for vehicle_pass in valid_passes:
            candidate = max(vehicle_pass["start"], vehicle_pass["end"])
            if latest is None or candidate > latest:
                latest = candidate

        now = latest or datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    window_start = now - timedelta(hours=24)

    buckets = []
    buckets_by_hour = {}

    for offset in range(24):
        slot_start = window_start + timedelta(hours=offset)
        hour_label = slot_start.astimezone().strftime("%H:00")

        bucket = {
            "hour": hour_label,
            "known": 0,
            "lingering": 0,
            "pass_by": 0,
            "total": 0,
        }

        buckets.append(bucket)
        buckets_by_hour.setdefault(hour_label, bucket)

    for vehicle_pass in valid_passes:
        start = vehicle_pass["start"]

        if not (window_start <= start <= now):
            continue

        hour_label = start.astimezone().strftime("%H:00")
        bucket = buckets_by_hour.get(hour_label)

        if bucket is None:
            continue

        event_type = classify_presence_event(vehicle_pass)

        if event_type not in ("known", "lingering", "pass_by"):
            event_type = "pass_by"

        bucket[event_type] += 1
        bucket["total"] += 1

    return {
        "window_start": window_start.isoformat(),
        "window_end": now.isoformat(),
        "buckets": buckets,
    }


def build_traffic_heatmap(vehicle_passes, now=None, days=7):
    """
    Build a fixed-size, trailing N-day day/hour traffic heatmap from
    vehicle_passes, using server-side aggregation (not raw events, and
    not the capped client-side timeline_points).

    Pure and read-only: same normalization/windowing approach as
    summarize_presence() and build_presence_timeline(). Always returns
    exactly days * 24 cells, oldest to newest, regardless of how many
    passes fall in the window.
    """

    if not isinstance(days, int) or isinstance(days, bool) or days < 1:
        days = 7

    valid_passes = normalized_vehicle_passes(vehicle_passes)

    if now is None:
        latest = None

        for vehicle_pass in valid_passes:
            candidate = max(vehicle_pass["start"], vehicle_pass["end"])
            if latest is None or candidate > latest:
                latest = candidate

        now = latest or datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    window_start = now - timedelta(days=days)

    cells = []
    cells_by_key = {}

    for offset in range(days * 24):
        slot_start = (window_start + timedelta(hours=offset)).astimezone()
        date_label = slot_start.strftime("%Y-%m-%d")
        weekday_label = slot_start.strftime("%a")
        hour_label = slot_start.strftime("%H:00")
        key = (date_label, hour_label)

        cell = {
            "date": date_label,
            "weekday": weekday_label,
            "hour": hour_label,
            "known": 0,
            "lingering": 0,
            "pass_by": 0,
            "total": 0,
        }

        cells.append(cell)
        cells_by_key.setdefault(key, cell)

    for vehicle_pass in valid_passes:
        start = vehicle_pass["start"]

        if not (window_start <= start <= now):
            continue

        local_start = start.astimezone()
        key = (local_start.strftime("%Y-%m-%d"), local_start.strftime("%H:00"))
        cell = cells_by_key.get(key)

        if cell is None:
            continue

        event_type = classify_presence_event(vehicle_pass)

        if event_type not in ("known", "lingering", "pass_by"):
            event_type = "pass_by"

        cell[event_type] += 1
        cell["total"] += 1

    return {
        "window_start": window_start.isoformat(),
        "window_end": now.isoformat(),
        "days": days,
        "cells": cells,
    }


def summarize_exact_candidates(vehicle_passes, normalized_vehicles):
    by_key = defaultdict(list)

    for vehicle_pass in vehicle_passes:
        if vehicle_pass["sensor_count"] >= POSSIBLE_SENSOR_COUNT:
            by_key[vehicle_pass["candidate_key"]].append(vehicle_pass)

    rows = []

    for key, passes in by_key.items():
        if len(passes) < MIN_REPEAT_CLUSTER_COUNT:
            continue

        first = min(p["start"] for p in passes)
        last = max(p["end"] for p in passes)
        sensor_ids = key.split(",")

        known_match = match_known_vehicle(sensor_ids, normalized_vehicles)

        weekend_pass_count = sum(1 for p in passes if p["start"].astimezone().weekday() >= 5)
        weekday_pass_count = len(passes) - weekend_pass_count

        rows.append({
            "candidate_key": key,
            "sensor_ids": sensor_ids,
            "sensor_count": len(sensor_ids),
            "pass_count": len(passes),
            "first_seen": first.isoformat(),
            "last_seen": last.isoformat(),
            "known_vehicle": known_match["name"],
            "category": known_match["category"],
            "known_match": known_match,
            "confidence": confidence_label(len(sensor_ids), len(passes)),
            "weekend_pass_count": weekend_pass_count,
            "weekday_pass_count": weekday_pass_count,
        })

    rows.sort(key=lambda r: (r["pass_count"], r["sensor_count"], r["last_seen"]), reverse=True)
    return rows


def summarize_overlap_candidates(vehicle_passes, normalized_vehicles):
    multi_sensor_passes = [
        p for p in vehicle_passes
        if (
            p["sensor_count"] >= POSSIBLE_SENSOR_COUNT
            and p["sensor_count"] <= MAX_CANDIDATE_SENSOR_COUNT
        )
    ]

    clusters = []

    for vehicle_pass in multi_sensor_passes:
        current_set = set(vehicle_pass["sensor_ids"])
        placed = False

        for cluster in clusters:
            overlap = current_set.intersection(cluster["sensor_set"])
            merged_sensor_ids = cluster["sensor_set"] | current_set

            if (
                len(overlap) >= 2
                and len(merged_sensor_ids) <= MAX_CANDIDATE_SENSOR_COUNT
            ):
                cluster["passes"].append(vehicle_pass)
                cluster["sensor_set"] = merged_sensor_ids
                placed = True
                break

        if not placed:
            clusters.append({
                "sensor_set": set(current_set),
                "passes": [vehicle_pass],
            })

    rows = []

    for cluster in clusters:
        passes = cluster["passes"]

        if len(passes) < MIN_REPEAT_CLUSTER_COUNT:
            continue

        sensor_ids = sorted(cluster["sensor_set"])
        first = min(p["start"] for p in passes)
        last = max(p["end"] for p in passes)

        known_match = match_known_vehicle(sensor_ids, normalized_vehicles)

        weekend_pass_count = sum(1 for p in passes if p["start"].astimezone().weekday() >= 5)
        weekday_pass_count = len(passes) - weekend_pass_count

        rows.append({
            "sensor_ids": sensor_ids,
            "sensor_count": len(sensor_ids),
            "pass_count": len(passes),
            "first_seen": first.isoformat(),
            "last_seen": last.isoformat(),
            "known_vehicle": known_match["name"],
            "category": known_match["category"],
            "known_match": known_match,
            "confidence": confidence_label(len(sensor_ids), len(passes)),
            "weekend_pass_count": weekend_pass_count,
            "weekday_pass_count": weekday_pass_count,
        })

    rows.sort(key=lambda r: (r["pass_count"], r["sensor_count"], r["last_seen"]), reverse=True)
    return rows


def summarize_known_vehicles(vehicle_passes, normalized_vehicles):
    rows = []

    for vehicle in normalized_vehicles:
        if vehicle["category"] == "ignore":
            continue

        matching_passes = []

        for vehicle_pass in vehicle_passes:
            observed = set(vehicle_pass["sensor_ids"])
            overlap = observed.intersection(vehicle["sensor_set"])

            if overlap:
                matching_passes.append({
                    **vehicle_pass,
                    "matched_count": len(overlap),
                    "total_count": len(vehicle["sensor_set"]),
                })

        if not matching_passes:
            rows.append({
                "name": vehicle["name"],
                "category": vehicle["category"],
                "notes": vehicle["notes"],
                "last_seen": "",
                "first_seen": "",
                "seen_count": 0,
                "seen_today": 0,
                "best_match": "",
                "sensor_ids": vehicle["sensor_ids"],
            })
            continue

        times = [p["start"] for p in matching_passes]
        today = datetime.now().astimezone().date()

        seen_today = sum(
            1 for p in matching_passes
            if p["start"].astimezone().date() == today
        )

        best = max(
            matching_passes,
            key=lambda p: (p["matched_count"], p["start"]),
        )

        rows.append({
            "name": vehicle["name"],
            "category": vehicle["category"],
            "notes": vehicle["notes"],
            "last_seen": max(times).isoformat(),
            "first_seen": min(times).isoformat(),
            "seen_count": len(matching_passes),
            "seen_today": seen_today,
            "best_match": f'{best["matched_count"]}/{best["total_count"]} sensors',
            "sensor_ids": vehicle["sensor_ids"],
        })

    rows.sort(key=lambda r: r["last_seen"], reverse=True)
    return rows


def find_new_unknown_candidates(overlap_candidates):
    rows = []

    for candidate in overlap_candidates:
        if candidate.get("known_vehicle"):
            continue

        if candidate["pass_count"] < MIN_REPEAT_CLUSTER_COUNT:
            continue

        rows.append(candidate)

    return rows[:50]


def daily_counts(events):
    counts = Counter()

    for event in events:
        if event["event_time"]:
            counts[event["event_time"].strftime("%Y-%m-%d")] += 1

    return [{"date": date, "count": count} for date, count in sorted(counts.items())]


def hourly_counts(events):
    counts = Counter()

    for event in events:
        if event["event_time"]:
            counts[event["event_time"].strftime("%H:00")] += 1

    hours = [f"{h:02d}:00" for h in range(24)]
    return [{"hour": hour, "count": counts.get(hour, 0)} for hour in hours]


def recent_events(events):
    return sorted(
        events,
        key=lambda e: e["event_time"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )[:MAX_RECENT_EVENTS]


def recent_passes(vehicle_passes):
    return vehicle_passes[:MAX_RECENT_PASSES]


DECODED_FIELD_NAMES = ["moving", "flags", "state", "status", "learn", "mic"]
DECODED_FIELD_TOP_VALUES = 8


def summarize_decoded_fields(events):
    field_present_counts = {name: 0 for name in DECODED_FIELD_NAMES}
    field_value_counts = {name: Counter() for name in DECODED_FIELD_NAMES}
    total_events = 0

    for event in events:
        total_events += 1
        raw = event.get("raw") if isinstance(event.get("raw"), dict) else {}

        for name in DECODED_FIELD_NAMES:
            if name not in raw:
                continue
            value = raw[name]
            if value is None or value == "":
                continue
            field_present_counts[name] += 1
            field_value_counts[name][str(value)] += 1

    fields = []
    for name in DECODED_FIELD_NAMES:
        present_count = field_present_counts[name]
        values = sorted(
            field_value_counts[name].items(),
            key=lambda item: (-item[1], item[0]),
        )[:DECODED_FIELD_TOP_VALUES]

        fields.append({
            "name": name,
            "present_count": present_count,
            "missing_count": total_events - present_count,
            "values": [{"value": value, "count": count} for value, count in values],
        })

    return {
        "total_events": total_events,
        "fields": fields,
    }
