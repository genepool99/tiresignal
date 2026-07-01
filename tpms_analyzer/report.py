import json
from datetime import datetime, timezone

from tpms_config import (
    DB_PATH,
    LOG_PATH,
    MAX_CANDIDATE_SENSOR_COUNT,
    MAX_RECENT_PASSES,
    MIN_REPEAT_CLUSTER_COUNT,
    PASS_WINDOW_SECONDS,
    REPORT_PATH,
    STRONG_SENSOR_COUNT,
    VEHICLE_MAP_PATH,
    VERY_STRONG_PASS_COUNT,
)
from utils import category_label, display_dt, display_time, parse_time, safe_text

from report_css import CSS_BLOCK
from report_js import JS_BLOCK


def pill(text, category="info"):
    text = safe_text(text)
    category = safe_text(category or "info")
    return f'<span class="pill {category}">{text}</span>'


def vehicle_status_html(name, category):
    if name:
        return pill(name, category or "known")

    return pill("Unknown", "unknown")


def known_match_text(match):
    if not match or not match.get("name"):
        return ""

    return f'{match["matched"]}/{match["total"]} sensors · {match["confidence"]}'


def pressure_value(event_or_row):
    if event_or_row.get("pressure_psi") is not None:
        return event_or_row["pressure_psi"]

    if event_or_row.get("pressure_kpa") is not None:
        return event_or_row["pressure_kpa"]

    if event_or_row.get("avg_pressure_psi") is not None:
        return event_or_row["avg_pressure_psi"]

    if event_or_row.get("avg_pressure_kpa") is not None:
        return event_or_row["avg_pressure_kpa"]

    return ""


def tail_log_lines(path, limit=200):
    try:
        if not path.exists():
            return []

        with path.open("rb") as file:
            file.seek(0, 2)
            size = file.tell()

            if size == 0:
                return []

            chunk_size = 8192
            buffer = b""
            position = size

            while position > 0 and buffer.count(b"\n") < limit + 1:
                step = min(chunk_size, position)
                position -= step
                file.seek(position)
                buffer = file.read(step) + buffer

        lines = buffer.decode("utf-8", errors="replace").splitlines()
        return [line for line in lines[-limit:] if line.strip()]
    except OSError:
        return []


def compute_pattern_labels(row, now_dt):
    labels = []

    pass_count = row.get("pass_count") or 0
    first_seen_dt = parse_time(row.get("first_seen", ""))
    last_seen_dt = parse_time(row.get("last_seen", ""))

    if first_seen_dt and first_seen_dt.tzinfo is None:
        first_seen_dt = first_seen_dt.replace(tzinfo=timezone.utc)
    if last_seen_dt and last_seen_dt.tzinfo is None:
        last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)

    if pass_count >= 10:
        labels.append({
            "text": "Regular visitor",
            "caveat": "Seen across 10 or more separate passes. Probably worth reviewing.",
        })
    elif pass_count <= MIN_REPEAT_CLUSTER_COUNT + 1:
        labels.append({
            "text": "Maybe a fluke",
            "caveat": "Only a few repeated passes so far. Could be a coincidence.",
        })

    if last_seen_dt:
        days_since = (now_dt - last_seen_dt).days
        if days_since <= 7:
            labels.append({
                "text": "Recently active",
                "caveat": "Seen within 7 days of this report.",
            })
        elif days_since > 30:
            labels.append({
                "text": "Went quiet",
                "caveat": "Not seen for more than 30 days as of this report.",
            })

    if first_seen_dt and last_seen_dt and pass_count < 10:
        span_days = (last_seen_dt - first_seen_dt).days
        if span_days > 14:
            labels.append({
                "text": "Occasional visitor",
                "caveat": "Seen over more than two weeks, but not very often.",
            })

    return labels


