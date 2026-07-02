import json
from collections import defaultdict
from datetime import datetime, timezone

from tpms_config import (
    APP_VERSION,
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
from utils import category_label, compute_signal_tags, display_dt, display_time, parse_time, safe_text

from report_css import CSS_BLOCK
from report_js import JS_BLOCK
from report_templates import CANDIDATE_DRAWER_HTML


def pill(text, category="info", description=None):
    text = safe_text(text)
    category = safe_text(category or "info")
    if description:
        desc = safe_text(description)
        return f'<span class="pill {category}" title="{desc}" aria-label="{text}: {desc}">{text}</span>'
    return f'<span class="pill {category}">{text}</span>'


def vehicle_status_html(name, category):
    if name:
        normalized = category or "known"
        return pill(name, normalized, category_description(normalized))

    return pill("Unknown", "unknown", category_description("unknown"))


def row_actions_menu(items, label="Vehicle actions"):
    toggle = (
        f'<button type="button"'
        f' class="small-action-button row-actions-toggle"'
        f' aria-label="{safe_text(label)}"'
        f' aria-haspopup="menu"'
        f' aria-expanded="false"'
        f' onclick="toggleRowActionsMenu(this)">&#x22EE;</button>'
    )
    menu_items_html = ""
    for item in items:
        danger = " row-actions-menu-item--danger" if item.get("danger") else ""
        handler = safe_text(item.get("handler", "rowMenuSubmitAction"))
        data_attr = safe_text(item.get("data_attr", "payload"))
        payload = safe_text(json.dumps(item["payload"]))
        menu_items_html += (
            f'<button type="button"'
            f' class="row-actions-menu-item{danger}"'
            f' role="menuitem"'
            f' data-{data_attr}="{payload}"'
            f' onclick="{handler}(this)">{safe_text(item["label"])}</button>'
        )
    return (
        f'<div class="row-actions">'
        f'{toggle}'
        f'<div class="row-actions-menu" role="menu" hidden>'
        f'{menu_items_html}'
        f'</div>'
        f'</div>'
    )


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


def pattern_label_class(label_text):
    mapping = {
        "Regular visitor": "pattern-regular",
        "Maybe a fluke": "pattern-fluke",
        "Recently active": "pattern-recent",
        "Went quiet": "pattern-quiet",
        "Occasional visitor": "pattern-occasional",
        "Mixed sensor types": "pattern-mixed",
        "Poss. Stalker": "pattern-stalker",
        "Weekend Warrior": "pattern-weekend",
        "Commuter": "pattern-commuter",
    }
    return mapping.get(label_text, "pattern-default")


def compute_mixed_sensor_label(sensor_ids, sensor_model_map, sensor_protocol_map):
    all_models = set().union(*(sensor_model_map.get(sid, set()) for sid in sensor_ids))
    all_protocols = set().union(*(sensor_protocol_map.get(sid, set()) for sid in sensor_ids))
    if len(all_models) > 1 or len(all_protocols) > 1:
        return {
            "text": "Mixed sensor types",
            "caveat": (
                "This group includes more than one sensor model or protocol. "
                "That can happen with replacement, aftermarket, winter-wheel, or cloned sensors, "
                "so this is only a caution — not a rejection."
            ),
        }
    return None


PATTERN_LABEL_DESCRIPTIONS = {
    "Mixed sensor types": "This group includes more than one sensor model or protocol. Possible with replacement, aftermarket, winter-wheel, or cloned sensors. Caution only — not a rejection.",
    "Regular visitor": "Seen across many separate passes. Probably worth reviewing.",
    "Recently active": "Seen recently relative to this report.",
    "Maybe a fluke": "Only a few repeated passes so far. Could be a coincidence.",
    "Went quiet": "Not seen recently relative to this report.",
    "Occasional visitor": "Seen over an extended period, but not very often.",
    "Poss. Stalker": "Repeated unknown signal seen across multiple days and still recently active.",
    "Weekend Warrior": "Unknown signal appears mostly on weekends.",
    "Commuter": "Unknown signal appears mostly on weekdays.",
}

CONFIDENCE_DESCRIPTIONS = {
    "Very strong": "Four or more sensors seen together across several passes.",
    "Strong": "Three or more sensors seen together across repeated passes.",
    "Possible": "Two sensors seen together across repeated passes.",
    "Weak": "Limited repeated evidence. Review before labeling.",
    "Single sensor": "Only one sensor is represented in this group.",
}


CATEGORY_DESCRIPTIONS = {
    "known": "Labeled as a known vehicle.",
    "watch": "Saved to the watchlist for follow-up.",
    "ignore": "Marked as ignored/noise in the vehicle map.",
    "unknown": "No saved vehicle-map entry currently matches this group.",
}


def category_description(category):
    return CATEGORY_DESCRIPTIONS.get((category or "unknown").lower(), "")


def category_pill(category):
    normalized = category or "unknown"
    return pill(category_label(normalized), normalized, category_description(normalized))


def saved_match_html(known_vehicle, category, known_match):
    if known_vehicle:
        normalized = category or "known"
        name_pill = pill(known_vehicle, normalized, category_description(normalized))
        match_text = known_match_text(known_match)
        if match_text:
            return f'{name_pill}<br><span class="muted">{safe_text(match_text)}</span>'
        return name_pill
    return '<span class="muted">No saved match</span>'


def pattern_pills(labels):
    html = ""
    for lbl in labels:
        desc = lbl.get("caveat") or lbl.get("description") or PATTERN_LABEL_DESCRIPTIONS.get(lbl.get("text", ""), "")
        cls = safe_text(lbl.get("class", "pattern-default"))
        text = safe_text(lbl.get("text", ""))
        if desc:
            desc_escaped = safe_text(desc)
            html += f'<span class="pill {cls}" title="{desc_escaped}" aria-label="{text}: {desc_escaped}">{text}</span>'
        else:
            html += f'<span class="pill {cls}">{text}</span>'
    return html


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
    vehicles = context["vehicles"]
    ingest_stats = context["ingest_stats"]
    prune_stats = context.get("prune_stats", {})

    sensor_model_map = defaultdict(set)
    sensor_protocol_map = defaultdict(set)
    for event in events:
        sensor_id = event.get("sensor_id")
        if not sensor_id:
            continue
        model = event.get("model") or ""
        protocol = event.get("protocol") or ""
        if model:
            sensor_model_map[sensor_id].add(model)
        if protocol:
            sensor_protocol_map[sensor_id].add(protocol)

    sensor_by_id = {s["sensor_id"]: s for s in sensor_summaries}

    generated_at = datetime.now().astimezone().strftime("%b %-d, %Y, %-I:%M %p")

    timeline_points = [
        {
            "time": e["event_time"].isoformat() if e["event_time"] else e["event_time_text"],
            "sensor_id": e["sensor_id"],
            "model": e["model"],
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

    TIMELINE_MAX_POINTS = 10_000
    timeline_points = timeline_points[-TIMELINE_MAX_POINTS:]

    known_count = len([v for v in vehicles if v.get("category") == "known"])
    watch_count = len([v for v in vehicles if v.get("category") == "watch"])
    ignore_count = len([v for v in vehicles if v.get("category") == "ignore"])
    ignored_vehicles = [v for v in vehicles if v.get("category") == "ignore"]
    raw_packet_lines = tail_log_lines(LOG_PATH, 200)

    html = html_start(generated_at)

    html += f"""
    <div class="tabs" role="tablist" aria-label="TireSignal report sections">
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
    html += new_unknown_section(new_unknown_candidates, sensor_model_map, sensor_protocol_map, sensor_by_id)
    html += overlap_candidates_section(overlap_candidate_summaries, sensor_model_map, sensor_protocol_map, sensor_by_id)
    html += exact_candidates_section(exact_candidate_summaries, sensor_model_map, sensor_protocol_map, sensor_by_id)

    html += """
    </div>

    <div id="tab-charts" class="tab-panel">
"""
    html += charts_section()

    html += """
    </div>

    <div id="tab-details" class="tab-panel">
"""
    SENSOR_TABLE_MIN_COUNT = 5
    SENSOR_TABLE_MAX_ROWS = 1000
    sensor_display_rows = [
        sensor for sensor in sensor_summaries
        if sensor["count"] >= SENSOR_TABLE_MIN_COUNT
    ][:SENSOR_TABLE_MAX_ROWS]
    html += recent_passes_section(recent_pass_rows)
    html += sensor_section(sensor_display_rows)
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
    html += html_end(timeline_points)

    REPORT_PATH.write_text(html, encoding="utf-8")


def html_start(generated_at):
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>TireSignal</title>
  <link rel="icon" type="image/png" sizes="32x32" href="tiresignal-favicon-32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="tiresignal-favicon-180.png">
  <style>{CSS_BLOCK}
.brand-title {{ margin: 0; line-height: 1; }}
.brand-logo {{ height: 90px; width: auto; display: block; }}
@media (max-width: 480px) {{ .brand-logo {{ height: 36px; }} }}
.brand-logo-button {{ display: block; background: none; border: none; padding: 0; margin: 0; cursor: pointer; border-radius: 10px; }}
.brand-logo-button:focus-visible {{ outline: 3px solid rgba(37, 99, 235, 0.35); outline-offset: 3px; }}
.header-meta {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
.header-chip {{ display: inline-flex; align-items: baseline; gap: 5px; font-size: 12px; line-height: 1.4; font-weight: 600; padding: 4px 9px; border-radius: 999px; background: #ffffff; color: var(--text); border: 1px solid var(--border); box-shadow: var(--shadow-sm); white-space: nowrap; }}
.header-chip-label {{ color: var(--muted); font-weight: 700; }}
.header-chip code {{ font-size: 12px; color: var(--text); background: transparent; padding: 0; }}
  </style>
</head>
<body>
  <div id="reportLoadingOverlay" class="report-loading-overlay" role="status" aria-live="polite">
    <div class="report-loading-card">
      <div class="report-loading-spinner" aria-hidden="true"></div>
      <div>
        <div class="report-loading-title">Loading TireSignal report…</div>
        <div class="report-loading-subtitle">Preparing tables, candidates, and charts.</div>
      </div>
    </div>
  </div>
  <header>
    <div class="header-row">
      <div>
        <h1 class="brand-title">
          <button type="button" class="brand-logo-button" onclick="showReportTab('tab-overview')" aria-label="Go to Overview tab">
            <img class="brand-logo" src="tiresignal-logo.png" alt="TireSignal">
          </button>
        </h1>
        <div class="header-meta">
          <span class="header-chip"><span class="header-chip-label">Generated</span>{safe_text(generated_at)}</span>
          <span class="header-chip"><span class="header-chip-label">Version</span>v{safe_text(APP_VERSION)}</span>
          <span class="header-chip" title="{safe_text(LOG_PATH)}"><span class="header-chip-label">Source</span><code>{safe_text(LOG_PATH)}</code></span>
        </div>
      </div>
      <button id="refreshButton" class="refresh-button" onclick="refreshReport()">
        Refresh Report
      </button>
    </div>
  </header>

  <main>
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
    signal_counts = {"Strong": 0, "Normal": 0, "Weak": 0, "Unknown": 0}
    for sensor in sensor_summaries:
        sq = sensor.get("signal_quality", "Unknown")
        signal_counts[sq] = signal_counts.get(sq, 0) + 1

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
      <div class="card">
        <div class="big">{signal_counts["Strong"]}</div>
        <div>Strong Signal Sensors</div>
      </div>
      <div class="card">
        <div class="big">{signal_counts["Normal"]}</div>
        <div>Normal Signal Sensors</div>
      </div>
      <div class="card">
        <div class="big">{signal_counts["Weak"]}</div>
        <div>Weak Signal Sensors</div>
      </div>
      <div class="card">
        <div class="big">{signal_counts["Unknown"]}</div>
        <div>Unknown Signal Sensors</div>
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
            <th>Notes</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
"""

    for row in rows:
        sensor_ids = row["sensor_ids"]
        category = row["category"]

        edit_payload = {
            "action": "add",
            "edit_mode": "saved_vehicle",
            "name": row["name"],
            "category": category,
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

        known_payload = {
            "action": "update_category",
            "name": row["name"],
            "category": "known",
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

        remove_payload = {
            "action": "remove",
            "name": row["name"],
            "sensor_ids": sensor_ids,
        }

        menu_items = [
            {"label": "Edit", "payload": edit_payload, "handler": "rowMenuEdit"},
        ]

        if category == "known":
            menu_items.append({"label": "Move to Watch", "payload": watch_payload, "handler": "rowMenuSubmitAction"})
        elif category == "watch":
            menu_items.append({"label": "Move to Known", "payload": known_payload, "handler": "rowMenuSubmitAction"})

        menu_items.append({"label": "Ignore", "payload": ignore_payload, "handler": "rowMenuSubmitAction"})
        menu_items.append({"label": "Delete", "payload": remove_payload, "handler": "rowMenuSubmitAction", "danger": True})

        html += f"""
          <tr>
            <td>{safe_text(row["name"])}</td>
            <td>{category_pill(row["category"])}</td>
            <td>{row["seen_today"]}</td>
            <td>{row["seen_count"]}</td>
            <td>{safe_text(row["best_match"])}</td>
            <td>{display_time(row["first_seen"])}</td>
            <td>{display_time(row["last_seen"])}</td>
            <td>{safe_text(", ".join(sensor_ids))}</td>
            <td>{safe_text(row["notes"])}</td>
            <td class="actions-cell">{row_actions_menu(menu_items)}</td>
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
            <th>Notes</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
"""

    for row in rows:
        sensor_ids = row.get("sensor_ids", [])
        name = row.get("name", "Ignored Vehicle")
        notes = row.get("notes", "")

        edit_payload = {
            "action": "add",
            "edit_mode": "saved_vehicle",
            "name": name,
            "category": "ignore",
            "notes": notes,
            "sensor_ids": sensor_ids,
        }

        known_payload = {
            "action": "update_category",
            "category": "known",
            "sensor_ids": sensor_ids,
        }

        watch_payload = {
            "action": "update_category",
            "category": "watch",
            "sensor_ids": sensor_ids,
        }

        remove_payload = {
            "action": "remove",
            "name": name,
            "sensor_ids": sensor_ids,
        }

        menu_items = [
            {"label": "Edit", "payload": edit_payload, "handler": "rowMenuEdit"},
            {"label": "Move to Known", "payload": known_payload, "handler": "rowMenuSubmitAction"},
            {"label": "Move to Watch", "payload": watch_payload, "handler": "rowMenuSubmitAction"},
            {"label": "Delete", "payload": remove_payload, "handler": "rowMenuSubmitAction", "danger": True},
        ]

        html += f"""
          <tr>
            <td>{safe_text(name)}</td>
            <td>{safe_text(", ".join(sensor_ids))}</td>
            <td>{safe_text(notes)}</td>
            <td class="actions-cell">{row_actions_menu(menu_items)}</td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def new_unknown_section(rows, sensor_model_map=None, sensor_protocol_map=None, sensor_by_id=None):
    html = """
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Unlabeled Repeat Candidates</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Sensor clusters that appeared together repeatedly, but have not been labeled yet. <button type="button" class="inline-info-button"
          onclick="openInfoModal(this)"
          data-info-title="About Unlabeled Repeat Candidates"
          data-info-body="&lt;p class=&quot;muted&quot;&gt;A group appears here when sensors are heard together repeatedly and are not yet saved to your vehicle map.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Add Watch&lt;/strong&gt; saves the group for follow-up. You can rename it later once you are sure.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Ignore&lt;/strong&gt; is useful for noise like a neighbor, a delivery vehicle, or any signal you do not want to track.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;Leaving a group unlabeled is fine when you need more data before deciding.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;These groups are filtered from Best Guess Candidates — check that section for confidence scores and more detail.&lt;/p&gt;"
        >How this works</button></p>
      <div class="toolbar">
        <input id="newUnknownSearchInput" placeholder="Search unknown candidates..." oninput="filterTable('newUnknownTable', this.value)">
        <div class="candidate-filter-buttons">
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('newUnknownTable', 'newUnknownSearchInput', 'Very strong', 'info')">Very strong</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('newUnknownTable', 'newUnknownSearchInput', 'Strong', 'info')">Strong</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('newUnknownTable', 'newUnknownSearchInput', 'Possible', 'info')">Possible</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('newUnknownTable', 'newUnknownSearchInput', 'High-Confidence Unknown', '')">High-Confidence Unknown</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('newUnknownTable', 'newUnknownSearchInput', 'Poss. Stalker', '')">Poss. Stalker</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('newUnknownTable', 'newUnknownSearchInput', 'Weekend Warrior', '')">Weekend Warrior</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('newUnknownTable', 'newUnknownSearchInput', 'Commuter', '')">Commuter</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('newUnknownTable', 'newUnknownSearchInput', 'Signal Lurker', '')">Signal Lurker</button>
        <button type="button" class="inline-info-button"
          onclick="openInfoModal(this)"
          data-info-title="About the signal filters"
          data-info-body="&lt;p class=&quot;muted&quot;&gt;These quick filters match the tags shown on each row.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Very strong / Strong / Possible&lt;/strong&gt; — confidence tiers based on how many sensors are in the group and how many times it repeated.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;High-Confidence Unknown&lt;/strong&gt; — unknown group has a strong repeat pattern and may be worth mapping.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Poss. Stalker&lt;/strong&gt; — repeated unknown signal seen across multiple days and still recently active.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Weekend Warrior&lt;/strong&gt; — unknown signal appears mostly on weekends.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Commuter&lt;/strong&gt; — unknown signal appears mostly on weekdays.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Signal Lurker&lt;/strong&gt; — mid-strength or weak unknown that has repeated but not enough to call regular.&lt;/p&gt;"
        >Signal filters explained</button>
        </div>
      </div>
      <table id="newUnknownTable">
        <thead>
          <tr>
            <th>Confidence</th>
            <th>Signals</th>
            <th>Pass Count</th>
            <th>Sensor Count</th>
            <th>First Seen</th>
            <th>Last Seen</th>
            <th>Sensor IDs</th>
            <th>Copy/Paste JSON</th>
            <th>Actions</th>
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

        menu_items = [
            {"label": "Add Watch", "payload": watch_payload, "handler": "rowMenuEdit"},
            {"label": "Ignore", "payload": ignore_payload, "handler": "rowMenuEdit"},
        ]

        all_labels = []
        if sensor_model_map is not None or sensor_protocol_map is not None:
            raw_mixed = compute_mixed_sensor_label(sensor_ids, sensor_model_map or {}, sensor_protocol_map or {})
            if raw_mixed:
                all_labels.append({**raw_mixed, "class": pattern_label_class(raw_mixed["text"])})
        if sensor_by_id is not None:
            all_labels.extend(compute_signal_tags(row, sensor_by_id))
        signals_html = pattern_pills(all_labels) if all_labels else '<span class="muted">—</span>'

        html += f"""
          <tr>
            <td>{pill(row["confidence"], "info", CONFIDENCE_DESCRIPTIONS.get(row["confidence"]))}</td>
            <td>{signals_html}</td>
            <td>{row["pass_count"]}</td>
            <td>{row["sensor_count"]}</td>
            <td>{display_time(row["first_seen"])}</td>
            <td>{display_time(row["last_seen"])}</td>
            <td>{safe_text(", ".join(sensor_ids))}</td>
            <td><div class="copybox">{safe_text(json.dumps(snippet, indent=2))}</div></td>
            <td class="actions-cell">{row_actions_menu(menu_items, label="Candidate actions")}</td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def overlap_candidates_section(rows, sensor_model_map=None, sensor_protocol_map=None, sensor_by_id=None):
    html = f"""
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Best Guess Vehicle Candidates</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Suggested vehicle groups built from sensors repeatedly heard together. Use Details to check the evidence before naming or ignoring a group. <button type="button" class="inline-info-button"
          onclick="openInfoModal(this)"
          data-info-title="How confidence is estimated"
          data-info-body="&lt;p class=&quot;muted&quot;&gt;Confidence is based on how many sensors are in the group and how many times that group was seen. More sensors and more repeat sightings usually means a better guess.&lt;/p&gt;&lt;div class=&quot;matching-summary&quot;&gt;&lt;div class=&quot;matching-summary-title&quot;&gt;Confidence tiers&lt;/div&gt;&lt;div class=&quot;matching-summary-grid&quot;&gt;&lt;div class=&quot;matching-summary-item&quot;&gt;&lt;span class=&quot;matching-summary-value&quot;&gt;2+ sensors&lt;/span&gt;&lt;span class=&quot;matching-summary-label&quot;&gt;Repeated across 2+ passes — Possible&lt;/span&gt;&lt;/div&gt;&lt;div class=&quot;matching-summary-item&quot;&gt;&lt;span class=&quot;matching-summary-value&quot;&gt;3+ sensors&lt;/span&gt;&lt;span class=&quot;matching-summary-label&quot;&gt;Repeated across 2+ passes — Strong&lt;/span&gt;&lt;/div&gt;&lt;div class=&quot;matching-summary-item&quot;&gt;&lt;span class=&quot;matching-summary-value&quot;&gt;{STRONG_SENSOR_COUNT}+ sensors&lt;/span&gt;&lt;span class=&quot;matching-summary-label&quot;&gt;{VERY_STRONG_PASS_COUNT}+ repeated passes — Very strong&lt;/span&gt;&lt;/div&gt;&lt;div class=&quot;matching-summary-item&quot;&gt;&lt;span class=&quot;matching-summary-value&quot;&gt;{MAX_CANDIDATE_SENSOR_COUNT} sensors&lt;/span&gt;&lt;span class=&quot;matching-summary-label&quot;&gt;Larger clusters are ignored&lt;/span&gt;&lt;/div&gt;&lt;/div&gt;&lt;/div&gt;"
        >How this works</button></p>
      <div class="toolbar">
        <input id="overlapCandidateSearchInput" placeholder="Search names, IDs, confidence..." oninput="filterTable('overlapCandidateTable', this.value)">
        <div class="candidate-filter-buttons">
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('overlapCandidateTable', 'overlapCandidateSearchInput', 'Very strong', 'confidence')">Very strong</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('overlapCandidateTable', 'overlapCandidateSearchInput', 'Strong', 'confidence')">Strong</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('overlapCandidateTable', 'overlapCandidateSearchInput', 'Possible', 'confidence')">Possible</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('overlapCandidateTable', 'overlapCandidateSearchInput', 'High-Confidence Unknown', '')">High-Confidence Unknown</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('overlapCandidateTable', 'overlapCandidateSearchInput', 'Poss. Stalker', '')">Poss. Stalker</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('overlapCandidateTable', 'overlapCandidateSearchInput', 'Weekend Warrior', '')">Weekend Warrior</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('overlapCandidateTable', 'overlapCandidateSearchInput', 'Commuter', '')">Commuter</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('overlapCandidateTable', 'overlapCandidateSearchInput', 'Signal Lurker', '')">Signal Lurker</button>
        <button type="button" class="inline-info-button"
          onclick="openInfoModal(this)"
          data-info-title="About the signal filters"
          data-info-body="&lt;p class=&quot;muted&quot;&gt;These quick filters match the tags shown on each row.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Very strong / Strong / Possible&lt;/strong&gt; — confidence tiers based on how many sensors are in the group and how many times it repeated.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;High-Confidence Unknown&lt;/strong&gt; — unknown group has a strong repeat pattern and may be worth mapping.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Poss. Stalker&lt;/strong&gt; — repeated unknown signal seen across multiple days and still recently active.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Weekend Warrior&lt;/strong&gt; — unknown signal appears mostly on weekends.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Commuter&lt;/strong&gt; — unknown signal appears mostly on weekdays.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Signal Lurker&lt;/strong&gt; — mid-strength or weak unknown that has repeated but not enough to call regular.&lt;/p&gt;"
        >Signal filters explained</button>
        </div>
      </div>
      <table id="overlapCandidateTable">
        <thead>
          <tr>
            <th>Saved Match</th>
            <th>Confidence</th>
            <th>Signals</th>
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

        raw_labels = compute_pattern_labels(row, now_dt)
        pattern_labels = [
            {"text": lbl["text"], "caveat": lbl["caveat"], "class": pattern_label_class(lbl["text"])}
            for lbl in raw_labels
        ]
        if sensor_model_map is not None or sensor_protocol_map is not None:
            mixed_label = compute_mixed_sensor_label(
                sensor_ids,
                sensor_model_map or {},
                sensor_protocol_map or {},
            )
            if mixed_label:
                mixed_label["class"] = pattern_label_class(mixed_label["text"])
                pattern_labels.append(mixed_label)
        if sensor_by_id is not None:
            pattern_labels.extend(compute_signal_tags(row, sensor_by_id))
        pattern_pills_html = pattern_pills(pattern_labels)

        details_payload = {
            "title": known_vehicle or f"Candidate {index}",
            "confidence": row["confidence"],
            "category": category,
            "known_vehicle": known_vehicle,
            "match_text": known_match_text(row["known_match"]),
            "sensor_count": row["sensor_count"],
            "pass_count": row["pass_count"],
            "first_seen": display_time(row["first_seen"]),
            "last_seen": display_time(row["last_seen"]),
            "sensor_ids": sensor_ids,
            "pattern_labels": pattern_labels,
        }
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
            menu_items = []
            if category != "known":
                menu_items.append({"label": "Move to Known", "payload": known_payload, "handler": "rowMenuSubmitAction"})
            if category != "watch":
                menu_items.append({"label": "Move to Watch", "payload": watch_payload, "handler": "rowMenuSubmitAction"})
            if category != "ignore":
                menu_items.append({"label": "Ignore", "payload": ignore_payload, "handler": "rowMenuSubmitAction"})
            menu_items.append({"label": "Details", "payload": details_payload, "handler": "openCandidateDrawer", "data_attr": "candidate"})
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
            menu_items = [
                {"label": "Add Watch", "payload": watch_payload, "handler": "rowMenuEdit"},
                {"label": "Ignore", "payload": ignore_payload, "handler": "rowMenuEdit"},
                {"label": "Details", "payload": details_payload, "handler": "openCandidateDrawer", "data_attr": "candidate"},
            ]

        overlap_signals_html = pattern_pills_html if pattern_pills_html else '<span class="muted">—</span>'

        html += f"""
          <tr>
            <td>{saved_match_html(row["known_vehicle"], row["category"], row["known_match"])}</td>
            <td title="{row['sensor_count']} sensors · {row['pass_count']} passes">{pill(row["confidence"], "confidence", CONFIDENCE_DESCRIPTIONS.get(row["confidence"]))}</td>
            <td>{overlap_signals_html}</td>
            <td>{row["pass_count"]}</td>
            <td>{row["sensor_count"]}</td>
            <td>{display_time(row["first_seen"])}</td>
            <td>{display_time(row["last_seen"])}</td>
            <td>{safe_text(", ".join(row["sensor_ids"]))}</td>
            <td class="actions-cell">{row_actions_menu(menu_items, label="Candidate actions")}</td>
          </tr>
"""

    html += """
        </tbody>
      </table>
    </details>
"""
    return html


def exact_candidates_section(rows, sensor_model_map=None, sensor_protocol_map=None, sensor_by_id=None):
    html = f"""
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Exact Repeat Sensor Groups</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">A stricter view — only groups where the exact same sensor IDs appeared together repeatedly. It can miss partial passes, so cross-check with Best Guess too. <button type="button" class="inline-info-button"
          onclick="openInfoModal(this)"
          data-info-title="About Exact Repeat Sensor Groups"
          data-info-body="&lt;p class=&quot;muted&quot;&gt;Exact Repeat only counts passes where the identical set of sensor IDs was seen together every time.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;A vehicle that occasionally misses a tire signal may not appear here consistently, even if it shows up in Best Guess.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;If a group appears in both Exact Repeat and Best Guess, the evidence is stronger — treat it as a higher-confidence candidate.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;For partial passes or slightly inconsistent sensor sets, Best Guess is usually the better place to look.&lt;/p&gt;"
        >How this works</button></p>
      <div class="toolbar">
        <input id="exactCandidateSearchInput" placeholder="Search exact candidates..." oninput="filterTable('exactCandidateTable', this.value)">
        <div class="candidate-filter-buttons">
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('exactCandidateTable', 'exactCandidateSearchInput', 'Very strong', 'info')">Very strong</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('exactCandidateTable', 'exactCandidateSearchInput', 'Strong', 'info')">Strong</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('exactCandidateTable', 'exactCandidateSearchInput', 'Possible', 'info')">Possible</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('exactCandidateTable', 'exactCandidateSearchInput', 'High-Confidence Unknown', '')">High-Confidence Unknown</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('exactCandidateTable', 'exactCandidateSearchInput', 'Poss. Stalker', '')">Poss. Stalker</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('exactCandidateTable', 'exactCandidateSearchInput', 'Weekend Warrior', '')">Weekend Warrior</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('exactCandidateTable', 'exactCandidateSearchInput', 'Commuter', '')">Commuter</button>
        <button type="button" class="filter-btn" onclick="quickFilterExactPillTable('exactCandidateTable', 'exactCandidateSearchInput', 'Signal Lurker', '')">Signal Lurker</button>
        <button type="button" class="inline-info-button"
          onclick="openInfoModal(this)"
          data-info-title="About the signal filters"
          data-info-body="&lt;p class=&quot;muted&quot;&gt;These quick filters match the tags shown on each row.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Very strong / Strong / Possible&lt;/strong&gt; — confidence tiers based on how many sensors are in the group and how many times it repeated.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;High-Confidence Unknown&lt;/strong&gt; — unknown group has a strong repeat pattern and may be worth mapping.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Poss. Stalker&lt;/strong&gt; — repeated unknown signal seen across multiple days and still recently active.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Weekend Warrior&lt;/strong&gt; — unknown signal appears mostly on weekends.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Commuter&lt;/strong&gt; — unknown signal appears mostly on weekdays.&lt;/p&gt;&lt;p class=&quot;muted&quot;&gt;&lt;strong&gt;Signal Lurker&lt;/strong&gt; — mid-strength or weak unknown that has repeated but not enough to call regular.&lt;/p&gt;"
        >Signal filters explained</button>
        </div>
      </div>
      <table id="exactCandidateTable">
        <thead>
          <tr>
            <th>Saved Match</th>
            <th>Confidence</th>
            <th>Signals</th>
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
            menu_items = []
            if category != "known":
                menu_items.append({"label": "Move to Known", "payload": known_payload, "handler": "rowMenuSubmitAction"})
            if category != "watch":
                menu_items.append({"label": "Move to Watch", "payload": watch_payload, "handler": "rowMenuSubmitAction"})
            if category != "ignore":
                menu_items.append({"label": "Ignore", "payload": ignore_payload, "handler": "rowMenuSubmitAction"})
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
            menu_items = [
                {"label": "Add Watch", "payload": watch_payload, "handler": "rowMenuEdit"},
                {"label": "Ignore", "payload": ignore_payload, "handler": "rowMenuEdit"},
            ]

        all_labels = []
        if sensor_model_map is not None or sensor_protocol_map is not None:
            raw_mixed = compute_mixed_sensor_label(sensor_ids, sensor_model_map or {}, sensor_protocol_map or {})
            if raw_mixed:
                all_labels.append({**raw_mixed, "class": pattern_label_class(raw_mixed["text"])})
        if sensor_by_id is not None:
            all_labels.extend(compute_signal_tags(row, sensor_by_id))
        exact_signals_html = pattern_pills(all_labels) if all_labels else '<span class="muted">—</span>'

        html += f"""
          <tr>
            <td>{saved_match_html(row["known_vehicle"], row["category"], row["known_match"])}</td>
            <td>{pill(row["confidence"], "info", CONFIDENCE_DESCRIPTIONS.get(row["confidence"]))}</td>
            <td>{exact_signals_html}</td>
            <td>{row["pass_count"]}</td>
            <td>{row["sensor_count"]}</td>
            <td>{display_time(row["first_seen"])}</td>
            <td>{display_time(row["last_seen"])}</td>
            <td>{safe_text(", ".join(row["sensor_ids"]))}</td>
            <td class="actions-cell">{row_actions_menu(menu_items, label="Candidate actions")}</td>
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
        <option value="all">All loaded data</option>
        <option value="24h">Last 24 hours</option>
        <option value="7d" selected>Last 7 days</option>
        <option value="30d">Last 30 days</option>
      </select>
      <span class="muted">Signal charts show the most recent 10,000 TPMS events. Use the time range filter to focus on a specific window.</span>
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
            crowded_indicator = pill(
                "Crowded window",
                "crowded-window",
                f"More than {MAX_CANDIDATE_SENSOR_COUNT} sensors were heard in this pass, so it's too crowded to use for candidate clustering.",
            )

        html += f"""
          <tr>
            <td>{vehicle_status_html(row["known_vehicle"], row["category"])}</td>
            <td>{category_pill(row["category"] or "unknown")}</td>
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
    SQ_CLASS = {
        "Strong": "known",
        "Normal": "info",
        "Weak": "pattern-fluke",
        "Unknown": "unknown",
    }

    html = """
    <details class="section">
      <summary class="section-summary">
        <span class="section-summary-main">
          <span class="section-summary-title">Unique TPMS Sensor IDs</span>
          <span class="section-summary-subtitle">Click to expand or collapse this section</span>
        </span>
        <span class="section-summary-action" aria-hidden="true"></span>
      </summary>
      <p class="muted">Repeated TPMS sensor IDs seen 5 or more times, limited to the 1,000 most recently active rows. One-off and low-repeat signals are hidden here to keep the report responsive.</p>
      <p class="muted">Signal is based on average rtl_433 RSSI/SNR for this receiver. It indicates radio decode quality, not exact distance.</p>
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
            <th>Signal</th>
          </tr>
        </thead>
        <tbody>
"""

    for row in rows:
        pressure = row["avg_pressure_psi"] if row["avg_pressure_psi"] is not None else row["avg_pressure_kpa"]
        sq = row.get("signal_quality", "Unknown")

        html += f"""
          <tr>
            <td>{vehicle_status_html(row["vehicle_name"], row["category"])}</td>
            <td>{category_pill(row["category"] or "unknown")}</td>
            <td>{safe_text(row["sensor_id"])}</td>
            <td>{row["count"]}</td>
            <td>{display_time(row["first_seen"])}</td>
            <td>{display_time(row["last_seen"])}</td>
            <td>{safe_text(row["models"])}</td>
            <td>{safe_text(pressure if pressure is not None else "")}</td>
            <td>{safe_text(row["avg_temperature_c"] if row["avg_temperature_c"] is not None else "")}</td>
            <td>{safe_text(row["avg_rssi"] if row["avg_rssi"] is not None else "")}</td>
            <td>{safe_text(row["avg_snr"] if row["avg_snr"] is not None else "")}</td>
            <td>{pill(sq, SQ_CLASS.get(sq, "unknown"))}</td>
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
                if isinstance(packet.get("rows"), list) and "frames" in packet:
                    continue
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


def html_end(timeline_points):
    return (
        CANDIDATE_DRAWER_HTML
        + "\n  </main>\n\n"
        + '  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>\n'
        + "  <script>\n"
        + f"    const allTimelinePoints = {json.dumps(timeline_points)};\n"
        + JS_BLOCK
        + "  </script>\n</body>\n</html>"
    )


