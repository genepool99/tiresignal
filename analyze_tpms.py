#!/usr/bin/env python3

import json
from datetime import datetime
import shutil
from analysis import (
    daily_counts,
    find_new_unknown_candidates,
    group_vehicle_passes,
    hourly_counts,
    recent_events,
    recent_passes,
    summarize_exact_candidates,
    summarize_known_vehicles,
    summarize_overlap_candidates,
    summarize_sensors,
)
from db import backfill_temperature_c, connect_db, ingest_log, init_db, load_events, prune_events
from report import write_report
from tpms_config import DB_PATH, OUT_DIR, REPORT_PATH, STATUS_PATH, VEHICLE_MAP_PATH, ensure_dirs
from vehicle_map import load_vehicle_map


def main():
    ensure_dirs()

    vehicles, sensor_to_vehicle, normalized_vehicles = load_vehicle_map()

    conn = connect_db()
    init_db(conn)

    ingest_stats = ingest_log(conn)
    prune_stats = prune_events(conn, normalized_vehicles)
    temperature_backfilled = backfill_temperature_c(conn)
    events = load_events(conn)

    sensor_summaries = summarize_sensors(events, sensor_to_vehicle)
    vehicle_passes = group_vehicle_passes(events, normalized_vehicles)

    exact_candidate_summaries = summarize_exact_candidates(
        vehicle_passes,
        normalized_vehicles,
    )

    overlap_candidate_summaries = summarize_overlap_candidates(
        vehicle_passes,
        normalized_vehicles,
    )

    known_vehicle_summaries = summarize_known_vehicles(
        vehicle_passes,
        normalized_vehicles,
    )

    new_unknown_candidates = find_new_unknown_candidates(
        overlap_candidate_summaries,
    )

    context = {
        "vehicles": vehicles,
        "events": events,
        "sensor_summaries": sensor_summaries,
        "vehicle_passes": vehicle_passes,
        "recent_passes": recent_passes(vehicle_passes),
        "recent_events": recent_events(events),
        "exact_candidate_summaries": exact_candidate_summaries,
        "overlap_candidate_summaries": overlap_candidate_summaries,
        "known_vehicle_summaries": known_vehicle_summaries,
        "new_unknown_candidates": new_unknown_candidates,
        "daily_counts": daily_counts(events),
        "hourly_counts": hourly_counts(events),
        "ingest_stats": ingest_stats,
        "prune_stats": prune_stats,
    }

    write_report(context)
    
    status = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "total_events": len(events),
        "unique_sensors": len(sensor_summaries),
        "detected_passes": len(vehicle_passes),
        "exact_repeat_candidates": len(exact_candidate_summaries),
        "overlap_candidates": len(overlap_candidate_summaries),
        "known_watch_vehicle_summaries": len(known_vehicle_summaries),
        "new_unknown_candidates": len(new_unknown_candidates),
        "imported_this_run": ingest_stats.get("imported", 0),
        "pruned_this_run": prune_stats.get("deleted", 0) if "prune_stats" in locals() else 0,
        "last_error": "",
        "report_path": str(REPORT_PATH),
        "database_path": str(DB_PATH),
        "vehicle_map_path": str(VEHICLE_MAP_PATH),
    }
    
    STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
    
    if VEHICLE_MAP_PATH.exists():
        backup_path = OUT_DIR / "vehicles.backup.json"
        timestamped_backup_path = OUT_DIR / f"vehicles.backup.{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        shutil.copy2(VEHICLE_MAP_PATH, backup_path)
        shutil.copy2(VEHICLE_MAP_PATH, timestamped_backup_path)

    print(f"Imported new events: {ingest_stats.get('imported', 0)}")
    print(f"Skipped total: {ingest_stats.get('skipped', 0)}")
    print(f"Duplicates: {ingest_stats.get('duplicate', 0)}")
    print(f"Non-TPMS lines: {ingest_stats.get('non_tpms', 0)}")
    print(f"Malformed JSON lines: {ingest_stats.get('malformed', 0)}")
    print(f"TPMS lines without sensor ID: {ingest_stats.get('no_sensor_id', 0)}")

    if temperature_backfilled > 0:
        print(f"Backfilled temperature_c for {temperature_backfilled} TPMS events.")
    print(f"Total TPMS events in DB: {len(events)}")
    print(f"Unique TPMS IDs: {len(sensor_summaries)}")
    print(f"Detected passes: {len(vehicle_passes)}")
    print(f"Exact repeat candidates: {len(exact_candidate_summaries)}")
    print(f"Overlap candidates: {len(overlap_candidate_summaries)}")
    print(f"Known/watch vehicle summaries: {len(known_vehicle_summaries)}")
    print(f"New unknown candidates: {len(new_unknown_candidates)}")
    print(f"SQLite DB: {DB_PATH}")
    print(f"Vehicle map: {VEHICLE_MAP_PATH}")
    print(f"HTML report: {REPORT_PATH}")
    print(f"Pruning enabled: {prune_stats.get('enabled')}")
    print(f"Pruned events: {prune_stats.get('deleted', 0)}")


if __name__ == "__main__":
    main()