def write_report(context):
    events = context["events"]
    sensor_summaries = context["sensor_summaries"]
    vehicle_passes = context["vehicle_passes"]
    recent_pass_rows = context["recent_passes"]
    recent_event_rows = context["recent_events"]
    exact_candidate_summaries = context["exact_candidate_summaries"]
    overlap_candidate_summaries = context["overlap_candidate_summaries"]
    known_vehicle_summaries = context["known_vehicle_summaries"]
    new_unknown_candidates = context["new_unknown_candidates"]
    daily_counts = context["daily_counts"]
    hourly_counts = context["hourly_counts"]
    vehicles = context["vehicles"]
    ingest_stats = context["ingest_stats"]
    prune_stats = context.get("prune_stats", {})

    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    timeline_points = [
        {
            "time": e["event_time"].isoformat() if e["event_time"] else e["event_time_text"],
            "sensor_id": e["sensor_id"],
            "model": e["model"],
            "pressure": e["pressure_psi"] if e["pressure_psi"] is not None else e["pressure_kpa"],
            "pressure_unit": "PSI" if e["pressure_psi"] is not None else ("kPa" if e["pressure_kpa"] is not None else ""),
            "temperature_c": e["temperature_c"],
            "pressure_psi": e["pressure_psi"],
            "pressure_kpa": e["pressure_kpa"],
            "rssi": e["rssi"],
            "snr": e["snr"],
            "noise": e["noise"],
            "battery_ok": e["battery_ok"],
            "maybe_battery": e.get("maybe_battery"),
            "protocol": e["protocol"],
        }
        for e in events
    ]

    known_count = len([v for v in vehicles if v.get("category") == "known"])
    watch_count = len([v for v in vehicles if v.get("category") == "watch"])
    ignore_count = len([v for v in vehicles if v.get("category") == "ignore"])
    ignored_vehicles = [v for v in vehicles if v.get("category") == "ignore"]
    raw_packet_lines = tail_log_lines(LOG_PATH, 200)

    html = html_start(generated_at)

    html += f"""
    <div class="tabs" role="tablist" aria-label="TPMS report sections">
      <button
        type="button"
        class="tab-button active"
        data-tab-target="tab-overview"
        onclick="showReportTab('tab-overview')"
      >
        Overview
      </button>
      <button
        type="button"
        class="tab-button"
        data-tab-target="tab-candidates"
        onclick="showReportTab('tab-candidates')"
      >
        Candidates
      </button>
      <button
        type="button"
        class="tab-button"
        data-tab-target="tab-charts"
        onclick="showReportTab('tab-charts')"
      >
        Charts
      </button>
      <button
        type="button"
        class="tab-button"
        data-tab-target="tab-details"
        onclick="showReportTab('tab-details')"
      >
        Details
      </button>
      <button
        type="button"
        class="tab-button"
        data-tab-target="tab-raw-packets"
        onclick="showReportTab('tab-raw-packets')"
      >
        Raw Packets
      </button>
    </div>

    <div id="tab-overview" class="tab-panel active">
"""

    html += summary_cards(
        events=events,
        sensor_summaries=sensor_summaries,
        vehicle_passes=vehicle_passes,
        overlap_candidate_summaries=overlap_candidate_summaries,
        known_count=known_count,
        watch_count=watch_count,
        ignore_count=ignore_count,
        ingest_stats=ingest_stats,
    )
    html += known_vehicle_section(known_vehicle_summaries)

    if ignored_vehicles:
        html += ignored_vehicle_section(ignored_vehicles)

    html += """
    </div>

    <div id="tab-candidates" class="tab-panel">
"""
    html += new_unknown_section(new_unknown_candidates)
    html += overlap_candidates_section(overlap_candidate_summaries)
    html += exact_candidates_section(exact_candidate_summaries)

    html += """
    </div>

    <div id="tab-charts" class="tab-panel">
"""
    html += charts_section()

    html += """
    </div>

    <div id="tab-details" class="tab-panel">
"""
    html += recent_passes_section(recent_pass_rows)
    html += sensor_section(sensor_summaries)
    html += recent_events_section(recent_event_rows)
    html += import_stats_section(ingest_stats, prune_stats)

    html += """
    </div>

    <div id="tab-raw-packets" class="tab-panel">
"""
    html += raw_packets_section(raw_packet_lines)

    html += """
    </div>
"""
    html += html_end(timeline_points, daily_counts, hourly_counts)

    REPORT_PATH.write_text(html, encoding="utf-8")


def html_start(generated_at):
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>TPMS Report</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>{CSS_BLOCK}  </style>
</head>
<body>
  <header>
    <div class="header-row">
      <div>
        <h1>TPMS Report</h1>
        <div class="muted">
          Generated: {safe_text(generated_at)} · Source: <code>{safe_text(LOG_PATH)}</code>
        </div>
      </div>
      <button id="refreshButton" class="refresh-button" onclick="refreshReport()">
        Refresh Report
      </button>
    </div>
  </header>

  <main>
    <div class="note">
      <div class="matching-summary">
        <div class="matching-summary-title">How matching works</div>
        <div class="matching-summary-grid">
          <div class="matching-summary-item">
            <span class="matching-summary-value">{PASS_WINDOW_SECONDS}s</span>
            <span class="matching-summary-label">Pass window</span>
          </div>
          <div class="matching-summary-item">
            <span class="matching-summary-value">{MIN_REPEAT_CLUSTER_COUNT}</span>
            <span class="matching-summary-label">Repeat passes required</span>
          </div>
          <div class="matching-summary-item">
            <span class="matching-summary-value">{MAX_CANDIDATE_SENSOR_COUNT}</span>
            <span class="matching-summary-label">Max sensors/group</span>
          </div>
          <div class="matching-summary-item">
            <span class="matching-summary-value">{STRONG_SENSOR_COUNT} \xd7 {VERY_STRONG_PASS_COUNT}</span>
            <span class="matching-summary-label">Very strong threshold</span>
          </div>
        </div>
      </div>
    </div>
