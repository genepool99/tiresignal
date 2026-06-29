import json
from datetime import datetime

from tpms_config import (
    DB_PATH,
    LOG_PATH,
    MAX_CANDIDATE_SENSOR_COUNT,
    PASS_WINDOW_SECONDS,
    REPORT_PATH,
    SERVICE_PORT,
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

    .chart-toolbar {{
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      margin: 0 0 20px;
      padding: 12px 14px;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--card);
    }}

    .chart-toolbar label {{
      font-weight: 800;
    }}

    .chart-toolbar select {{
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 14px;
      min-width: 220px;
      background: #ffffff;
      color: var(--text);
    }}

    .chart-loading {{
      display: none;
      align-items: center;
      gap: 10px;
      width: fit-content;
      margin: -8px 0 16px;
      padding: 9px 12px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: var(--info-bg);
      color: var(--info-text);
      font-weight: 800;
    }}

    .chart-option-row {{
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
      margin: 6px 0 14px;
    }}

    .pressure-option-row {{
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--soft);
    }}

    .chart-toggle-control {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      flex: 0 0 auto;
      color: var(--text);
      font-weight: 800;
      cursor: pointer;
      user-select: none;
    }}

    .chart-toggle-control input {{
      position: absolute;
      opacity: 0;
      pointer-events: none;
    }}

    .chart-toggle-slider {{
      position: relative;
      width: 38px;
      height: 22px;
      border-radius: 999px;
      background: #cbd5e1;
      box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.12);
      transition: background 0.15s ease;
    }}

    .chart-toggle-slider::after {{
      content: "";
      position: absolute;
      top: 3px;
      left: 3px;
      width: 16px;
      height: 16px;
      border-radius: 999px;
      background: #ffffff;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.25);
      transition: transform 0.15s ease;
    }}

    .chart-toggle-control input:checked + .chart-toggle-slider {{
      background: var(--accent);
    }}

    .chart-toggle-control input:checked + .chart-toggle-slider::after {{
      transform: translateX(16px);
    }}

    .chart-toggle-control input:focus-visible + .chart-toggle-slider {{
      outline: 3px solid rgba(37, 99, 235, 0.25);
      outline-offset: 2px;
    }}

    .chart-toggle-label {{
      white-space: nowrap;
    }}

    .chart-inline-note {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }}

    @media (max-width: 700px) {{
      .pressure-option-row {{
        align-items: flex-start;
      }}

      .chart-toggle-label {{
        white-space: normal;
      }}
    }}

    .chart-loading.active {{
      display: inline-flex;
    }}

    .chart-loading::before {{
      content: "";
      width: 14px;
      height: 14px;
      border: 2px solid rgba(91, 33, 182, 0.25);
      border-top-color: var(--info-text);
      border-radius: 999px;
      animation: chart-loading-spin 0.8s linear infinite;
    }}

    @keyframes chart-loading-spin {{
      to {{
        transform: rotate(360deg);
      }}
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
    <div class="chart-toolbar">
      <label for="chart-time-filter">Time range</label>
      <select id="chart-time-filter">
        <option value="all">All data</option>
        <option value="24h">Last 24 hours</option>
        <option value="7d" selected>Last 7 days</option>
        <option value="30d">Last 30 days</option>
      </select>
      <span class="muted">Filters charts using event timestamps from this report.</span>
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
    const allTimelinePoints = {json.dumps(timeline_points)};
    const serviceBaseUrl = `http://${{window.location.hostname}}:{safe_text(SERVICE_PORT)}`;
    const refreshWebhookUrl = `${{serviceBaseUrl}}/refresh`;
    const vehicleMapEditWebhookUrl = `${{serviceBaseUrl}}/vehicle-map-edit`;
    const PRESSURE_SUSPICIOUS_PSI = 120;
    const MAX_SCATTER_POINTS = 5000;

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

    let chartsRendered = false;
    let chartsRenderPending = false;

    function setChartsLoading(isLoading) {{
      const loading = document.getElementById("charts-loading");

      if (!loading) return;

      loading.classList.toggle("active", isLoading);
      loading.setAttribute("aria-hidden", isLoading ? "false" : "true");
    }}

    function renderChartsSoon() {{
      if (chartsRenderPending) return;

      chartsRendered = true;
      chartsRenderPending = true;
      setChartsLoading(true);

      const runRender = () => {{
        try {{
          renderCharts();
        }} finally {{
          chartsRenderPending = false;
          setChartsLoading(false);
        }}
      }};

      if (window.requestAnimationFrame) {{
        requestAnimationFrame(() => setTimeout(runRender, 0));
      }} else {{
        setTimeout(runRender, 0);
      }}
    }}

    function ensureChartsRendered() {{
      if (!chartsRendered) {{
        renderChartsSoon();
      }}
    }}

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
        ensureChartsRendered();

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

    function parseChartTime(value) {{
      const date = new Date(value);

      if (Number.isNaN(date.getTime())) {{
        return null;
      }}

      return date;
    }}

    function getNewestChartTimestamp(points) {{
      let newest = null;

      points.forEach(point => {{
        const date = parseChartTime(point.time);

        if (!date) return;

        if (!newest || date > newest) {{
          newest = date;
        }}
      }});

      return newest;
    }}

    function getFilteredChartPointsByTime() {{
      const filter = document.getElementById("chart-time-filter");
      const selectedRange = filter ? filter.value : "all";

      if (selectedRange === "all") {{
        return allTimelinePoints;
      }}

      const newest = getNewestChartTimestamp(allTimelinePoints);

      if (!newest) {{
        return [];
      }}

      const rangeHours = {{
        "24h": 24,
        "7d": 24 * 7,
        "30d": 24 * 30
      }}[selectedRange];

      if (!rangeHours) {{
        return allTimelinePoints;
      }}

      const cutoff = newest.getTime() - (rangeHours * 60 * 60 * 1000);

      return allTimelinePoints.filter(point => {{
        const date = parseChartTime(point.time);
        return date && date.getTime() >= cutoff && date.getTime() <= newest.getTime();
      }});
    }}

    function localDateLabel(value) {{
      const date = parseChartTime(value);

      if (!date) {{
        return "Unknown";
      }}

      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${{year}}-${{month}}-${{day}}`;
    }}

    function localHourLabel(value) {{
      const date = parseChartTime(value);

      if (!date) {{
        return "Unknown";
      }}

      return `${{String(date.getHours()).padStart(2, "0")}}:00`;
    }}

    function countBy(points, labelFn) {{
      const counts = new Map();

      points.forEach(point => {{
        const label = labelFn(point);
        counts.set(label, (counts.get(label) || 0) + 1);
      }});

      return Array.from(counts.entries())
        .map(([label, count]) => ({{ label, count }}))
        .sort((a, b) => a.label.localeCompare(b.label));
    }}

    function countByDate(points) {{
      return countBy(
        points.filter(point => parseChartTime(point.time)),
        point => localDateLabel(point.time)
      );
    }}

    function countByModelWithProtocols(points) {{
      const models = new Map();

      points.forEach(point => {{
        const model = categoryValue(point.model);
        const protocol = categoryValue(point.protocol);

        if (!models.has(model)) {{
          models.set(model, {{
            label: model,
            count: 0,
            protocols: new Map()
          }});
        }}

        const row = models.get(model);
        row.count += 1;
        row.protocols.set(protocol, (row.protocols.get(protocol) || 0) + 1);
      }});

      return Array.from(models.values())
        .map(row => {{
          const protocols = Array.from(row.protocols.entries())
            .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
          const protocolText = protocols.length === 1
            ? `Protocol: ${{protocols[0][0]}}`
            : `Protocols: ${{protocols.map(([protocol, count]) => `${{protocol}} (${{count}})`).join(", ")}}`;

          return {{
            label: row.label,
            count: row.count,
            hoverText: `${{row.label}}<br>Events: ${{row.count}}<br>${{protocolText}}`
          }};
        }})
        .sort((a, b) => a.label.localeCompare(b.label));
    }}

    function hourlyCountsFor(points) {{
      const counts = new Map();

      for (let hour = 0; hour < 24; hour += 1) {{
        counts.set(`${{String(hour).padStart(2, "0")}}:00`, 0);
      }}

      points.forEach(point => {{
        if (!parseChartTime(point.time)) return;

        const label = localHourLabel(point.time);
        counts.set(label, (counts.get(label) || 0) + 1);
      }});

      return Array.from(counts.entries())
        .map(([label, count]) => ({{ label, count }}))
        .sort((a, b) => a.label.localeCompare(b.label));
    }}

    function numericValue(value) {{
      if (value === null || value === undefined || value === "") {{
        return null;
      }}

      const number = Number(value);
      return Number.isFinite(number) ? number : null;
    }}

    function downsampleRows(rows, maxPoints = MAX_SCATTER_POINTS) {{
      if (!Array.isArray(rows) || rows.length <= maxPoints) return rows;
      if (maxPoints <= 0) return [];

      const step = rows.length / maxPoints;
      const sampled = [];

      for (let index = 0; index < maxPoints; index += 1) {{
        sampled.push(rows[Math.floor(index * step)]);
      }}

      return sampled;
    }}

    function samplingNote(sampledCount, totalCount) {{
      if (totalCount <= sampledCount) return "";
      return `Showing ${{sampledCount.toLocaleString()}} of ${{totalCount.toLocaleString()}} points for performance.`;
    }}

    function chartTitleWithSampling(title, notes) {{
      const note = notes.filter(Boolean).join(" ");
      return note ? `${{title}}<br><sup>${{note}}</sup>` : title;
    }}

    function pressurePointSamplingNote(label, sampledCount, totalCount) {{
      if (totalCount <= sampledCount) return "";
      return `${{label}}: showing ${{sampledCount.toLocaleString()}} of ${{totalCount.toLocaleString()}} points.`;
    }}

    function pressurePointValue(point) {{
      const pressurePsi = numericValue(point.pressure_psi);

      if (pressurePsi !== null) {{
        return {{
          normalizedPsi: pressurePsi,
          originalValue: pressurePsi,
          originalUnit: "PSI"
        }};
      }}

      const pressureKpa = numericValue(point.pressure_kpa);

      if (pressureKpa !== null) {{
        return {{
          normalizedPsi: pressureKpa * 0.145038,
          originalValue: pressureKpa,
          originalUnit: "kPa"
        }};
      }}

      return null;
    }}

    function formatPressure(value) {{
      return Number(value).toFixed(1);
    }}

    function pressureHoverText(row, isSuspicious = false) {{
      const model = row.point.model || "Unknown";
      const protocol = row.point.protocol || "Unknown";
      const temperatureC = numericValue(row.point.temperature_c);
      const temperatureText = temperatureC !== null
        ? `<br>Temperature C: ${{temperatureC.toFixed(1)}}`
        : "";
      return [
        isSuspicious ? "Suspicious high pressure<br>" : "",
        `Sensor ID: ${{row.point.sensor_id}}`,
        `<br>Model: ${{model}}`,
        `<br>Protocol: ${{protocol}}`,
        temperatureText,
        `<br>Original pressure: ${{formatPressure(row.originalValue)}} ${{row.originalUnit}}`,
        `<br>Normalized pressure: ${{formatPressure(row.normalizedPsi)}} PSI`
      ].join("");
    }}

    function pressureTrace(name, rows, isSuspicious = false) {{
      return {{
        name,
        x: rows.map(row => row.point.time),
        y: rows.map(row => Number(formatPressure(row.normalizedPsi))),
        mode: "markers",
        type: "scatter",
        text: rows.map(row => pressureHoverText(row, isSuspicious)),
        hovertemplate: "%{{text}}<extra></extra>",
        marker: {{
          size: isSuspicious ? 8 : 7,
          symbol: isSuspicious ? "x" : "circle"
        }}
      }};
    }}

    function updatePressureChartNote(hiddenSuspiciousCount) {{
      const note = document.getElementById("pressureChartNote");

      if (!note) return;

      note.textContent = `Suspicious pressure points above ${{PRESSURE_SUSPICIOUS_PSI}} PSI are hidden by default. Hidden suspicious points: ${{hiddenSuspiciousCount}}`;
    }}

    function categoryValue(value) {{
      const text = String(value || "").trim();
      return text || "Unknown";
    }}

    function batteryStatus(value) {{
      if (value === null || value === undefined || String(value).trim() === "") {{
        return "Unknown";
      }}

      if (typeof value === "boolean") {{
        return value ? "Battery OK" : "Battery Low";
      }}

      const text = String(value).trim().toLowerCase();

      if (["1", "true", "ok", "yes", "y", "good"].includes(text)) {{
        return "Battery OK";
      }}

      if (["0", "false", "low", "no", "n", "bad"].includes(text)) {{
        return "Battery Low";
      }}

      return "Unknown";
    }}

    function groupedMetricTraces(points, valueFn, textFn) {{
      const bySensorId = new Map();

      points.forEach(point => {{
        const value = valueFn(point);

        if (value === null || value === undefined) return;

        const sensorId = point.sensor_id || "Unknown";

        if (!bySensorId.has(sensorId)) {{
          bySensorId.set(sensorId, []);
        }}

        bySensorId.get(sensorId).push({{ point, value }});
      }});

      return Array.from(bySensorId.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([sensorId, rows]) => ({{
          name: sensorId,
          x: rows.map(row => row.point.time),
          y: rows.map(row => row.value),
          mode: "markers",
          type: "scatter",
          text: rows.map(row => textFn(row.point, row.value)),
          marker: {{ size: 7 }}
        }}));
    }}

    function maybeBatteryTraceRows(points) {{
      return points
        .map(point => ({{
          point,
          value: numericValue(point.maybe_battery)
        }}))
        .filter(row => row.value !== null);
    }}

    function maybeBatteryTraces(rows) {{
      const byModel = new Map();

      rows.forEach(row => {{
        const model = categoryValue(row.point.model);

        if (!byModel.has(model)) {{
          byModel.set(model, []);
        }}

        byModel.get(model).push(row);
      }});

      return Array.from(byModel.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([model, rows]) => ({{
          name: model,
          x: rows.map(row => row.point.time),
          y: rows.map(row => row.value),
          mode: "markers",
          type: "scatter",
          text: rows.map(row => `${{row.point.sensor_id || "Unknown"}}<br>${{row.point.model || "Unknown"}}<br>Protocol: ${{row.point.protocol || "Unknown"}}<br>maybe_battery: ${{row.value}}`),
          hovertemplate: "%{{text}}<extra></extra>",
          marker: {{ size: 7 }}
        }}));
    }}

    function metricTrace(name, rows) {{
      if (rows.length < 2) {{
        return null;
      }}

      return {{
        name,
        x: rows.map(row => row.point.time),
        y: rows.map(row => row.value),
        mode: "markers",
        type: "scatter",
        text: rows.map(row => `${{row.point.sensor_id || "Unknown"}} ${{name}}`),
        marker: {{ size: 7 }}
      }};
    }}

    function metricRows(points, field) {{
      return points
        .map(point => ({{ point, value: numericValue(point[field]) }}))
        .filter(row => row.value !== null);
    }}

    function emptyChart(chartId, title, message, yAxisTitle = "") {{
      Plotly.newPlot(chartId, [], {{
        title,
        xaxis: {{ title: "Time" }},
        yaxis: {{ title: yAxisTitle }},
        annotations: [{{
          text: message,
          xref: "paper",
          yref: "paper",
          x: 0.5,
          y: 0.5,
          showarrow: false,
          font: {{ size: 14 }}
        }}],
        margin: {{ l: 80, r: 30, t: 50, b: 60 }}
      }});
    }}

    function renderChartSafely(chartId, chartTitle, yAxisTitle, renderFn) {{
      try {{
        renderFn();
      }} catch (error) {{
        console.error(`${{chartTitle}} failed to render`, error);

        try {{
          emptyChart(chartId, chartTitle, "Chart failed to render; check browser console", yAxisTitle);
        }} catch (emptyError) {{
          console.error(`${{chartTitle}} error annotation failed to render`, emptyError);
        }}
      }}
    }}

    function renderBarChart(chartId, title, rows, xTitle, yTitle, emptyMessage) {{
      if (!rows.length) {{
        emptyChart(chartId, title, emptyMessage, yTitle);
        return;
      }}

      Plotly.newPlot(chartId, [{{
        x: rows.map(row => row.label),
        y: rows.map(row => row.count),
        type: "bar",
        text: rows.map(row => row.hoverText || `${{row.label}}<br>Events: ${{row.count}}`),
        hovertemplate: "%{{text}}<extra></extra>"
      }}], {{
        title,
        xaxis: {{ title: xTitle }},
        yaxis: {{ title: yTitle }},
        margin: {{ l: 70, r: 30, t: 50, b: 80 }}
      }});
    }}

    function renderCharts() {{
      const points = getFilteredChartPointsByTime();
      const emptyMessage = "No data for selected time range";
      const suspiciousPressureToggle = document.getElementById("chart-show-suspicious-pressure");
      const showSuspiciousPressure = Boolean(suspiciousPressureToggle && suspiciousPressureToggle.checked);

      if (!points.length) {{
        updatePressureChartNote(0);
        renderChartSafely("timelineChart", "TPMS detections by sensor ID", "TPMS Sensor ID", () => {{
          emptyChart("timelineChart", "TPMS detections by sensor ID", emptyMessage, "TPMS Sensor ID");
        }});
        renderChartSafely("dailyChart", "TPMS events per day", "Event count", () => {{
          emptyChart("dailyChart", "TPMS events per day", emptyMessage, "Event count");
        }});
        renderChartSafely("hourlyChart", "TPMS events by hour of day", "Event count", () => {{
          emptyChart("hourlyChart", "TPMS events by hour of day", emptyMessage, "Event count");
        }});
        renderChartSafely("pressureChart", "TPMS pressure values, normalized to PSI", "Pressure (PSI)", () => {{
          emptyChart("pressureChart", "TPMS pressure values, normalized to PSI", emptyMessage, "Pressure (PSI)");
        }});
        renderChartSafely("temperatureChart", "TPMS temperature values", "Temperature (°C)", () => {{
          emptyChart("temperatureChart", "TPMS temperature values", "Not enough temperature data for this time range", "Temperature (°C)");
        }});
        renderChartSafely("modelChart", "Events by model", "Event count", () => {{
          emptyChart("modelChart", "Events by model", emptyMessage, "Event count");
        }});
        renderChartSafely("batteryChart", "Confirmed Battery Status", "Event count", () => {{
          emptyChart("batteryChart", "Confirmed Battery Status", emptyMessage, "Event count");
        }});
        renderChartSafely("maybeBatteryChart", "Unconfirmed battery signal", "maybe_battery raw value", () => {{
          emptyChart("maybeBatteryChart", "Unconfirmed battery signal", "Not enough maybe_battery data for this time range", "maybe_battery raw value");
        }});
        renderChartSafely("signalChart", "TPMS signal quality", "Signal value", () => {{
          emptyChart("signalChart", "TPMS signal quality", "Not enough signal data for this time range", "Signal value");
        }});
        return;
      }}

      renderChartSafely("timelineChart", "TPMS detections by sensor ID", "TPMS Sensor ID", () => {{
        const timelineRows = downsampleRows(points);

        Plotly.newPlot("timelineChart", [{{
          x: timelineRows.map(point => point.time),
          y: timelineRows.map(point => point.sensor_id),
          mode: "markers",
          type: "scatter",
          text: timelineRows.map(point => `${{point.sensor_id}} ${{point.model || ""}}`),
          marker: {{ size: 7 }}
        }}], {{
          title: chartTitleWithSampling("TPMS detections by sensor ID", [
            samplingNote(timelineRows.length, points.length)
          ]),
          xaxis: {{ title: "Time" }},
          yaxis: {{ title: "TPMS Sensor ID", type: "category" }},
          margin: {{ l: 170, r: 30, t: 70, b: 60 }}
        }});
      }});

      renderChartSafely("dailyChart", "TPMS events per day", "Event count", () => {{
        renderBarChart(
          "dailyChart",
          "TPMS events per day",
          countByDate(points),
          "Date",
          "Event count",
          emptyMessage
        );
      }});

      renderChartSafely("hourlyChart", "TPMS events by hour of day", "Event count", () => {{
        renderBarChart(
          "hourlyChart",
          "TPMS events by hour of day",
          hourlyCountsFor(points),
          "Hour",
          "Event count",
          emptyMessage
        );
      }});

      renderChartSafely("pressureChart", "TPMS pressure values, normalized to PSI", "Pressure (PSI)", () => {{
        const pressurePoints = points
          .map(point => {{
            const pressure = pressurePointValue(point);

            if (!pressure) return null;

            return {{
              point,
              normalizedPsi: pressure.normalizedPsi,
              originalValue: pressure.originalValue,
              originalUnit: pressure.originalUnit,
              isSuspicious: pressure.normalizedPsi > PRESSURE_SUSPICIOUS_PSI
            }};
          }})
          .filter(row => row !== null);
        const normalPressurePoints = pressurePoints.filter(row => !row.isSuspicious);
        const suspiciousPressurePoints = pressurePoints.filter(row => row.isSuspicious);
        const hiddenSuspiciousCount = showSuspiciousPressure ? 0 : suspiciousPressurePoints.length;

        updatePressureChartNote(hiddenSuspiciousCount);

        if (pressurePoints.length) {{
          const pressureTraces = [];
          const sampledNormalPressurePoints = downsampleRows(normalPressurePoints);
          const sampledSuspiciousPressurePoints = downsampleRows(suspiciousPressurePoints);
          const pressureSamplingNotes = [
            pressurePointSamplingNote("Normal", sampledNormalPressurePoints.length, normalPressurePoints.length)
          ];

          if (normalPressurePoints.length) {{
            pressureTraces.push(pressureTrace("Pressure", sampledNormalPressurePoints));
          }}

          if (showSuspiciousPressure && suspiciousPressurePoints.length) {{
            pressureTraces.push(pressureTrace("Suspicious pressure", sampledSuspiciousPressurePoints, true));
            pressureSamplingNotes.push(
              pressurePointSamplingNote("Suspicious", sampledSuspiciousPressurePoints.length, suspiciousPressurePoints.length)
            );
          }}

          if (pressureTraces.length) {{
            Plotly.newPlot("pressureChart", pressureTraces, {{
              title: chartTitleWithSampling("TPMS pressure values, normalized to PSI", pressureSamplingNotes),
              xaxis: {{ title: "Time" }},
              yaxis: {{ title: "Pressure (PSI)" }},
              margin: {{ l: 80, r: 30, t: 70, b: 60 }}
            }});
          }} else {{
            emptyChart("pressureChart", "TPMS pressure values, normalized to PSI", "Only suspicious pressure points in this time range", "Pressure (PSI)");
          }}
        }} else {{
          emptyChart("pressureChart", "TPMS pressure values, normalized to PSI", emptyMessage, "Pressure (PSI)");
        }}
      }});

      renderChartSafely("temperatureChart", "TPMS temperature values", "Temperature (°C)", () => {{
        const temperaturePoints = points
          .map(point => ({{
            point,
            value: numericValue(point.temperature_c)
          }}))
          .filter(row => row.value !== null);

        if (temperaturePoints.length >= 2) {{
          const sampledTemperaturePoints = downsampleRows(temperaturePoints);

          Plotly.newPlot("temperatureChart", [{{
            name: "Temperature",
            x: sampledTemperaturePoints.map(row => row.point.time),
            y: sampledTemperaturePoints.map(row => row.value),
            mode: "markers",
            type: "scatter",
            text: sampledTemperaturePoints.map(row => `${{row.point.sensor_id || "Unknown"}}<br>${{row.point.model || "Unknown"}}<br>Protocol: ${{row.point.protocol || "Unknown"}}<br>Temperature C: ${{row.value.toFixed(1)}}`),
            hovertemplate: "%{{text}}<extra></extra>",
            marker: {{ size: 5 }}
          }}], {{
            title: chartTitleWithSampling("TPMS temperature values", [
              samplingNote(sampledTemperaturePoints.length, temperaturePoints.length)
            ]),
            xaxis: {{ title: "Time" }},
            yaxis: {{ title: "Temperature (°C)" }},
            margin: {{ l: 80, r: 30, t: 70, b: 60 }}
          }});
        }} else {{
          emptyChart("temperatureChart", "TPMS temperature values", "Not enough temperature data for this time range", "Temperature (°C)");
        }}
      }});

      renderChartSafely("modelChart", "Events by model", "Event count", () => {{
        renderBarChart(
          "modelChart",
          "Events by model",
          countByModelWithProtocols(points),
          "Model",
          "Event count",
          emptyMessage
        );
      }});

      renderChartSafely("batteryChart", "Confirmed Battery Status", "Event count", () => {{
        renderBarChart(
          "batteryChart",
          "Confirmed Battery Status",
          countBy(points, point => batteryStatus(point.battery_ok)),
          "Battery status",
          "Event count",
          emptyMessage
        );
      }});

      renderChartSafely("maybeBatteryChart", "Unconfirmed battery signal", "maybe_battery raw value", () => {{
        const maybeBatteryRows = maybeBatteryTraceRows(points);
        const sampledMaybeBatteryRows = downsampleRows(maybeBatteryRows);
        const maybeBatteryTracesForPlot = maybeBatteryTraces(sampledMaybeBatteryRows);

        if (maybeBatteryRows.length >= 2 && maybeBatteryTracesForPlot.length) {{
          Plotly.newPlot("maybeBatteryChart", maybeBatteryTracesForPlot, {{
            title: chartTitleWithSampling("Unconfirmed battery signal", [
              samplingNote(sampledMaybeBatteryRows.length, maybeBatteryRows.length)
            ]),
            xaxis: {{ title: "Time" }},
            yaxis: {{ title: "maybe_battery raw value" }},
            margin: {{ l: 80, r: 30, t: 70, b: 60 }}
          }});
        }} else {{
          emptyChart("maybeBatteryChart", "Unconfirmed battery signal", "Not enough maybe_battery data for this time range", "maybe_battery raw value");
        }}
      }});

      renderChartSafely("signalChart", "TPMS signal quality", "Signal value", () => {{
        const signalRows = [
          ["RSSI", metricRows(points, "rssi")],
          ["SNR", metricRows(points, "snr")],
          ["Noise", metricRows(points, "noise")]
        ];
        const signalSamplingNotes = [];
        const signalTraces = signalRows
          .map(([name, rows]) => {{
            const sampledRows = downsampleRows(rows);
            const note = pressurePointSamplingNote(name, sampledRows.length, rows.length);

            if (note) {{
              signalSamplingNotes.push(note);
            }}

            return metricTrace(name, sampledRows);
          }})
          .filter(Boolean);

        if (signalTraces.length) {{
          Plotly.newPlot("signalChart", signalTraces, {{
            title: chartTitleWithSampling("TPMS signal quality", signalSamplingNotes),
            xaxis: {{ title: "Time" }},
            yaxis: {{ title: "Signal value" }},
            margin: {{ l: 80, r: 30, t: 70, b: 60 }}
          }});
        }} else {{
          emptyChart("signalChart", "TPMS signal quality", "Not enough signal data for this time range", "Signal value");
        }}
      }});
    }}

    const chartTimeFilter = document.getElementById("chart-time-filter");
    const suspiciousPressureToggle = document.getElementById("chart-show-suspicious-pressure");

    if (chartTimeFilter) {{
      chartTimeFilter.addEventListener("change", () => {{
        if (chartsRendered) renderChartsSoon();
      }});
    }}

    if (suspiciousPressureToggle) {{
      suspiciousPressureToggle.addEventListener("change", () => {{
        if (chartsRendered) renderChartsSoon();
      }});
    }}
  </script>
</body>
</html>
"""
