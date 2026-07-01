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
    }

    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      color: var(--text);
      background: var(--bg);
    }

    header {
      padding: 24px;
      background: var(--card);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 10;
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

    .toolbar {
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      margin: 12px 0;
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
      gap: 16px;
    }

    .refresh-button {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 14px;
      background: var(--soft);
      color: var(--text);
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }

    .refresh-button:hover {
      filter: brightness(0.97);
    }

    .refresh-button:disabled {
      opacity: 0.6;
      cursor: wait;
    }

    .tabs {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      margin: 16px 0 20px;
      padding: 8px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--card);
    }

    .tab-button {
      border: 1px solid transparent;
      border-radius: 10px;
      padding: 10px 14px;
      background: transparent;
      color: var(--muted);
      font-weight: 800;
      cursor: pointer;
      white-space: nowrap;
    }

    .tab-button:hover {
      background: var(--soft);
      color: var(--text);
    }

    .tab-button.active {
      border-color: var(--border);
      background: var(--soft);
      color: var(--text);
      box-shadow: 0 1px 2px rgba(0,0,0,.04);
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
      width: 380px;
      max-width: 92vw;
      height: 100vh;
      overflow-y: auto;
      background: var(--card);
      border-left: 1px solid var(--border);
      padding: 20px;
      box-shadow: -4px 0 16px rgba(0, 0, 0, 0.1);
      box-sizing: border-box;
    }

    .candidate-drawer-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
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

    .drawer-pill-list {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 6px;
    }

    .drawer-note-hint {
      margin-top: 4px;
      font-style: italic;
    }

    .drawer-section-heading {
      font-weight: 700;
      margin-bottom: 6px;
    }

    .matching-summary-value--sm {
      font-size: 14px;
    }

    .chart-inline-note--spaced {
      margin-top: 8px;
    }
"""