"""


def summary_cards(
    events,
    sensor_summaries,
    vehicle_passes,
    overlap_candidate_summaries,
    known_count,
    watch_count,
    ignore_count,
    ingest_stats,
):
    return f"""
    <div class="cards">
      <div class="card">
        <div class="big">{len(events)}</div>
        <div>Total TPMS Events</div>
      </div>
      <div class="card">
        <div class="big">{len(sensor_summaries)}</div>
        <div>Unique Sensor IDs</div>
      </div>
      <div class="card">
        <div class="big">{len(vehicle_passes)}</div>
        <div>Detected Passes</div>
      </div>
      <div class="card">
        <div class="big">{len(overlap_candidate_summaries)}</div>
        <div>Overlap Candidates</div>
      </div>
      <div class="card">
        <div class="big">{known_count}</div>
        <div>Known Vehicles</div>
      </div>
      <div class="card">
        <div class="big">{watch_count}</div>
        <div>Watchlist Vehicles</div>
      </div>
      <div class="card">
        <div class="big">{ignore_count}</div>
        <div>Ignored Entries</div>
      </div>
      <div class="card">
        <div class="big">{ingest_stats.get("imported", 0)}</div>
        <div>New Events Imported</div>
      </div>
    </div>
"""


def known_vehicle_section(rows):
    html = f"""
    <div class="section">
      <h2>Known &amp; Watchlist Vehicles</h2>
      <p class="muted">Your labeled vehicles, matched against observed passes. Example: if two or more sensors from a saved vehicle appear within a {PASS_WINDOW_SECONDS}-second pass window, the report counts that as a match.</p>
      <div class="toolbar">
        <input placeholder="Search known/watch vehicles..." oninput="filterTable('knownVehicleTable', this.value)">
      </div>
      <table id="knownVehicleTable">
        <thead>
          <tr>
            <th>Name</th>
            <th>Category</th>
            <th>Seen Today</th>
            <th>Total Seen</th>
            <th>Best Match</th>
            <th>First Seen</th>
            <th>Last Seen</th>
            <th>Sensor IDs</th>
            <th>Actions</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
"""

    for row in rows:
        sensor_ids = row["sensor_ids"]
        category = row["category"]

        known_payload = {
            "action": "update_category",
            "name": row["name"],
            "category": "known",
            "notes": row["notes"],
            "sensor_ids": sensor_ids,
        }

        watch_payload = {
            "action": "update_category",
            "name": row["name"],
            "category": "watch",
            "notes": row["notes"],
            "sensor_ids": sensor_ids,
        }

        ignore_payload = {
            "action": "update_category",
            "name": row["name"],
            "category": "ignore",
            "notes": row["notes"],
            "sensor_ids": sensor_ids,
        }

        move_button = ""

        if category == "known":
            move_button = f"""
                <button
                  type="button"
                  class="small-action-button watch-action"
                  data-payload="{safe_text(json.dumps(watch_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Move to Watch
                </button>
"""
        elif category == "watch":
            move_button = f"""
                <button
                  type="button"
                  class="small-action-button known-action"
                  data-payload="{safe_text(json.dumps(known_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Move to Known
                </button>
"""

        html += f"""
          <tr>
            <td>{safe_text(row["name"])}</td>
            <td>{pill(category_label(row["category"]), row["category"])}</td>
            <td>{row["seen_today"]}</td>
            <td>{row["seen_count"]}</td>
            <td>{safe_text(row["best_match"])}</td>
            <td>{display_time(row["first_seen"])}</td>
            <td>{display_time(row["last_seen"])}</td>
            <td>{safe_text(", ".join(sensor_ids))}</td>
            <td>
              <div class="action-buttons">
                {move_button}
                <button
                  type="button"
                  class="small-action-button ignore-action"
                  data-payload="{safe_text(json.dumps(ignore_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Ignore
                </button>
              </div>
            </td>
            <td>{safe_text(row["notes"])}</td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </div>
"""
    return html


def ignored_vehicle_section(rows):
    html = """
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Ignored Vehicles</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Sensor groups you've marked as uninteresting noise. Move one back to Known or Watchlist if you change your mind.</p>
      <div class="toolbar">
        <input placeholder="Search ignored vehicles..." oninput="filterTable('ignoredVehicleTable', this.value)">
      </div>
      <table id="ignoredVehicleTable">
        <thead>
          <tr>
            <th>Name</th>
            <th>Sensor IDs</th>
            <th>Actions</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
