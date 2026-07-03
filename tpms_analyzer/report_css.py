CSS_BLOCK = """
    :root {
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
      --accent: #2563eb;
      --accent-strong: #1d4ed8;
      --accent-soft: #eff6ff;
      --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06);
      --shadow-md: 0 10px 30px rgba(15, 23, 42, 0.08);
      --radius-lg: 18px;
    }

    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      color: var(--text);
      background: var(--bg);
    }

    header {
      padding: 14px 24px;
      background: linear-gradient(to bottom, #ffffff, #f5f8ff);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 10;
      box-shadow: var(--shadow-sm);
    }

    h1 {
      margin: 0 0 4px;
      font-size: 28px;
    }

    h2 {
      margin-top: 0;
    }

    main {
      padding: 24px;
      max-width: 1750px;
      margin: 0 auto;
    }

    .muted {
      color: var(--muted);
    }

    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 16px;
      margin: 20px 0;
    }

    .card {
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      background: var(--card);
      box-shadow: 0 1px 2px rgba(0,0,0,.04);
    }

    .big {
      font-size: 32px;
      font-weight: 800;
      line-height: 1.1;
    }

    .section {
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--card);
      padding: 18px;
      margin: 20px 0;
      overflow: hidden;
    }

    details.section > summary.section-summary {
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
    }

    details.section:not([open]) > summary.section-summary {
      margin-bottom: -18px;
      border-bottom: 0;
    }

    details.section > summary.section-summary::-webkit-details-marker {
      display: none;
    }

    details.section > summary.section-summary::marker {
      content: "";
    }

    details.section > summary.section-summary:hover {
      background: #eef4ff;
    }

    details.section > summary.section-summary:focus-visible {
      outline: 3px solid rgba(37, 99, 235, 0.35);
      outline-offset: 3px;
    }

    .section-summary-main {
      min-width: 0;
    }

    .section-summary-title {
      display: block;
      color: var(--text);
      font-size: 1.2rem;
      font-weight: 800;
      line-height: 1.2;
    }

    .section-summary-subtitle {
      display: block;
      color: var(--muted);
      font-size: 0.85rem;
      font-weight: 600;
      margin-top: 4px;
    }

    .section-summary-action {
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
    }

    details.section:not([open]) .section-summary-action::before {
      content: "Expand ▾";
    }

    details.section[open] .section-summary-action::before {
      content: "Collapse ▴";
    }

    .chart {
      height: 560px;
      margin: 12px 0 24px;
    }

    .small-chart {
      height: 360px;
      margin: 12px 0 24px;
    }

    /*
      Presence Timeline: a small, subtle 24-bucket hourly strip, not a
      full chart. .presence-timeline-track/.presence-timeline-bar-wrap/
      .presence-timeline-legend-swatch/.presence-timeline-segment-known/
      .presence-timeline-segment-lingering/.presence-timeline-segment-pass-by
      are included alongside the classes report.py currently emits
      (.presence-timeline, .presence-timeline-bucket,
      .presence-timeline-segment + known/lingering/pass-by modifiers) so
      this stays in sync if the markup is ever adjusted.
    */
    .presence-timeline,
    .presence-timeline-track {
      display: flex;
      align-items: flex-end;
      gap: 3px;
      margin: 14px 0 6px;
      padding: 4px 2px 0;
      overflow-x: auto;
    }

    .presence-timeline-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      font-size: 12px;
      color: var(--muted);
      margin: 12px 0 4px;
    }

    .presence-timeline-legend-item {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .presence-timeline-legend-item::before {
      content: "";
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 2px;
      background: var(--muted);
      flex-shrink: 0;
    }

    .presence-timeline-legend-swatch {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 2px;
      background: var(--muted);
      flex-shrink: 0;
    }

    .presence-timeline-legend-item.presence-timeline-known::before,
    .presence-timeline-legend-item.presence-timeline-known .presence-timeline-legend-swatch {
      background: var(--known-text);
    }

    .presence-timeline-legend-item.presence-timeline-lingering::before,
    .presence-timeline-legend-item.presence-timeline-lingering .presence-timeline-legend-swatch {
      background: var(--unknown-text);
    }

    .presence-timeline-legend-item.presence-timeline-pass-by::before,
    .presence-timeline-legend-item.presence-timeline-pass-by .presence-timeline-legend-swatch {
      background: var(--muted);
    }

    .presence-timeline-bucket,
    .presence-timeline-bar-wrap {
      display: grid;
      grid-template-rows: 96px auto;
      row-gap: 4px;
      flex: 1 1 0;
      min-width: 6px;
      text-align: center;
    }

    .presence-timeline-bar {
      /*
        report.py sets an inline height percentage on this element
        (count/max_total, meant to read against the full 96px track).
        min-height: 100% keeps that reference frame correct: the inner
        segments are already each sized as their own share of the
        busiest hour, so letting them stack from the bottom of a
        full-height box reproduces the "shorter bar for quieter hours"
        effect without the percentages compounding against an
        already-shrunk box.
      */
      min-height: 100%;
      width: 100%;
      display: flex;
      flex-direction: column-reverse;
      align-items: stretch;
      border: 1px solid var(--border);
      border-radius: 4px;
      background: var(--soft);
      overflow: hidden;
    }

    .presence-timeline-segment,
    .presence-timeline-segment-known,
    .presence-timeline-segment-lingering,
    .presence-timeline-segment-pass-by {
      width: 100%;
      flex-shrink: 0;
    }

    .presence-timeline-segment.presence-timeline-known,
    .presence-timeline-segment-known {
      background: var(--known-text);
    }

    .presence-timeline-segment.presence-timeline-lingering,
    .presence-timeline-segment-lingering {
      background: var(--unknown-text);
    }

    .presence-timeline-segment.presence-timeline-pass-by,
    .presence-timeline-segment-pass-by {
      background: var(--muted);
    }

    .presence-timeline-hour-label {
      font-size: 10px;
      color: var(--muted);
      white-space: nowrap;
    }

    @media (max-width: 640px) {
      .presence-timeline,
      .presence-timeline-track {
        gap: 2px;
      }

      .presence-timeline-bucket,
      .presence-timeline-bar-wrap {
        grid-template-rows: 64px auto;
        min-width: 4px;
      }

      .presence-timeline-hour-label {
        font-size: 9px;
      }
    }

    .toolbar {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      margin: 12px 0;
    }

    .candidate-filter-buttons {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      width: 100%;
    }

    .inline-info-button {
      background: none;
      border: none;
      border-bottom: 1px dotted var(--info-text);
      padding: 0;
      color: var(--info-text);
      font-size: inherit;
      font-family: inherit;
      text-decoration: none;
      cursor: pointer;
    }

    .inline-info-button:hover {
      color: var(--text);
      border-bottom-color: var(--text);
      border-bottom-style: solid;
    }

    .inline-info-button:focus-visible {
      outline: 2px solid var(--info-text);
      outline-offset: 2px;
      border-radius: 2px;
    }

    .filter-btn {
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: var(--card);
      color: var(--text);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      box-shadow: var(--shadow-sm);
    }

    .filter-btn:hover,
    .filter-btn:focus-visible {
      border-color: var(--muted);
      background: #f3f4f6;
      outline: none;
    }

    .chart-toolbar {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      margin: 0 0 20px;
      padding: 12px 14px;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--card);
    }

    .chart-toolbar label {
      font-weight: 800;
    }

    .chart-toolbar select {
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 14px;
      min-width: 220px;
      background: #ffffff;
      color: var(--text);
    }

    .chart-loading {
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
    }

    .chart-option-row {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
      margin: 6px 0 14px;
    }

    .pressure-option-row {
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--soft);
    }

    .chart-toggle-control {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      flex: 0 0 auto;
      color: var(--text);
      font-weight: 800;
      cursor: pointer;
      user-select: none;
    }

    .chart-toggle-control input {
      position: absolute;
      opacity: 0;
      pointer-events: none;
    }

    .chart-toggle-slider {
      position: relative;
      width: 38px;
      height: 22px;
      border-radius: 999px;
      background: #cbd5e1;
      box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.12);
      transition: background 0.15s ease;
    }

    .chart-toggle-slider::after {
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
    }

    .chart-toggle-control input:checked + .chart-toggle-slider {
      background: var(--accent);
    }

    .chart-toggle-control input:checked + .chart-toggle-slider::after {
      transform: translateX(16px);
    }

    .chart-toggle-control input:focus-visible + .chart-toggle-slider {
      outline: 3px solid rgba(37, 99, 235, 0.25);
      outline-offset: 2px;
    }

    .chart-toggle-label {
      white-space: nowrap;
    }

    .chart-inline-note {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }

    @media (max-width: 700px) {
      .pressure-option-row {
        align-items: flex-start;
      }

      .chart-toggle-label {
        white-space: normal;
      }
    }

    .chart-loading.active {
      display: inline-flex;
    }

    .chart-loading::before {
      content: "";
      width: 14px;
      height: 14px;
      border: 2px solid rgba(91, 33, 182, 0.25);
      border-top-color: var(--info-text);
      border-radius: 999px;
      animation: chart-loading-spin 0.8s linear infinite;
    }

    @keyframes chart-loading-spin {
      to {
        transform: rotate(360deg);
      }
    }

    input {
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 14px;
      min-width: 280px;
    }

    table {
      border-collapse: collapse;
      width: 100%;
      margin-top: 12px;
      margin-bottom: 12px;
    }

    th, td {
      border-bottom: 1px solid var(--border);
      padding: 8px 10px;
      font-size: 13px;
      vertical-align: top;
    }

    th {
      background: var(--soft);
      text-align: left;
      position: sticky;
      top: 89px;
      z-index: 5;
      cursor: pointer;
      white-space: nowrap;
    }

    tr:hover td {
      background: #fafafa;
    }

    code {
      background: #eee;
      padding: 2px 4px;
      border-radius: 4px;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      white-space: nowrap;
      font-weight: 700;
      margin: 2px 3px 2px 0;
    }

    .known {
      background: var(--known-bg);
      color: var(--known-text);
    }

    .watch {
      background: var(--watch-bg);
      color: var(--watch-text);
    }

    .ignore {
      background: var(--ignore-bg);
      color: var(--ignore-text);
    }

    .unknown {
      background: var(--unknown-bg);
      color: var(--unknown-text);
    }

    .info {
      background: var(--info-bg);
      color: var(--info-text);
    }

    .confidence {
      background: #e0f2fe;
      color: #075985;
    }

    .pattern-regular {
      background: #d1fae5;
      color: #065f46;
    }

    .pattern-recent {
      background: #dbeafe;
      color: #1e40af;
    }

    .pattern-fluke {
      background: #fef3c7;
      color: #92400e;
    }

    .pattern-quiet {
      background: #e5e7eb;
      color: #374151;
    }

    .pattern-occasional {
      background: #ede9fe;
      color: #5b21b6;
    }

    .pattern-default {
      background: var(--info-bg);
      color: var(--info-text);
    }

    .pattern-mixed {
      background: #ffedd5;
      color: #c2410c;
    }

    .pattern-stalker {
      background: #fee2e2;
      color: #991b1b;
    }

    .pattern-weekend {
      background: #fae8ff;
      color: #7e22ce;
    }

    .pattern-commuter {
      background: #e0f2fe;
      color: #0369a1;
    }

    .pill.crowded-window {
      background: #fde68a;
      color: #78350f;
    }

    .note {
      background: #fff7ed;
      border: 1px solid #fed7aa;
      border-radius: 12px;
      padding: 12px 14px;
      margin: 12px 0;
    }

    .matching-summary {
      margin-top: 8px;
    }

    .matching-summary-title {
      font-weight: 600;
      margin-bottom: 8px;
    }

    .matching-summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
    }

    .matching-summary-item {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px 10px;
      text-align: center;
    }

    .matching-summary-value {
      display: block;
      font-size: 20px;
      font-weight: 700;
      line-height: 1.2;
    }

    .matching-summary-label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-top: 2px;
    }

    .copybox {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      white-space: pre-wrap;
      background: #111827;
      color: #f9fafb;
      padding: 10px;
      border-radius: 10px;
      font-size: 12px;
      max-width: 800px;
      overflow-x: auto;
    }

    .header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }

    .refresh-button {
      border: 1px solid var(--accent-strong);
      border-radius: 10px;
      padding: 10px 18px;
      background: var(--accent);
      color: #ffffff;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.01em;
      cursor: pointer;
      white-space: nowrap;
      box-shadow: var(--shadow-sm);
      transition: background 0.15s ease, box-shadow 0.15s ease;
    }

    .refresh-button:hover {
      background: var(--accent-strong);
      box-shadow: 0 2px 8px rgba(37, 99, 235, 0.28);
    }

    .refresh-button:disabled {
      opacity: 0.6;
      cursor: wait;
    }

    .tabs {
      display: flex;
      gap: 4px;
      align-items: center;
      flex-wrap: wrap;
      margin: 16px 0 20px;
      padding: 6px;
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      background: var(--soft);
      box-shadow: var(--shadow-sm);
    }

    .tab-button {
      border: 1px solid transparent;
      border-radius: 12px;
      padding: 9px 16px;
      background: transparent;
      color: var(--muted);
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      transition: background 0.12s ease, color 0.12s ease, border-color 0.12s ease;
    }

    .tab-button:hover {
      background: #ffffff;
      color: var(--text);
      border-color: var(--border);
    }

    .tab-button.active {
      border-color: var(--accent);
      background: #ffffff;
      color: var(--accent);
      font-weight: 800;
      box-shadow: var(--shadow-sm);
    }

    .tab-panel {
      display: none;
    }

    .tab-panel.active {
      display: block;
    }

    .action-buttons {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }

    .small-action-button {
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 6px 10px;
      background: var(--soft);
      color: var(--text);
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
      white-space: nowrap;
    }

    .small-action-button:hover {
      filter: brightness(0.97);
    }

    .small-action-button:disabled {
      opacity: 0.6;
      cursor: wait;
    }

    .known-action {
      background: var(--known-bg);
      color: var(--known-text);
    }

    .watch-action {
      background: var(--watch-bg);
      color: var(--watch-text);
    }

    .ignore-action {
      background: var(--ignore-bg);
      color: var(--ignore-text);
    }

    .candidate-drawer {
      position: fixed;
      inset: 0;
      z-index: 20;
      display: none;
      align-items: flex-start;
      justify-content: flex-end;
    }

    .candidate-drawer.open {
      display: flex;
    }

    .candidate-drawer-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.35);
    }

    .candidate-drawer-panel {
      position: relative;
      width: 420px;
      max-width: 92vw;
      height: 100vh;
      overflow-y: auto;
      background: var(--card);
      border-left: 1px solid var(--border);
      padding: 22px;
      box-shadow: -4px 0 16px rgba(0, 0, 0, 0.1);
      box-sizing: border-box;
    }

    .candidate-drawer-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 18px;
    }

    .candidate-drawer-close {
      border: 1px solid var(--border);
      border-radius: 999px;
      background: var(--soft);
      color: var(--text);
      font-size: 13px;
      font-weight: 800;
      padding: 4px 10px;
      cursor: pointer;
      flex-shrink: 0;
    }

    .candidate-drawer-close:hover {
      background: var(--border);
    }

    .drawer-pill-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 12px;
    }

    .drawer-summary-section,
    #candidateDrawerBody > .drawer-pill-row {
      margin-bottom: 14px;
    }

    .drawer-summary-section > .drawer-stat-grid,
    #candidateDrawerBody > .drawer-stat-grid {
      margin-bottom: 4px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }

    .report-loading-overlay {
      position: fixed;
      inset: 0;
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(246, 247, 249, 0.92);
      transition: opacity 0.25s ease;
    }

    .report-loading-overlay.hidden {
      opacity: 0;
      pointer-events: none;
    }

    .report-loading-card {
      display: flex;
      align-items: center;
      gap: 16px;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px 28px;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
    }

    .report-loading-spinner {
      width: 28px;
      height: 28px;
      border: 3px solid var(--border);
      border-top-color: var(--info-text);
      border-radius: 999px;
      flex-shrink: 0;
      animation: report-loading-spin 0.75s linear infinite;
    }

    @keyframes report-loading-spin {
      to { transform: rotate(360deg); }
    }

    .report-loading-title {
      font-size: 15px;
      font-weight: 800;
      color: var(--text);
    }

    .report-loading-subtitle {
      font-size: 13px;
      color: var(--muted);
      margin-top: 2px;
    }

    .drawer-vehicle-name {
      font-weight: 600;
    }

    .drawer-stat-grid {
      margin-bottom: 10px;
    }

    .drawer-block {
      margin-top: 12px;
      margin-bottom: 12px;
    }

    .drawer-block.drawer-why-section,
    .drawer-block.drawer-evidence-section {
      margin-top: 16px;
      margin-bottom: 16px;
      padding-top: 4px;
    }

    .drawer-pill-list {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 6px;
    }

    .drawer-note-hint {
      margin-top: 8px;
      font-style: italic;
    }

    .drawer-section-heading {
      font-weight: 700;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text);
      margin-bottom: 10px;
    }

    .drawer-hint-row {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      background: var(--soft);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px 10px;
      margin-bottom: 6px;
    }

    .drawer-hint-row:last-of-type {
      margin-bottom: 0;
    }

    .drawer-hint-row .pill {
      flex-shrink: 0;
      margin: 0;
    }

    .drawer-hint-caveat {
      font-size: 12px;
      line-height: 1.4;
      color: var(--muted);
    }

    .drawer-evidence-section .chart-inline-note {
      margin-bottom: 6px;
    }

    .drawer-evidence-section .chart-inline-note:last-child {
      margin-bottom: 0;
    }

    .drawer-technical-details {
      margin-top: 16px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--soft);
      overflow: hidden;
    }

    .drawer-technical-details > summary {
      list-style: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 10px 12px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }

    .drawer-technical-details > summary::-webkit-details-marker {
      display: none;
    }

    .drawer-technical-details > summary::marker {
      content: "";
    }

    .drawer-technical-details > summary::before {
      content: "▸";
      font-size: 10px;
      transition: transform 0.15s ease;
    }

    .drawer-technical-details[open] > summary::before {
      transform: rotate(90deg);
    }

    .drawer-technical-details > summary:hover {
      background: var(--border);
    }

    .drawer-technical-details > summary:focus-visible {
      outline: 3px solid rgba(37, 99, 235, 0.35);
      outline-offset: -2px;
    }

    .drawer-technical-body {
      padding: 4px 12px 12px;
      border-top: 1px solid var(--border);
    }

    .drawer-technical-body .chart-inline-note {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .drawer-technical-body .chart-inline-note:last-child {
      margin-bottom: 0;
    }

    .matching-summary-value--sm {
      font-size: 14px;
    }

    .chart-inline-note--spaced {
      margin-top: 8px;
    }

    .back-to-top-button {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 15;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 10px 16px;
      background: var(--card);
      color: var(--text);
      font-size: 13px;
      font-weight: 800;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.10);
      opacity: 0;
      pointer-events: none;
      transform: translateY(8px);
      transition: opacity 0.2s ease, transform 0.2s ease;
    }

    .back-to-top-button.visible {
      opacity: 1;
      pointer-events: auto;
      transform: translateY(0);
    }

    .back-to-top-button:hover {
      background: var(--soft);
      border-color: var(--muted);
    }

    .back-to-top-button:focus-visible {
      outline: 3px solid rgba(37, 99, 235, 0.35);
      outline-offset: 3px;
    }

    .vehicle-edit-modal {
      position: fixed;
      inset: 0;
      z-index: 30;
      display: none;
      align-items: center;
      justify-content: center;
    }

    .vehicle-edit-modal.open {
      display: flex;
    }

    .vehicle-edit-modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.45);
    }

    .vehicle-edit-modal-panel {
      position: relative;
      width: 460px;
      max-width: 94vw;
      max-height: 90vh;
      overflow-y: auto;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.14);
      box-sizing: border-box;
    }

    .vehicle-edit-modal-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 20px;
    }

    .vehicle-edit-field {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 16px;
    }

    .vehicle-edit-input,
    .vehicle-edit-textarea {
      width: 100%;
      box-sizing: border-box;
      background: var(--soft);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 14px;
      color: var(--text);
      font-family: inherit;
      resize: vertical;
    }

    .vehicle-edit-input:focus,
    .vehicle-edit-textarea:focus {
      outline: 3px solid rgba(37, 99, 235, 0.30);
      outline-offset: 1px;
      border-color: var(--info-text);
    }

    .vehicle-edit-counter {
      font-size: 12px;
      color: var(--muted);
      text-align: right;
    }

    .vehicle-edit-counter.invalid {
      color: var(--ignore-text);
      font-weight: 600;
    }

    .vehicle-edit-error {
      font-size: 13px;
      color: var(--ignore-text);
      background: var(--ignore-bg);
      border: 1px solid var(--ignore-text);
      border-radius: 8px;
      padding: 8px 12px;
      margin-bottom: 16px;
    }

    .vehicle-edit-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 4px;
    }

    .info-modal {
      position: fixed;
      inset: 0;
      z-index: 30;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(15, 23, 42, 0.40);
    }

    .info-modal[aria-hidden="true"] {
      display: none;
    }

    .info-modal-panel {
      position: relative;
      width: 520px;
      max-width: 94vw;
      max-height: 90vh;
      overflow-y: auto;
      background: var(--card);
      border: 1px solid var(--border);
      border-top: 4px solid var(--accent);
      border-radius: 18px;
      padding: 26px 28px;
      box-shadow: 0 20px 50px rgba(15, 23, 42, 0.18);
      box-sizing: border-box;
    }

    .info-modal .vehicle-edit-modal-header {
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }

    .info-modal-panel h2 {
      margin: 0;
      font-size: 20px;
      color: var(--text);
    }

    .info-modal-close {
      width: 34px;
      height: 34px;
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: var(--soft);
      color: var(--text);
      font-size: 20px;
      line-height: 1;
      padding: 0;
      cursor: pointer;
    }

    .info-modal-close:hover {
      background: var(--border);
    }

    .info-modal-close:focus-visible {
      outline: 3px solid rgba(37, 99, 235, 0.35);
      outline-offset: 2px;
    }

    .info-modal-body {
      overflow-y: auto;
      line-height: 1.6;
      color: var(--text);
    }

    .info-modal-body p {
      margin: 0 0 12px;
    }

    .info-modal-body p:last-child {
      margin-bottom: 0;
    }

    .info-modal-body strong {
      color: var(--text);
      font-weight: 700;
    }

    .info-modal-body .muted {
      color: #4b5563;
    }

    .actions-cell {
      text-align: right;
      white-space: nowrap;
      width: 1%;
    }

    .row-actions {
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .row-actions-toggle {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      min-width: unset;
      padding: 0;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: var(--card);
      color: var(--text);
      font-size: 18px;
      line-height: 1;
      letter-spacing: normal;
      cursor: pointer;
    }

    .row-actions-toggle:hover {
      background: var(--soft);
      border-color: var(--muted);
    }

    .row-actions-toggle:focus-visible {
      outline: 3px solid rgba(37, 99, 235, 0.30);
      outline-offset: 2px;
    }

    .row-actions-toggle[aria-expanded="true"] {
      background: var(--soft);
      border-color: var(--muted);
    }

    .row-actions-menu {
      position: fixed;
      z-index: 40;
      min-width: 140px;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
      padding: 4px 0;
      margin: 0;
    }

    .row-actions-menu-item {
      display: block;
      width: 100%;
      padding: 8px 14px;
      background: none;
      border: none;
      border-radius: 0;
      font-size: 13px;
      font-weight: 700;
      color: var(--text);
      text-align: left;
      cursor: pointer;
      white-space: nowrap;
    }

    .row-actions-menu-item:hover,
    .row-actions-menu-item:focus-visible {
      background: var(--soft);
      outline: none;
    }

    .row-actions-menu-item:focus-visible {
      outline: 3px solid rgba(37, 99, 235, 0.30);
      outline-offset: -2px;
    }

    .row-actions-menu-item--danger {
      color: #b91c1c;
    }

    .row-actions-menu-item--danger:hover,
    .row-actions-menu-item--danger:focus-visible {
      background: #fef2f2;
    }
"""
