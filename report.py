import json
from datetime import datetime

from tpms_config import (
    DB_PATH,
    LOG_PATH,
    MAX_CANDIDATE_SENSOR_COUNT,
    PASS_WINDOW_SECONDS,
    REFRESH_WEBHOOK_ID,
    REPORT_PATH,
    VEHICLE_MAP_PATH,
)
from utils import category_label, display_dt, display_time, safe_text


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
        Overview ({known_count + watch_count})
      </button>
      <button
        type="button"
        class="tab-button"
        data-tab-target="tab-charts"
        onclick="showReportTab('tab-charts')"
      >
        Charts ({len(events)})
      </button>
      <button
        type="button"
        class="tab-button"
        data-tab-target="tab-details"
        onclick="showReportTab('tab-details')"
      >
        Details ({len(recent_pass_rows)})
      </button>
      <button
        type="button"
        class="tab-button"
        data-tab-target="tab-raw-packets"
        onclick="showReportTab('tab-raw-packets')"
      >
        Raw Packets ({len(raw_packet_lines)})
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
  <title>rtl_433 TPMS Report</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{
      --bg: #f6f7f9;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --border: #d1d5db;
      --soft: #eef2f7;
      --known-bg: #d1fae5;
      --known-text: #065f46;
      --watch-bg: #dbeafe;
      --watch-text: #1e40af;
      --ignore-bg: #e5e7eb;
      --ignore-text: #374151;
      --unknown-bg: #fef3c7;
      --unknown-text: #92400e;
      --info-bg: #ede9fe;
      --info-text: #5b21b6;
    }}

    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      color: var(--text);
      background: var(--bg);
    }}

    header {{
      padding: 24px;
      background: var(--card);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 10;
    }}

    h1 {{
      margin: 0 0 4px;
      font-size: 28px;
    }}

    h2 {{
      margin-top: 0;
    }}

    main {{
      padding: 24px;
      max-width: 1750px;
      margin: 0 auto;
    }}

    .muted {{
      color: var(--muted);
    }}

    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 16px;
      margin: 20px 0;
    }}

    .card {{
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      background: var(--card);
      box-shadow: 0 1px 2px rgba(0,0,0,.04);
    }}

    .big {{
      font-size: 32px;
      font-weight: 800;
      line-height: 1.1;
    }}

    .section {{
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--card);
      padding: 18px;
      margin: 20px 0;
      overflow: hidden;
    }}

    details.section > summary.section-summary {{
      list-style: none;
      cursor: pointer;
      margin: -18px -18px 16px;
      padding: 16px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      background: var(--soft);
      border-bottom: 1px solid var(--border);
    }}

    details.section:not([open]) > summary.section-summary {{
      margin-bottom: -18px;
      border-bottom: 0;
    }}

    details.section > summary.section-summary::-webkit-details-marker {{
      display: none;
    }}

    details.section > summary.section-summary::marker {{
      content: "";
    }}

    details.section > summary.section-summary:hover {{
      background: #eef4ff;
    }}

    details.section > summary.section-summary:focus-visible {{
      outline: 3px solid rgba(37, 99, 235, 0.35);
      outline-offset: 3px;
    }}

    .section-summary-main {{
      min-width: 0;
    }}

    .section-summary-title {{
      display: block;
      color: var(--text);
      font-size: 1.2rem;
      font-weight: 800;
      line-height: 1.2;
    }}

    .section-summary-subtitle {{
      display: block;
      color: var(--muted);
      font-size: 0.85rem;
      font-weight: 600;
      margin-top: 4px;
    }}

    .section-summary-action {{
      flex: 0 0 auto;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 7px 11px;
      background: #ffffff;
      color: var(--text);
      font-size: 0.8rem;
      font-weight: 800;
      white-space: nowrap;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
    }}

    details.section:not([open]) .section-summary-action::before {{
      content: "Expand ▾";
    }}

    details.section[open] .section-summary-action::before {{
      content: "Collapse ▴";
    }}

    .chart {{
      height: 560px;
      margin: 12px 0 24px;
    }}

    .small-chart {{
      height: 360px;
      margin: 12px 0 24px;
    }}

    .toolbar {{
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      margin: 12px 0;
    }}

    input {{
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 14px;
      min-width: 280px;
    }}

    table {{
      border-collapse: collapse;
      width: 100%;
      margin-top: 12px;
      margin-bottom: 12px;
    }}

    th, td {{
      border-bottom: 1px solid var(--border);
      padding: 8px 10px;
      font-size: 13px;
      vertical-align: top;
    }}

    th {{
      background: var(--soft);
      text-align: left;
      position: sticky;
      top: 89px;
      z-index: 5;
      cursor: pointer;
      white-space: nowrap;
    }}

    tr:hover td {{
      background: #fafafa;
    }}

    code {{
      background: #eee;
      padding: 2px 4px;
      border-radius: 4px;
    }}

    .pill {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      white-space: nowrap;
      font-weight: 700;
    }}

    .known {{
      background: var(--known-bg);
      color: var(--known-text);
    }}

    .watch {{
      background: var(--watch-bg);
      color: var(--watch-text);
    }}

    .ignore {{
      background: var(--ignore-bg);
      color: var(--ignore-text);
    }}

    .unknown {{
      background: var(--unknown-bg);
      color: var(--unknown-text);
    }}

    .info {{
      background: var(--info-bg);
      color: var(--info-text);
    }}

    .note {{
      background: #fff7ed;
      border: 1px solid #fed7aa;
      border-radius: 12px;
      padding: 12px 14px;
      margin: 12px 0;
    }}

    .copybox {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      white-space: pre-wrap;
      background: #111827;
      color: #f9fafb;
      padding: 10px;
      border-radius: 10px;
      font-size: 12px;
      max-width: 800px;
      overflow-x: auto;
    }}
    
    .header-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}

    .refresh-button {{
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 14px;
      background: var(--soft);
      color: var(--text);
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }}

    .refresh-button:hover {{
      filter: brightness(0.97);
    }}

    .refresh-button:disabled {{
      opacity: 0.6;
      cursor: wait;
    }}

    .tabs {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      margin: 16px 0 20px;
      padding: 8px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--card);
    }}

    .tab-button {{
      border: 1px solid transparent;
      border-radius: 10px;
      padding: 10px 14px;
      background: transparent;
      color: var(--muted);
      font-weight: 800;
      cursor: pointer;
      white-space: nowrap;
    }}

    .tab-button:hover {{
      background: var(--soft);
      color: var(--text);
    }}

    .tab-button.active {{
      border-color: var(--border);
      background: var(--soft);
      color: var(--text);
      box-shadow: 0 1px 2px rgba(0,0,0,.04);
    }}

    .tab-panel {{
      display: none;
    }}

    .tab-panel.active {{
      display: block;
    }}

    .action-buttons {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }}

    .small-action-button {{
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 6px 10px;
      background: var(--soft);
      color: var(--text);
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
      white-space: nowrap;
    }}

    .small-action-button:hover {{
      filter: brightness(0.97);
    }}

    .small-action-button:disabled {{
      opacity: 0.6;
      cursor: wait;
    }}

    .known-action {{
      background: var(--known-bg);
      color: var(--known-text);
    }}

    .watch-action {{
      background: var(--watch-bg);
      color: var(--watch-text);
    }}

    .ignore-action {{
      background: var(--ignore-bg);
      color: var(--ignore-text);
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-row">
      <div>
        <h1>rtl_433 TPMS Report</h1>
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
      <strong>Last successful run:</strong> {safe_text(generated_at)}<br>
      <strong>Busy road mode is enabled.</strong>
      Pass grouping uses a short {PASS_WINDOW_SECONDS}-second window to avoid merging nearby traffic.
      Focus on known vehicles, watchlist vehicles, and repeat overlap candidates.
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
    html = """
    <div class="section">
      <h2>Known / Watchlist Vehicle Summary</h2>
      <p class="muted">Vehicles from vehicles.json, matched by sensor overlap.</p>
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
      <p class="muted">Ignored entries from vehicles.json. Restore one to Known or Watchlist if it should be tracked again.</p>
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
          <span class="section-summary-title">New Repeat Unknowns</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Unlabeled repeat candidates. These are good candidates to add to vehicles.json as known, watch, or ignore.</p>
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
    html = """
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Best Guess Vehicle Candidates</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Merges repeated passes that share two or more sensor IDs. Best table for a busy road.</p>
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
          </tr>
        </thead>
        <tbody>
"""

    for row in rows:
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
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def exact_candidates_section(rows):
    html = """
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Exact Repeat Sensor Groups</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Exact repeated sensor groups. Stricter than overlap matching.</p>
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
          </tr>
        </thead>
        <tbody>
"""

    for row in rows:
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
    <div class="section">
      <h2>Detection Timeline</h2>
      <div id="timeline" class="chart"></div>
    </div>

    <div class="section">
      <h2>Daily TPMS Event Volume</h2>
      <div id="daily" class="small-chart"></div>
    </div>

    <div class="section">
      <h2>Hourly TPMS Event Volume</h2>
      <div id="hourly" class="small-chart"></div>
    </div>

    <div class="section">
      <h2>Pressure Over Time</h2>
      <div id="pressure" class="chart"></div>
    </div>
"""


def recent_passes_section(rows):
    html = """
    <details class="section" open>
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Recent Passes</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Single-sensor passes are included, but they are weak evidence next to a busy road.</p>
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
      <p class="muted">Raw sensor-level summary. Use this to label vehicles.</p>
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
            <th>Avg Pressure</th>
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
      <div class="toolbar">
        <input placeholder="Search recent events..." oninput="filterTable('eventTable', this.value)">
      </div>
      <table id="eventTable">
        <thead>
          <tr>
            <th>Time</th>
            <th>Sensor ID</th>
            <th>Model</th>
            <th>Pressure</th>
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
      <p class="muted">Newest raw rtl_433 JSONL packets from the active log file. This includes packets that may not be parsed as TPMS events.</p>
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
    return f"""
  </main>

  <script>
    const points = {json.dumps(timeline_points)};
    const dailyCounts = {json.dumps(daily_counts)};
    const hourlyCounts = {json.dumps(hourly_counts)};
    const refreshWebhookUrl = "/api/webhook/{safe_text(REFRESH_WEBHOOK_ID)}";
    const vehicleMapEditWebhookUrl = "/api/webhook/tpms-vehicle-map-edit-b8f41c6a9e73";

    async function refreshReport() {{
      const button = document.getElementById("refreshButton");
      const originalText = button.innerText;

      try {{
        button.disabled = true;
        button.innerText = "Refreshing...";

        const response = await fetch(refreshWebhookUrl, {{
          method: "POST"
        }});

        if (!response.ok) {{
          throw new Error(`HTTP ${{response.status}}`);
        }}

        button.innerText = "Refresh requested";

        setTimeout(() => {{
          window.location.reload();
        }}, 2500);
      }} catch (error) {{
        console.error(error);
        button.innerText = "Refresh failed";
        setTimeout(() => {{
          button.innerText = originalText;
          button.disabled = false;
        }}, 4000);
      }}
    }}

    async function editVehicleMapFromButton(button) {{
      const originalText = button.innerText;

      try {{
        const payload = JSON.parse(button.dataset.payload || "{{}}");

        button.disabled = true;
        button.innerText = "Saving...";

        const response = await fetch(vehicleMapEditWebhookUrl, {{
          method: "POST",
          headers: {{
            "Content-Type": "application/json"
          }},
          body: JSON.stringify(payload)
        }});

        if (!response.ok) {{
          throw new Error(`HTTP ${{response.status}}`);
        }}

        button.innerText = "Saved";

        setTimeout(() => {{
          window.location.reload();
        }}, 2500);
      }} catch (error) {{
        console.error(error);
        button.innerText = "Failed";

        setTimeout(() => {{
          button.innerText = originalText;
          button.disabled = false;
        }}, 4000);
      }}
    }}

    function filterTable(tableId, query) {{
      const q = query.toLowerCase();
      const table = document.getElementById(tableId);
      const rows = table.querySelectorAll("tbody tr");

      rows.forEach(row => {{
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(q) ? "" : "none";
      }});
    }}

    function makeTablesSortable() {{
      document.querySelectorAll("table").forEach(table => {{
        table.querySelectorAll("th").forEach((th, index) => {{
          th.addEventListener("click", () => {{
            const tbody = table.querySelector("tbody");
            if (!tbody) return;

            const rows = Array.from(tbody.querySelectorAll("tr"));
            const current = th.getAttribute("data-sort") || "none";
            const next = current === "asc" ? "desc" : "asc";

            table.querySelectorAll("th").forEach(h => h.removeAttribute("data-sort"));
            th.setAttribute("data-sort", next);

            rows.sort((a, b) => {{
              const av = a.children[index]?.innerText.trim() || "";
              const bv = b.children[index]?.innerText.trim() || "";

              const an = Number(av.replace(/[^0-9.-]/g, ""));
              const bn = Number(bv.replace(/[^0-9.-]/g, ""));

              let result;

              if (!Number.isNaN(an) && !Number.isNaN(bn) && av !== "" && bv !== "") {{
                result = an - bn;
              }} else {{
                result = av.localeCompare(bv);
              }}

              return next === "asc" ? result : -result;
            }});

            rows.forEach(row => tbody.appendChild(row));
          }});
        }});
      }});
    }}

    makeTablesSortable();

    function showReportTab(tabId) {{
      document.querySelectorAll(".tab-panel").forEach(panel => {{
        panel.classList.toggle("active", panel.id === tabId);
      }});

      document.querySelectorAll(".tab-button").forEach(button => {{
        const isActive = button.getAttribute("data-tab-target") === tabId;
        button.classList.toggle("active", isActive);
      }});

      localStorage.setItem("tpmsReportActiveTab", tabId);

      if (tabId === "tab-charts" && window.Plotly) {{
        setTimeout(() => {{
          document.querySelectorAll("#tab-charts .js-plotly-plot").forEach(chart => {{
            Plotly.Plots.resize(chart);
          }});
        }}, 50);
      }}
    }}

    const savedTab = localStorage.getItem("tpmsReportActiveTab");

    if (savedTab && document.getElementById(savedTab)) {{
      showReportTab(savedTab);
    }}

    Plotly.newPlot("timeline", [{{
      x: points.map(p => p.time),
      y: points.map(p => p.sensor_id),
      mode: "markers",
      type: "scatter",
      text: points.map(p => `${{p.sensor_id}} ${{p.model || ""}}`),
      marker: {{ size: 7 }}
    }}], {{
      title: "TPMS detections by sensor ID",
      xaxis: {{ title: "Time" }},
      yaxis: {{ title: "TPMS Sensor ID", type: "category" }},
      margin: {{ l: 170, r: 30, t: 50, b: 60 }}
    }});

    Plotly.newPlot("daily", [{{
      x: dailyCounts.map(d => d.date),
      y: dailyCounts.map(d => d.count),
      type: "bar"
    }}], {{
      title: "TPMS events per day",
      xaxis: {{ title: "Date" }},
      yaxis: {{ title: "Event count" }},
      margin: {{ l: 70, r: 30, t: 50, b: 60 }}
    }});

    Plotly.newPlot("hourly", [{{
      x: hourlyCounts.map(d => d.hour),
      y: hourlyCounts.map(d => d.count),
      type: "bar"
    }}], {{
      title: "TPMS events by hour of day",
      xaxis: {{ title: "Hour" }},
      yaxis: {{ title: "Event count" }},
      margin: {{ l: 70, r: 30, t: 50, b: 60 }}
    }});

    const pressurePoints = points.filter(p => p.pressure !== null && p.pressure !== undefined);

    Plotly.newPlot("pressure", [{{
      x: pressurePoints.map(p => p.time),
      y: pressurePoints.map(p => p.pressure),
      mode: "markers",
      type: "scatter",
      text: pressurePoints.map(p => `${{p.sensor_id}} ${{p.model || ""}} ${{p.pressure_unit || ""}}`),
      marker: {{ size: 7 }}
    }}], {{
      title: "TPMS pressure values",
      xaxis: {{ title: "Time" }},
      yaxis: {{ title: "Pressure" }},
      margin: {{ l: 80, r: 30, t: 50, b: 60 }}
    }});
  </script>
</body>
</html>
"""