"""

    for row in rows:
        sensor_ids = row.get("sensor_ids", [])
        name = row.get("name", "Ignored Vehicle")
        notes = row.get("notes", "")

        known_payload = {
            "action": "update_category",
            "name": name,
            "category": "known",
            "notes": notes,
            "sensor_ids": sensor_ids,
        }

        watch_payload = {
            "action": "update_category",
            "name": name,
            "category": "watch",
            "notes": notes,
            "sensor_ids": sensor_ids,
        }

        html += f"""
          <tr>
            <td>{safe_text(name)}</td>
            <td>{safe_text(", ".join(sensor_ids))}</td>
            <td>
              <div class="action-buttons">
                <button
                  type="button"
                  class="small-action-button known-action"
                  data-payload="{safe_text(json.dumps(known_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Move to Known
                </button>
                <button
                  type="button"
                  class="small-action-button watch-action"
                  data-payload="{safe_text(json.dumps(watch_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Move to Watch
                </button>
              </div>
            </td>
            <td>{safe_text(notes)}</td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def new_unknown_section(rows):
    html = """
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Unlabeled Repeat Candidates</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Sensor clusters that appeared together repeatedly but have not been labeled yet. Example: a recurring four-sensor group may be a new vehicle to add, watch, or ignore.</p>
      <div class="toolbar">
        <input placeholder="Search unknown candidates..." oninput="filterTable('newUnknownTable', this.value)">
      </div>
      <table id="newUnknownTable">
        <thead>
          <tr>
            <th>Confidence</th>
            <th>Pass Count</th>
            <th>Sensor Count</th>
            <th>First Seen</th>
            <th>Last Seen</th>
            <th>Sensor IDs</th>
            <th>Actions</th>
            <th>Copy/Paste JSON</th>
          </tr>
        </thead>
        <tbody>
"""

    for index, row in enumerate(rows, start=1):
        candidate_name = f"Unknown Candidate {index}"
        candidate_notes = f"Generated from TPMS report. Pass count: {row['pass_count']}"
        sensor_ids = row["sensor_ids"]

        snippet = {
            "name": candidate_name,
            "category": "watch",
            "notes": candidate_notes,
            "sensor_ids": sensor_ids,
        }

        watch_payload = {
            "action": "add",
            "name": candidate_name,
            "category": "watch",
            "notes": candidate_notes,
            "sensor_ids": sensor_ids,
        }

        ignore_payload = {
            "action": "add",
            "name": candidate_name,
            "category": "ignore",
            "notes": candidate_notes,
            "sensor_ids": sensor_ids,
        }

        html += f"""
          <tr>
            <td>{pill(row["confidence"], "info")}</td>
            <td>{row["pass_count"]}</td>
            <td>{row["sensor_count"]}</td>
            <td>{display_time(row["first_seen"])}</td>
            <td>{display_time(row["last_seen"])}</td>
            <td>{safe_text(", ".join(sensor_ids))}</td>
            <td>
              <div class="action-buttons">
                <button
                  type="button"
                  class="small-action-button watch-action"
                  data-payload="{safe_text(json.dumps(watch_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Add Watch
                </button>
                <button
                  type="button"
                  class="small-action-button ignore-action"
                  data-payload="{safe_text(json.dumps(ignore_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Ignore
                </button>
              </div>
            </td>
            <td><div class="copybox">{safe_text(json.dumps(snippet, indent=2))}</div></td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def overlap_candidates_section(rows):
    html = f"""
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Best Guess Vehicle Candidates</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Groups passes that share two or more sensor IDs, allowing partial overlap across passes. Example: near a busy road, the same vehicle may only transmit three of four sensors during a pass. Click Details to inspect a suggested vehicle.</p>
      <div class="note">
        <span class="muted">
          Best Guess candidates are based on repeated co-occurrence of sensor IDs across separate passes.
          More sensors seen together across more passes means stronger confidence.
          These are suggestions from local radio observations, not confirmed vehicle identities.
        </span>
        <div class="matching-summary">
          <div class="matching-summary-title">Confidence tiers</div>
          <div class="matching-summary-grid">
            <div class="matching-summary-item">
              <span class="matching-summary-value">2+ sensors</span>
              <span class="matching-summary-label">Repeated across 2+ passes — Possible</span>
            </div>
            <div class="matching-summary-item">
              <span class="matching-summary-value">3+ sensors</span>
              <span class="matching-summary-label">Repeated across 2+ passes — Strong</span>
            </div>
            <div class="matching-summary-item">
              <span class="matching-summary-value">{STRONG_SENSOR_COUNT}+ sensors</span>
              <span class="matching-summary-label">{VERY_STRONG_PASS_COUNT}+ repeated passes — Very strong</span>
            </div>
            <div class="matching-summary-item">
              <span class="matching-summary-value">{MAX_CANDIDATE_SENSOR_COUNT} sensors</span>
              <span class="matching-summary-label">Larger clusters are ignored</span>
            </div>
          </div>
        </div>
      </div>
      <div class="toolbar">
        <input placeholder="Search names, IDs, confidence..." oninput="filterTable('overlapCandidateTable', this.value)">
      </div>
      <table id="overlapCandidateTable">
        <thead>
          <tr>
            <th>Known Name</th>
            <th>Category</th>
            <th>Known Match</th>
            <th>Confidence</th>
            <th>Pass Count</th>
            <th>Sensor Count</th>
            <th>First Seen</th>
            <th>Last Seen</th>
            <th>Sensor IDs</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
"""

    now_dt = datetime.now().astimezone()

    for index, row in enumerate(rows, start=1):
        sensor_ids = row["sensor_ids"]
        known_vehicle = row["known_vehicle"]
        category = row["category"] or ""

        details_payload = {
            "title": known_vehicle or f"Candidate {index}",
            "confidence": row["confidence"],
            "category": category,
            "known_vehicle": known_vehicle,
            "match_text": known_match_text(row["known_match"]),
            "sensor_count": row["sensor_count"],
            "pass_count": row["pass_count"],
            "first_seen": row["first_seen"],
            "last_seen": row["last_seen"],
            "sensor_ids": sensor_ids,
            "pattern_labels": compute_pattern_labels(row, now_dt),
        }
        details_button = f"""
                <button
                  type="button"
                  class="small-action-button"
                  data-candidate="{safe_text(json.dumps(details_payload))}"
                  onclick="openCandidateDrawer(this)"
                >
                  Details
                </button>"""

        if known_vehicle:
            known_payload = {
                "action": "update_category",
                "name": known_vehicle,
                "category": "known",
                "notes": "",
                "sensor_ids": sensor_ids,
            }
            watch_payload = {
                "action": "update_category",
                "name": known_vehicle,
                "category": "watch",
                "notes": "",
                "sensor_ids": sensor_ids,
            }
            ignore_payload = {
                "action": "update_category",
                "name": known_vehicle,
                "category": "ignore",
                "notes": "",
                "sensor_ids": sensor_ids,
            }
            action_buttons = ""
            if category != "known":
                action_buttons += f"""
                <button
                  type="button"
                  class="small-action-button known-action"
                  data-payload="{safe_text(json.dumps(known_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Move to Known
                </button>"""
            if category != "watch":
                action_buttons += f"""
                <button
                  type="button"
                  class="small-action-button watch-action"
                  data-payload="{safe_text(json.dumps(watch_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Move to Watch
                </button>"""
            if category != "ignore":
                action_buttons += f"""
                <button
                  type="button"
                  class="small-action-button ignore-action"
                  data-payload="{safe_text(json.dumps(ignore_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Ignore
                </button>"""
            action_buttons += details_button
        else:
            candidate_name = f"Unknown Candidate {index}"
            candidate_notes = f"Pass count: {row['pass_count']}"
            watch_payload = {
                "action": "add",
                "name": candidate_name,
                "category": "watch",
                "notes": candidate_notes,
                "sensor_ids": sensor_ids,
            }
            ignore_payload = {
                "action": "add",
                "name": candidate_name,
                "category": "ignore",
                "notes": candidate_notes,
                "sensor_ids": sensor_ids,
            }
            action_buttons = f"""
                <button
                  type="button"
                  class="small-action-button watch-action"
                  data-payload="{safe_text(json.dumps(watch_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Add Watch
                </button>
                <button
                  type="button"
                  class="small-action-button ignore-action"
                  data-payload="{safe_text(json.dumps(ignore_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Ignore
                </button>""" + details_button

        html += f"""
          <tr>
            <td>{vehicle_status_html(row["known_vehicle"], row["category"])}</td>
            <td>{pill(category_label(row["category"] or "unknown"), row["category"] or "unknown")}</td>
            <td>{safe_text(known_match_text(row["known_match"]))}</td>
            <td title="{row['sensor_count']} sensors · {row['pass_count']} passes">{pill(row["confidence"], "info")}</td>
            <td>{row["pass_count"]}</td>
            <td>{row["sensor_count"]}</td>
            <td>{display_time(row["first_seen"])}</td>
            <td>{display_time(row["last_seen"])}</td>
            <td>{safe_text(", ".join(row["sensor_ids"]))}</td>
            <td>
              <div class="action-buttons">{action_buttons}
              </div>
            </td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def exact_candidates_section(rows):
    html = f"""
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Exact Repeat Sensor Groups</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Groups passes where the identical set of sensor IDs appeared together repeatedly. Example: the same three tire IDs seen together at least {MIN_REPEAT_CLUSTER_COUNT} times. This is stricter than Best Guess and may miss partial passes.</p>
      <div class="toolbar">
        <input placeholder="Search exact candidates..." oninput="filterTable('exactCandidateTable', this.value)">
      </div>
      <table id="exactCandidateTable">
        <thead>
          <tr>
            <th>Known Name</th>
            <th>Category</th>
            <th>Known Match</th>
            <th>Confidence</th>
            <th>Pass Count</th>
            <th>Sensor Count</th>
            <th>First Seen</th>
            <th>Last Seen</th>
            <th>Sensor IDs</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
"""

    for index, row in enumerate(rows, start=1):
        sensor_ids = row["sensor_ids"]
        known_vehicle = row["known_vehicle"]
        category = row["category"] or ""

        if known_vehicle:
            known_payload = {
                "action": "update_category",
                "name": known_vehicle,
                "category": "known",
                "notes": "",
                "sensor_ids": sensor_ids,
            }
            watch_payload = {
                "action": "update_category",
                "name": known_vehicle,
                "category": "watch",
                "notes": "",
                "sensor_ids": sensor_ids,
            }
            ignore_payload = {
                "action": "update_category",
                "name": known_vehicle,
                "category": "ignore",
                "notes": "",
                "sensor_ids": sensor_ids,
            }
            action_buttons = ""
            if category != "known":
                action_buttons += f"""
                <button
                  type="button"
                  class="small-action-button known-action"
                  data-payload="{safe_text(json.dumps(known_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Move to Known
                </button>"""
            if category != "watch":
                action_buttons += f"""
                <button
                  type="button"
                  class="small-action-button watch-action"
                  data-payload="{safe_text(json.dumps(watch_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Move to Watch
                </button>"""
            if category != "ignore":
                action_buttons += f"""
                <button
                  type="button"
                  class="small-action-button ignore-action"
                  data-payload="{safe_text(json.dumps(ignore_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Ignore
                </button>"""
        else:
            candidate_name = f"Exact Repeat Candidate {index}"
            candidate_notes = f"Pass count: {row['pass_count']}"
            watch_payload = {
                "action": "add",
                "name": candidate_name,
                "category": "watch",
                "notes": candidate_notes,
                "sensor_ids": sensor_ids,
            }
            ignore_payload = {
                "action": "add",
                "name": candidate_name,
                "category": "ignore",
                "notes": candidate_notes,
                "sensor_ids": sensor_ids,
            }
            action_buttons = f"""
                <button
                  type="button"
                  class="small-action-button watch-action"
                  data-payload="{safe_text(json.dumps(watch_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Add Watch
                </button>
                <button
                  type="button"
                  class="small-action-button ignore-action"
                  data-payload="{safe_text(json.dumps(ignore_payload))}"
                  onclick="editVehicleMapFromButton(this)"
                >
                  Ignore
                </button>"""

        html += f"""
          <tr>
            <td>{vehicle_status_html(row["known_vehicle"], row["category"])}</td>
            <td>{pill(category_label(row["category"] or "unknown"), row["category"] or "unknown")}</td>
            <td>{safe_text(known_match_text(row["known_match"]))}</td>
            <td>{pill(row["confidence"], "info")}</td>
            <td>{row["pass_count"]}</td>
            <td>{row["sensor_count"]}</td>
            <td>{display_time(row["first_seen"])}</td>
            <td>{display_time(row["last_seen"])}</td>
            <td>{safe_text(", ".join(row["sensor_ids"]))}</td>
            <td>
              <div class="action-buttons">{action_buttons}
              </div>
            </td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def charts_section():
    return """
    <div class="chart-toolbar">
      <label for="chart-time-filter">Time range</label>
      <select id="chart-time-filter">
        <option value="all">All data</option>
        <option value="24h">Last 24 hours</option>
        <option value="7d" selected>Last 7 days</option>
        <option value="30d">Last 30 days</option>
      </select>
      <span class="muted">Signal history from the TPMS database. Use the time range filter to focus on recent activity.</span>
    </div>
    <div id="charts-loading" class="chart-loading" role="status" aria-live="polite" aria-hidden="true">
      Rendering charts...
    </div>

    <div class="section">
      <h2>Detection Timeline</h2>
      <div id="timelineChart" class="chart"></div>
    </div>

    <div class="section">
      <h2>Daily TPMS Event Volume</h2>
      <div id="dailyChart" class="small-chart"></div>
    </div>

    <div class="section">
      <h2>Hourly TPMS Event Volume</h2>
      <div id="hourlyChart" class="small-chart"></div>
    </div>

    <div class="section">
      <h2>Pressure Over Time</h2>
      <div class="chart-option-row pressure-option-row">
        <label class="chart-toggle-control">
          <input id="chart-show-suspicious-pressure" type="checkbox">
          <span class="chart-toggle-slider" aria-hidden="true"></span>
          <span class="chart-toggle-label">Show suspicious pressure points</span>
        </label>
        <span id="pressureChartNote" class="chart-inline-note">
          Suspicious pressure points above 120 PSI are hidden by default. Hidden suspicious points: 0
        </span>
      </div>
      <div id="pressureChart" class="chart"></div>
    </div>

    <div class="section">
      <h2>Temperature Over Time</h2>
      <div id="temperatureChart" class="chart"></div>
    </div>

    <div class="section">
      <h2>Events by Model</h2>
      <div id="modelChart" class="small-chart"></div>
    </div>

    <div class="section">
      <h2>Confirmed Battery Status</h2>
      <p class="muted">Uses confirmed battery_ok / battery fields only. maybe_battery is not interpreted.</p>
      <div id="batteryChart" class="small-chart"></div>
    </div>

    <div class="section">
      <h2>Unconfirmed Battery Signal</h2>
      <p class="muted">Raw rtl_433 maybe_battery decoder hint. This is not interpreted as Battery OK/Low.</p>
      <div id="maybeBatteryChart" class="chart"></div>
    </div>

    <div class="section">
      <h2>Signal Quality Over Time</h2>
      <div id="signalChart" class="chart"></div>
    </div>
"""


def recent_passes_section(rows):
    html = f"""
    <details class="section" open>
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Recent Passes</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">A pass is a burst of TPMS signals received within a {PASS_WINDOW_SECONDS}-second window. Example: several tire IDs heard close together are shown as one pass. Up to {MAX_RECENT_PASSES} recent passes are shown.</p>
      <div class="toolbar">
        <input placeholder="Search recent passes..." oninput="filterTable('passTable', this.value)">
      </div>
      <table id="passTable">
        <thead>
          <tr>
            <th>Known Name</th>
            <th>Category</th>
            <th>Known Match</th>
            <th>Start</th>
            <th>Duration</th>
            <th>Sensors</th>
            <th>Events</th>
            <th>Models</th>
            <th>Sensor IDs</th>
          </tr>
        </thead>
        <tbody>
"""

    for row in rows:
        crowded_indicator = ""

        if row["sensor_count"] > MAX_CANDIDATE_SENSOR_COUNT:
            crowded_indicator = pill("Crowded window", "unknown")

        html += f"""
          <tr>
            <td>{vehicle_status_html(row["known_vehicle"], row["category"])}</td>
            <td>{pill(category_label(row["category"] or "unknown"), row["category"] or "unknown")}</td>
            <td>{safe_text(known_match_text(row["known_match"]))}</td>
            <td>{display_dt(row["start"])}</td>
            <td>{row["duration_seconds"]}s</td>
            <td>{row["sensor_count"]} {crowded_indicator}</td>
            <td>{row["event_count"]}</td>
            <td>{safe_text(", ".join(row["models"]))}</td>
            <td>{safe_text(", ".join(row["sensor_ids"]))}</td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def sensor_section(rows):
    html = """
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Unique TPMS Sensor IDs</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Every unique TPMS sensor ID seen in the database, with basic timing, signal, pressure, and temperature summaries. Use this table when identifying which sensors belong together.</p>
      <div class="toolbar">
        <input placeholder="Search sensor IDs, models, names..." oninput="filterTable('sensorTable', this.value)">
      </div>
      <table id="sensorTable">
        <thead>
          <tr>
            <th>Known Vehicle</th>
            <th>Category</th>
            <th>Sensor ID</th>
            <th>Count</th>
            <th>First Seen</th>
            <th>Last Seen</th>
            <th>Model(s)</th>
            <th>Avg Pressure (native unit)</th>
            <th>Avg Temp C</th>
            <th>Avg RSSI</th>
            <th>Avg SNR</th>
          </tr>
        </thead>
        <tbody>
"""

    for row in rows:
        pressure = row["avg_pressure_psi"] if row["avg_pressure_psi"] is not None else row["avg_pressure_kpa"]

        html += f"""
          <tr>
            <td>{vehicle_status_html(row["vehicle_name"], row["category"])}</td>
            <td>{pill(category_label(row["category"] or "unknown"), row["category"] or "unknown")}</td>
            <td>{safe_text(row["sensor_id"])}</td>
            <td>{row["count"]}</td>
            <td>{display_time(row["first_seen"])}</td>
            <td>{display_time(row["last_seen"])}</td>
            <td>{safe_text(row["models"])}</td>
            <td>{safe_text(pressure if pressure is not None else "")}</td>
            <td>{safe_text(row["avg_temperature_c"] if row["avg_temperature_c"] is not None else "")}</td>
            <td>{safe_text(row["avg_rssi"] if row["avg_rssi"] is not None else "")}</td>
            <td>{safe_text(row["avg_snr"] if row["avg_snr"] is not None else "")}</td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def recent_events_section(rows):
    html = """
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Recent Raw Events</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Individual TPMS signal events, most recent first. Example: one vehicle pass may produce multiple raw events from one or more tire sensors.</p>
      <div class="toolbar">
        <input placeholder="Search recent events..." oninput="filterTable('eventTable', this.value)">
      </div>
      <table id="eventTable">
        <thead>
          <tr>
            <th>Time</th>
            <th>Sensor ID</th>
            <th>Model</th>
            <th>Pressure (native unit)</th>
            <th>Temp C</th>
            <th>RSSI</th>
            <th>SNR</th>
          </tr>
        </thead>
        <tbody>
"""

    for event in rows:
        pressure = event["pressure_psi"] if event["pressure_psi"] is not None else event["pressure_kpa"]
        event_time = display_dt(event["event_time"]) if event["event_time"] else safe_text(event["event_time_text"])

        html += f"""
          <tr>
            <td>{event_time}</td>
            <td>{safe_text(event["sensor_id"])}</td>
            <td>{safe_text(event["model"])}</td>
            <td>{safe_text(pressure if pressure is not None else "")}</td>
            <td>{safe_text(event["temperature_c"] if event["temperature_c"] is not None else "")}</td>
            <td>{safe_text(event["rssi"] if event["rssi"] is not None else "")}</td>
            <td>{safe_text(event["snr"] if event["snr"] is not None else "")}</td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def raw_packets_section(lines):
    html = """
    <div class="section">
      <h2>Recent Raw Packets</h2>
      <p class="muted">Raw JSON lines from the rtl_433 log file, newest first. Includes all packet types, not just TPMS, which is useful when checking what signals are being received.</p>
      <div class="toolbar">
        <input placeholder="Search raw packets..." oninput="filterTable('rawPacketTable', this.value)">
      </div>
      <table id="rawPacketTable">
        <thead>
          <tr>
            <th>Time</th>
            <th>Model</th>
            <th>ID</th>
            <th>Raw JSON</th>
          </tr>
        </thead>
        <tbody>
"""

    for line in reversed(lines):
        packet_time = ""
        model = ""
        packet_id = ""

        try:
            packet = json.loads(line)

            if isinstance(packet, dict):
                packet_time = packet.get("time", "")
                model = packet.get("model", "")
                packet_id = (
                    packet.get("id")
                    or packet.get("sensor_id")
                    or packet.get("device")
                    or ""
                )
        except json.JSONDecodeError:
            packet_time = "[malformed]"
            model = "[malformed]"
            packet_id = ""

        html += f"""
          <tr>
            <td>{safe_text(packet_time)}</td>
            <td>{safe_text(model)}</td>
            <td>{safe_text(packet_id)}</td>
            <td><div class="copybox">{safe_text(line)}</div></td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </div>
"""
    return html


def import_stats_section(stats, prune_stats):
    return f"""
    <div class="section">
      <h2>Import / Pruning Stats</h2>
      <p class="muted">Log ingestion and database maintenance counts from this run.</p>
      <table>
        <tbody>
          <tr><th>Imported this run</th><td>{stats.get("imported", 0)}</td></tr>
          <tr><th>Skipped total</th><td>{stats.get("skipped", 0)}</td></tr>
          <tr><th>Duplicates</th><td>{stats.get("duplicate", 0)}</td></tr>
          <tr><th>Non-TPMS lines</th><td>{stats.get("non_tpms", 0)}</td></tr>
          <tr><th>Malformed JSON</th><td>{stats.get("malformed", 0)}</td></tr>
          <tr><th>TPMS lines without sensor ID</th><td>{stats.get("no_sensor_id", 0)}</td></tr>
          <tr><th>Pruning enabled</th><td>{safe_text(prune_stats.get("enabled", ""))}</td></tr>
          <tr><th>Pruned events this run</th><td>{prune_stats.get("deleted", 0)}</td></tr>
          <tr><th>Unknown single-sensor cutoff</th><td>{safe_text(prune_stats.get("single_cutoff", ""))}</td></tr>
          <tr><th>Unknown recurring cutoff</th><td>{safe_text(prune_stats.get("multi_cutoff", ""))}</td></tr>
          <tr><th>Preserved labeled sensors</th><td>{prune_stats.get("preserved_labeled_sensors", 0)}</td></tr>
          <tr><th>Database</th><td><code>{safe_text(DB_PATH)}</code></td></tr>
          <tr><th>Vehicle map</th><td><code>{safe_text(VEHICLE_MAP_PATH)}</code></td></tr>
        </tbody>
      </table>
    </div>
"""


def html_end(timeline_points, daily_counts, hourly_counts):
    return (
        """
  <div id="candidateDrawer" class="candidate-drawer"
       role="dialog" aria-modal="true"
       aria-hidden="true" aria-labelledby="candidateDrawerTitle">
    <div class="candidate-drawer-backdrop" onclick="closeCandidateDrawer()"></div>
    <div class="candidate-drawer-panel">
      <div class="candidate-drawer-header">
        <strong id="candidateDrawerTitle">Candidate details</strong>
        <button type="button" class="candidate-drawer-close"
                onclick="closeCandidateDrawer()">&#x2715; Close</button>
      </div>
      <div id="candidateDrawerBody"></div>
    </div>
  </div>

  </main>

  <script>
"""
        + f"    const allTimelinePoints = {json.dumps(timeline_points)};\n"
        + JS_BLOCK
        + "  </script>\n</body>\n</html>"
    )


