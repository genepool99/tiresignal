JS_BLOCK = """    function getServiceBaseUrl() {
      if (window.location.pathname.startsWith("/local/")) {
        return window.location.protocol + "//" + window.location.hostname + ":8099";
      }

      if (window.location.port === "8099") {
        return "";
      }

      const parts = window.location.pathname.split("/").filter(Boolean);

      if (parts.length >= 3 && parts[0] === "api" && parts[1] === "hassio_ingress") {
        return "/" + parts.slice(0, 3).join("/");
      }

      if (parts.length > 0) {
        return "/" + parts[0];
      }

      return "";
    }

    const refreshWebhookUrl = getServiceBaseUrl() + "/refresh";
    const vehicleMapEditWebhookUrl = getServiceBaseUrl() + "/vehicle-map-edit";
    const PRESSURE_SUSPICIOUS_PSI = 120;
    const MAX_SCATTER_POINTS = 5000;

    async function refreshReport() {
      const button = document.getElementById("refreshButton");
      const originalText = button.innerText;

      try {
        button.disabled = true;
        button.innerText = "Refreshing...";

        const response = await fetch(refreshWebhookUrl, {
          method: "POST"
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        button.innerText = "Refresh requested";

        setTimeout(() => {
          window.location.reload();
        }, 2500);
      } catch (error) {
        console.error(error);
        button.innerText = "Refresh failed";
        setTimeout(() => {
          button.innerText = originalText;
          button.disabled = false;
        }, 4000);
      }
    }

    async function editVehicleMapFromButton(button) {
      const payload = JSON.parse(button.dataset.payload || "{}");

      if (payload.action === "add" || payload.action === "edit") {
        openVehicleEditModal(button, payload);
        return;
      }

      await submitVehicleMapPayload(button, payload);
    }

    function showVehicleActionStatus(message) {
      let el = document.getElementById("vehicleActionStatus");
      if (!el) {
        el = document.createElement("div");
        el.id = "vehicleActionStatus";
        el.setAttribute("role", "status");
        el.setAttribute("aria-live", "polite");
        el.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:9999;" +
          "padding:0.6em 1em;background:#b91c1c;color:#fff;" +
          "font-size:0.95em;text-align:center;";
        document.body.insertBefore(el, document.body.firstChild);
      }
      el.textContent = message;
      el.hidden = false;
      clearTimeout(el._hideTimer);
      el._hideTimer = setTimeout(() => {
        el.hidden = true;
        el.textContent = "";
      }, 6000);
    }

    async function submitVehicleMapPayload(button, payload, options = {}) {
      const originalText = button.innerText;
      const { keepModalOpenOnError = false, modalSaveButton = null } = options;

      try {
        button.disabled = true;
        button.innerText = "Saving...";

        if (modalSaveButton) {
          modalSaveButton.disabled = true;
          modalSaveButton.innerText = "Saving...";
        }

        const response = await fetch(vehicleMapEditWebhookUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errorBody = await response.json().catch(() => null);
          const message = errorBody && errorBody.error ? errorBody.error : `HTTP ${response.status}`;
          throw new Error(message);
        }

        button.innerText = "Saved";

        if (keepModalOpenOnError) {
          closeVehicleEditModal();
        }

        setTimeout(() => {
          window.location.reload();
        }, 2500);
      } catch (error) {
        console.error(error);

        if (keepModalOpenOnError) {
          button.innerText = originalText;
          button.disabled = false;

          if (modalSaveButton) {
            modalSaveButton.disabled = false;
            modalSaveButton.innerText = "Save";
          }

          const errorEl = document.getElementById("vehicleEditError");
          if (errorEl) {
            errorEl.textContent = error.message;
            errorEl.hidden = false;
          }
        } else {
          button.innerText = "Failed";
          showVehicleActionStatus(error.message);

          setTimeout(() => {
            button.innerText = originalText;
            button.disabled = false;
          }, 4000);
        }
      }
    }

    let _vehicleEditPendingButton = null;
    let _vehicleEditPendingPayload = null;

    function openVehicleEditModal(button, payload) {
      const modal = document.getElementById("vehicleEditModal");
      const titleEl = document.getElementById("vehicleEditModalTitle");
      const nameInput = document.getElementById("vehicleEditNameInput");
      const notesInput = document.getElementById("vehicleEditNotesInput");
      const errorEl = document.getElementById("vehicleEditError");

      if (payload.edit_mode === "saved_vehicle" || payload.action === "edit") {
        titleEl.textContent = "Edit vehicle";
      } else if (payload.category === "watch") {
        titleEl.textContent = "Add to watchlist";
      } else if (payload.category === "ignore") {
        titleEl.textContent = "Ignore vehicle";
      } else {
        titleEl.textContent = "Save vehicle";
      }

      nameInput.value = payload.name || "";
      notesInput.value = payload.notes || "";
      errorEl.hidden = true;
      errorEl.textContent = "";

      _vehicleEditPendingButton = button;
      _vehicleEditPendingPayload = payload;

      updateVehicleEditModalState();

      modal.classList.add("open");
      modal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      document.addEventListener("keydown", onVehicleEditModalKeydown);

      requestAnimationFrame(() => nameInput.focus());
    }

    function closeVehicleEditModal() {
      const modal = document.getElementById("vehicleEditModal");

      if (_vehicleEditPendingButton) {
        _vehicleEditPendingButton.focus();
      } else if (modal.contains(document.activeElement)) {
        document.activeElement.blur();
      }

      modal.classList.remove("open");
      modal.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onVehicleEditModalKeydown);
      _vehicleEditPendingButton = null;
      _vehicleEditPendingPayload = null;
    }

    function onVehicleEditModalKeydown(event) {
      if (event.key === "Escape") closeVehicleEditModal();
    }

    function updateVehicleEditModalState() {
      const nameInput = document.getElementById("vehicleEditNameInput");
      const notesInput = document.getElementById("vehicleEditNotesInput");
      const nameCount = document.getElementById("vehicleEditNameCount");
      const notesCount = document.getElementById("vehicleEditNotesCount");
      const saveButton = document.getElementById("vehicleEditSaveButton");

      const nameLen = nameInput.value.length;
      const notesLen = notesInput.value.length;
      const nameMax = Number(nameInput.maxLength);
      const notesMax = Number(notesInput.maxLength);

      nameCount.textContent = `${nameLen}/${nameMax}`;
      notesCount.textContent = `${notesLen}/${notesMax}`;

      const nameInvalid = nameInput.value.trim() === "" || nameLen > nameMax;
      const notesInvalid = notesLen > notesMax;

      nameCount.classList.toggle("invalid", nameLen > nameMax);
      notesCount.classList.toggle("invalid", notesInvalid);

      saveButton.disabled = nameInvalid || notesInvalid;
    }

    function submitVehicleEditModal() {
      const nameInput = document.getElementById("vehicleEditNameInput");
      const notesInput = document.getElementById("vehicleEditNotesInput");
      const errorEl = document.getElementById("vehicleEditError");
      const saveButton = document.getElementById("vehicleEditSaveButton");

      const name = nameInput.value.trim();
      const notes = notesInput.value.trim();

      if (!name) {
        errorEl.textContent = "Name is required.";
        errorEl.hidden = false;
        nameInput.focus();
        return;
      }

      if (!_vehicleEditPendingButton || !_vehicleEditPendingPayload) return;

      const button = _vehicleEditPendingButton;
      const payload = _vehicleEditPendingPayload;
      payload.name = name;
      payload.notes = notes;

      errorEl.hidden = true;
      errorEl.textContent = "";

      delete payload.edit_mode;

      submitVehicleMapPayload(button, payload, { keepModalOpenOnError: true, modalSaveButton: saveButton });
    }

    function setupVehicleEditModal() {
      const nameInput = document.getElementById("vehicleEditNameInput");
      const notesInput = document.getElementById("vehicleEditNotesInput");
      const saveButton = document.getElementById("vehicleEditSaveButton");

      if (!nameInput || !notesInput || !saveButton) return;

      nameInput.addEventListener("input", updateVehicleEditModalState);
      notesInput.addEventListener("input", updateVehicleEditModalState);
      saveButton.addEventListener("click", submitVehicleEditModal);
    }

    function escHtml(value) {
      return String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    let _rowActionsListenerAttached = false;

    function _onRowActionsOutsideClick(event) {
      if (event.target.closest(".row-actions")) return;
      closeAllRowActionsMenus();
    }

    function _onRowActionsEscape(event) {
      if (event.key !== "Escape") return;
      if (!document.querySelector(".row-actions-menu:not([hidden])")) return;
      closeAllRowActionsMenus({ restoreFocus: true });
    }

    function _attachRowActionsListeners() {
      if (_rowActionsListenerAttached) return;
      _rowActionsListenerAttached = true;
      document.addEventListener("pointerdown", _onRowActionsOutsideClick);
      document.addEventListener("keydown", _onRowActionsEscape);
    }

    function _detachRowActionsListeners() {
      _rowActionsListenerAttached = false;
      document.removeEventListener("pointerdown", _onRowActionsOutsideClick);
      document.removeEventListener("keydown", _onRowActionsEscape);
    }

    function closeRowActionsMenu(menu, toggle, options = {}) {
      if (!menu) return;
      menu.hidden = true;
      menu.style.top = "";
      menu.style.left = "";
      if (toggle) toggle.setAttribute("aria-expanded", "false");
      if (options.restoreFocus && toggle) toggle.focus();
    }

    function closeAllRowActionsMenus(options = {}) {
      const openMenus = Array.from(
        document.querySelectorAll(".row-actions-menu:not([hidden])")
      );
      if (!openMenus.length) return;

      let focusToggle = null;
      openMenus.forEach((menu, index) => {
        const wrapper = menu.closest(".row-actions");
        const toggle = wrapper ? wrapper.querySelector(".row-actions-toggle") : null;
        if (options.restoreFocus && index === 0 && toggle) focusToggle = toggle;
        closeRowActionsMenu(menu, toggle, {});
      });

      if (focusToggle) focusToggle.focus();
      _detachRowActionsListeners();
    }

    function positionRowActionsMenu(menu, toggle) {
      const GAP = 6;
      const rect = toggle.getBoundingClientRect();
      const menuWidth = menu.offsetWidth || 160;
      const menuHeight = menu.offsetHeight || 100;
      const vw = window.innerWidth;
      const vh = window.innerHeight;

      let left = rect.right - menuWidth;
      if (left < 4) left = 4;
      if (left + menuWidth > vw - 4) left = vw - menuWidth - 4;

      let top = rect.bottom + GAP + menuHeight <= vh
        ? rect.bottom + GAP
        : rect.top - GAP - menuHeight;
      top = Math.max(4, Math.min(top, vh - menuHeight - 4));

      menu.style.left = `${left}px`;
      menu.style.top = `${top}px`;
    }

    function toggleRowActionsMenu(toggle) {
      const wrapper = toggle.closest(".row-actions");
      if (!wrapper) return;
      const menu = wrapper.querySelector(".row-actions-menu");
      if (!menu) return;

      if (!menu.hidden) {
        closeRowActionsMenu(menu, toggle, { restoreFocus: true });
        _detachRowActionsListeners();
        return;
      }

      closeAllRowActionsMenus();
      menu.hidden = false;
      toggle.setAttribute("aria-expanded", "true");
      positionRowActionsMenu(menu, toggle);
      _attachRowActionsListeners();

      const firstItem = menu.querySelector(".row-actions-menu-item");
      if (firstItem) requestAnimationFrame(() => firstItem.focus());
    }

    function rowMenuEdit(menuItem) {
      const payload = JSON.parse(menuItem.dataset.payload || "{}");
      const wrapper = menuItem.closest(".row-actions");
      const toggle = wrapper ? wrapper.querySelector(".row-actions-toggle") : null;
      const menu = menuItem.closest(".row-actions-menu");
      closeRowActionsMenu(menu, toggle, {});
      _detachRowActionsListeners();
      openVehicleEditModal(toggle, payload);
    }

    function rowMenuSubmitAction(menuItem) {
      const payload = JSON.parse(menuItem.dataset.payload || "{}");
      const wrapper = menuItem.closest(".row-actions");
      const toggle = wrapper ? wrapper.querySelector(".row-actions-toggle") : null;
      const menu = menuItem.closest(".row-actions-menu");

      if (payload.action === "remove") {
        const label = payload.name ? `"${payload.name}"` : "this saved vehicle";
        if (!window.confirm(`Remove ${label} from your vehicle map?`)) {
          closeRowActionsMenu(menu, toggle, { restoreFocus: true });
          _detachRowActionsListeners();
          return;
        }
      }

      closeRowActionsMenu(menu, toggle, {});
      _detachRowActionsListeners();
      submitVehicleMapPayload(toggle, payload);
    }

    let candidateDrawerOpener = null;

    function openCandidateDrawer(button) {
      const wrapper = button.closest(".row-actions");
      const toggle = wrapper ? wrapper.querySelector(".row-actions-toggle") : null;
      candidateDrawerOpener = toggle;
      closeAllRowActionsMenus();
      const candidate = JSON.parse(button.dataset.candidate || "{}");
      const drawer = document.getElementById("candidateDrawer");
      const titleEl = document.getElementById("candidateDrawerTitle");
      const bodyEl = document.getElementById("candidateDrawerBody");

      titleEl.textContent = candidate.title || "Candidate details";
      bodyEl.innerHTML = renderCandidateDrawer(candidate);

      drawer.classList.add("open");
      drawer.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      document.addEventListener("keydown", onCandidateDrawerKeydown);
    }

    function closeCandidateDrawer() {
      const drawer = document.getElementById("candidateDrawer");
      if (drawer.contains(document.activeElement)) {
        document.activeElement.blur();
      }
      drawer.classList.remove("open");
      drawer.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onCandidateDrawerKeydown);
      if (candidateDrawerOpener && typeof candidateDrawerOpener.focus === "function") {
        candidateDrawerOpener.focus();
      }
      candidateDrawerOpener = null;
    }

    function onCandidateDrawerKeydown(event) {
      if (event.key === "Escape") closeCandidateDrawer();
    }

    let infoModalOpener = null;

    function openInfoModal(button) {
      infoModalOpener = button;
      const modal = document.getElementById("infoModal");
      document.getElementById("infoModalTitle").textContent = button.dataset.infoTitle || "";
      document.getElementById("infoModalBody").innerHTML = button.dataset.infoBody || "";
      modal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      document.addEventListener("keydown", onInfoModalKeydown);
      requestAnimationFrame(() => {
        const closeBtn = modal.querySelector("button[aria-label='Close info modal']");
        if (closeBtn) closeBtn.focus();
      });
    }

    function closeInfoModal() {
      const modal = document.getElementById("infoModal");
      if (modal.contains(document.activeElement)) {
        document.activeElement.blur();
      }
      modal.setAttribute("aria-hidden", "true");
      document.getElementById("infoModalTitle").textContent = "";
      document.getElementById("infoModalBody").innerHTML = "";
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onInfoModalKeydown);
      if (infoModalOpener && typeof infoModalOpener.focus === "function") {
        infoModalOpener.focus();
      }
      infoModalOpener = null;
    }

    function onInfoModalKeydown(event) {
      if (event.key === "Escape") closeInfoModal();
    }

    function categoryDisplayLabel(category) {
      if (category === "known") return "Known";
      if (category === "watch") return "Watch";
      if (category === "ignore") return "Ignored";
      return category;
    }

    function renderCandidateDrawer(c) {
      const sensorIds = Array.isArray(c.sensor_ids) ? c.sensor_ids : [];
      const patternLabels = Array.isArray(c.pattern_labels) ? c.pattern_labels : [];
      const candidatePoints = allTimelinePoints.filter(pt => sensorIds.includes(pt.sensor_id));

      let latestDate = null;
      let latestPoint = null;
      candidatePoints.forEach(pt => {
        const d = parseChartTime(pt.time);
        if (!d) return;
        if (!latestDate || d > latestDate) {
          latestDate = d;
          latestPoint = pt;
        }
      });

      const models = Array.from(new Set(
        candidatePoints.map(pt => categoryValue(pt.model)).filter(v => v !== "Unknown")
      ));
      const protocols = Array.from(new Set(
        candidatePoints.map(pt => categoryValue(pt.protocol)).filter(v => v !== "Unknown")
      ));

      const pressureRows = candidatePoints
        .map(pt => pressurePointValue(pt))
        .filter(pv => pv !== null);

      let pressureLine = "";
      let hasSuspiciousPressure = false;
      if (pressureRows.length > 0) {
        const psiValues = pressureRows.map(pv => pv.normalizedPsi);
        const minPsi = Math.min(...psiValues);
        const maxPsi = Math.max(...psiValues);
        hasSuspiciousPressure = psiValues.some(v => v > PRESSURE_SUSPICIOUS_PSI);
        pressureLine = `Pressure (PSI): ${formatPressure(minPsi)} – ${formatPressure(maxPsi)}`;
      }

      const rssiValues = candidatePoints.map(pt => numericValue(pt.rssi)).filter(v => v !== null);
      const snrValues = candidatePoints.map(pt => numericValue(pt.snr)).filter(v => v !== null);
      const avgRssi = rssiValues.length > 0
        ? rssiValues.reduce((a, b) => a + b, 0) / rssiValues.length
        : null;
      const avgSnr = snrValues.length > 0
        ? snrValues.reduce((a, b) => a + b, 0) / snrValues.length
        : null;

      let summaryHtml = `<div class="drawer-pill-row">`;
      if (c.confidence) summaryHtml += `<span class="pill confidence">${escHtml(c.confidence)}</span>`;
      if (c.category) summaryHtml += `<span class="pill ${escHtml(c.category)}">${escHtml(categoryDisplayLabel(c.category))}</span>`;
      if (c.known_vehicle) summaryHtml += `<span class="drawer-vehicle-name">${escHtml(c.known_vehicle)}</span>`;
      summaryHtml += `</div>`;
      summaryHtml += `<div class="matching-summary-grid drawer-stat-grid">`;
      summaryHtml += `<div class="matching-summary-item"><span class="matching-summary-value">${escHtml(c.sensor_count ?? "")}</span><span class="matching-summary-label">Sensors</span></div>`;
      summaryHtml += `<div class="matching-summary-item"><span class="matching-summary-value">${escHtml(c.pass_count ?? "")}</span><span class="matching-summary-label">Passes</span></div>`;
      summaryHtml += `</div>`;

      let whyHtml = "";
      if (patternLabels.length > 0) {
        whyHtml += `<div class="drawer-block drawer-why-section">`;
        whyHtml += `<div class="chart-inline-note drawer-section-heading">Why this was flagged</div>`;
        patternLabels.forEach(label => {
          const labelClass = label.class || "pattern-default";
          whyHtml += `<div class="drawer-hint-row">`;
          whyHtml += `<span class="pill ${labelClass}">${escHtml(label.text)}</span>`;
          whyHtml += `<span class="drawer-hint-caveat">${escHtml(label.caveat || label.description)}</span>`;
          whyHtml += `</div>`;
        });
        whyHtml += `<div class="chart-inline-note drawer-note-hint">Pattern hints are educated guesses from this report, not confirmed identities.</div>`;
        whyHtml += `</div>`;
      }

      let evidenceHtml = `<div class="drawer-block drawer-evidence-section">`;
      evidenceHtml += `<div class="chart-inline-note drawer-section-heading">Evidence</div>`;
      if (candidatePoints.length === 0) {
        evidenceHtml += `<div class="chart-inline-note">No event detail available from current data.</div>`;
      } else {
        const eventCount = candidatePoints.length;
        evidenceHtml += `<div class="matching-summary-grid drawer-stat-grid">`;
        evidenceHtml += `<div class="matching-summary-item"><span class="matching-summary-value">${escHtml(eventCount)}</span><span class="matching-summary-label">Events</span></div>`;
        evidenceHtml += `<div class="matching-summary-item"><span class="matching-summary-value matching-summary-value--sm">${latestPoint ? escHtml(localDateLabel(latestPoint.time)) : "Unknown"}</span><span class="matching-summary-label">Latest event</span></div>`;
        evidenceHtml += `</div>`;
        if (models.length > 0) {
          evidenceHtml += `<div class="chart-inline-note">Models: ${escHtml(models.join(", "))}</div>`;
        }
        if (protocols.length > 0) {
          evidenceHtml += `<div class="chart-inline-note">Protocols: ${escHtml(protocols.join(", "))}</div>`;
        }
      }
      evidenceHtml += `<div class="chart-inline-note">First seen: ${escHtml(c.first_seen || "—")}</div>`;
      evidenceHtml += `<div class="chart-inline-note">Last seen: ${escHtml(c.last_seen || "—")}</div>`;
      evidenceHtml += `</div>`;

      let decodedFlagsHtml = "";
      const decodedFlags = c.decoded_flags;
      if (decodedFlags && Array.isArray(decodedFlags.values) && decodedFlags.values.length > 0) {
        decodedFlagsHtml += `<div class="drawer-block drawer-decoded-flags-section">`;
        decodedFlagsHtml += `<div class="chart-inline-note drawer-section-heading">Decoded flags observed</div>`;
        decodedFlagsHtml += `<div class="matching-summary-grid drawer-stat-grid">`;
        decodedFlagsHtml += `<div class="matching-summary-item"><span class="matching-summary-value">${escHtml(decodedFlags.total_events ?? "")}</span><span class="matching-summary-label">Events</span></div>`;
        decodedFlagsHtml += `<div class="matching-summary-item"><span class="matching-summary-value">${escHtml(decodedFlags.present_count ?? "")}</span><span class="matching-summary-label">Present</span></div>`;
        decodedFlagsHtml += `<div class="matching-summary-item"><span class="matching-summary-value">${escHtml(decodedFlags.missing_count ?? "")}</span><span class="matching-summary-label">Missing</span></div>`;
        decodedFlagsHtml += `</div>`;
        decodedFlagsHtml += `<div class="drawer-pill-row">`;
        decodedFlags.values.forEach(v => {
          decodedFlagsHtml += `<span class="pill info">${escHtml(v.value)} × ${escHtml(v.count)}</span>`;
        });
        decodedFlagsHtml += `</div>`;
        decodedFlagsHtml += `<div class="chart-inline-note drawer-note-hint">Raw rtl_433 decoder-specific values. Do not compare across different models/protocols.</div>`;
        if (models.length > 1 || protocols.length > 1) {
          decodedFlagsHtml += `<div class="chart-inline-note drawer-note-hint">Multiple model/protocol values observed for these sensors. Treat flags as mixed decoder-specific raw values.</div>`;
        }
        decodedFlagsHtml += `</div>`;
      }

      let technicalHtml = `<details class="drawer-technical-details">`;
      technicalHtml += `<summary>Technical details</summary>`;
      technicalHtml += `<div class="drawer-technical-body">`;
      if (pressureLine) {
        technicalHtml += `<div class="chart-inline-note">${escHtml(pressureLine)}${hasSuspiciousPressure ? ' <span class="pill info">High pressure seen</span>' : ""}</div>`;
      }
      if (avgRssi !== null || avgSnr !== null) {
        const parts = [];
        if (avgRssi !== null) parts.push(`Avg RSSI: ${avgRssi.toFixed(1)}`);
        if (avgSnr !== null) parts.push(`Avg SNR: ${avgSnr.toFixed(1)}`);
        technicalHtml += `<div class="chart-inline-note">${escHtml(parts.join(" · "))}</div>`;
      }
      if (c.match_text) {
        technicalHtml += `<div class="chart-inline-note chart-inline-note--spaced">Known match: ${escHtml(c.match_text)}</div>`;
      }
      if (sensorIds.length > 0) {
        technicalHtml += `<div class="chart-inline-note chart-inline-note--spaced">Sensor IDs: ${escHtml(sensorIds.join(", "))}</div>`;
      }
      technicalHtml += `</div>`;
      technicalHtml += `</details>`;

      return summaryHtml + whyHtml + evidenceHtml + decodedFlagsHtml + technicalHtml;
    }

    function filterTable(tableId, query) {
      const q = query.toLowerCase();
      const table = document.getElementById(tableId);
      const rows = table.querySelectorAll("tbody tr");

      rows.forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(q) ? "" : "none";
      });
    }

    function quickFilterTable(tableId, inputId, query) {
      const input = document.getElementById(inputId);
      input.value = input.value === query ? "" : query;
      filterTable(tableId, input.value);
    }

    function quickFilterExactPillTable(tableId, inputId, query, pillClass) {
      const input = document.getElementById(inputId);
      input.value = input.value === query ? "" : query;
      const active = input.value;
      const table = document.getElementById(tableId);
      const rows = table.querySelectorAll("tbody tr");

      if (!active) {
        rows.forEach(row => { row.style.display = ""; });
        return;
      }

      rows.forEach(row => {
        const selector = pillClass ? `.pill.${pillClass}` : ".pill";
        const pills = row.querySelectorAll(selector);
        const match = Array.from(pills).some(pill => pill.textContent.trim() === active);
        row.style.display = match ? "" : "none";
      });
    }

    function makeTablesSortable() {
      document.querySelectorAll("table").forEach(table => {
        table.querySelectorAll("th").forEach((th, index) => {
          th.addEventListener("click", () => {
            const tbody = table.querySelector("tbody");
            if (!tbody) return;

            const rows = Array.from(tbody.querySelectorAll("tr"));
            const current = th.getAttribute("data-sort") || "none";
            const next = current === "asc" ? "desc" : "asc";

            table.querySelectorAll("th").forEach(h => h.removeAttribute("data-sort"));
            th.setAttribute("data-sort", next);

            rows.sort((a, b) => {
              const av = a.children[index]?.innerText.trim() || "";
              const bv = b.children[index]?.innerText.trim() || "";

              const an = Number(av.replace(/[^0-9.-]/g, ""));
              const bn = Number(bv.replace(/[^0-9.-]/g, ""));

              let result;

              if (!Number.isNaN(an) && !Number.isNaN(bn) && av !== "" && bv !== "") {
                result = an - bn;
              } else {
                result = av.localeCompare(bv);
              }

              return next === "asc" ? result : -result;
            });

            rows.forEach(row => tbody.appendChild(row));
          });
        });
      });
    }

    function hideReportLoadingOverlay() {
      const overlay = document.getElementById("reportLoadingOverlay");
      if (!overlay) return;
      overlay.classList.add("hidden");
      window.setTimeout(() => {
        if (overlay && overlay.parentNode) {
          overlay.parentNode.removeChild(overlay);
        }
      }, 300);
    }

    window.addEventListener("load", hideReportLoadingOverlay);

    function setupBackToTopButton() {
      const button = document.getElementById("backToTopButton");
      if (!button) return;

      function updateVisibility() {
        const shouldShow = window.scrollY > window.innerHeight;
        button.classList.toggle("visible", shouldShow);
      }

      button.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      });

      window.addEventListener("scroll", updateVisibility, { passive: true });
      window.addEventListener("resize", updateVisibility);
      updateVisibility();
    }

    makeTablesSortable();
    setupBackToTopButton();
    setupVehicleEditModal();

    let chartsRendered = false;
    let chartsRenderPending = false;

    function setChartsLoading(isLoading) {
      const loading = document.getElementById("charts-loading");

      if (!loading) return;

      loading.classList.toggle("active", isLoading);
      loading.setAttribute("aria-hidden", isLoading ? "false" : "true");
    }

    function renderChartsSoon() {
      if (chartsRenderPending) return;

      chartsRendered = true;
      chartsRenderPending = true;
      setChartsLoading(true);

      const runRender = () => {
        try {
          renderCharts();
        } finally {
          chartsRenderPending = false;
          setChartsLoading(false);
        }
      };

      if (window.requestAnimationFrame) {
        requestAnimationFrame(() => setTimeout(runRender, 0));
      } else {
        setTimeout(runRender, 0);
      }
    }

    function ensureChartsRendered() {
      if (!chartsRendered) {
        renderChartsSoon();
      }
    }

    function showReportTab(tabId) {
      document.querySelectorAll(".tab-panel").forEach(panel => {
        panel.classList.toggle("active", panel.id === tabId);
      });

      document.querySelectorAll(".tab-button").forEach(button => {
        const isActive = button.getAttribute("data-tab-target") === tabId;
        button.classList.toggle("active", isActive);
      });

      localStorage.setItem("tpmsReportActiveTab", tabId);

      if (tabId === "tab-charts" && window.Plotly) {
        ensureChartsRendered();

        setTimeout(() => {
          document.querySelectorAll("#tab-charts .js-plotly-plot").forEach(chart => {
            Plotly.Plots.resize(chart);
          });
        }, 50);
      }
    }

    const savedTab = localStorage.getItem("tpmsReportActiveTab");

    if (savedTab && document.getElementById(savedTab)) {
      showReportTab(savedTab);
    }

    requestAnimationFrame(() => {
      window.setTimeout(hideReportLoadingOverlay, 50);
    });

    function parseChartTime(value) {
      const date = new Date(value);

      if (Number.isNaN(date.getTime())) {
        return null;
      }

      return date;
    }

    function getNewestChartTimestamp(points) {
      let newest = null;

      points.forEach(point => {
        const date = parseChartTime(point.time);

        if (!date) return;

        if (!newest || date > newest) {
          newest = date;
        }
      });

      return newest;
    }

    function getFilteredChartPointsByTime() {
      const filter = document.getElementById("chart-time-filter");
      const selectedRange = filter ? filter.value : "all";

      if (selectedRange === "all") {
        return allTimelinePoints;
      }

      const newest = getNewestChartTimestamp(allTimelinePoints);

      if (!newest) {
        return [];
      }

      const rangeHours = {
        "24h": 24,
        "7d": 24 * 7,
        "30d": 24 * 30
      }[selectedRange];

      if (!rangeHours) {
        return allTimelinePoints;
      }

      const cutoff = newest.getTime() - (rangeHours * 60 * 60 * 1000);

      return allTimelinePoints.filter(point => {
        const date = parseChartTime(point.time);
        return date && date.getTime() >= cutoff && date.getTime() <= newest.getTime();
      });
    }

    function localDateLabel(value) {
      const date = parseChartTime(value);

      if (!date) {
        return "Unknown";
      }

      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    }

    function localHourLabel(value) {
      const date = parseChartTime(value);

      if (!date) {
        return "Unknown";
      }

      return `${String(date.getHours()).padStart(2, "0")}:00`;
    }

    function countBy(points, labelFn) {
      const counts = new Map();

      points.forEach(point => {
        const label = labelFn(point);
        counts.set(label, (counts.get(label) || 0) + 1);
      });

      return Array.from(counts.entries())
        .map(([label, count]) => ({ label, count }))
        .sort((a, b) => a.label.localeCompare(b.label));
    }

    function countByDate(points) {
      return countBy(
        points.filter(point => parseChartTime(point.time)),
        point => localDateLabel(point.time)
      );
    }

    function countByModelWithProtocols(points) {
      const models = new Map();

      points.forEach(point => {
        const model = categoryValue(point.model);
        const protocol = categoryValue(point.protocol);

        if (!models.has(model)) {
          models.set(model, {
            label: model,
            count: 0,
            protocols: new Map()
          });
        }

        const row = models.get(model);
        row.count += 1;
        row.protocols.set(protocol, (row.protocols.get(protocol) || 0) + 1);
      });

      return Array.from(models.values())
        .map(row => {
          const protocols = Array.from(row.protocols.entries())
            .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
          const protocolText = protocols.length === 1
            ? `Protocol: ${protocols[0][0]}`
            : `Protocols: ${protocols.map(([protocol, count]) => `${protocol} (${count})`).join(", ")}`;

          return {
            label: row.label,
            count: row.count,
            hoverText: `${row.label}<br>Events: ${row.count}<br>${protocolText}`
          };
        })
        .sort((a, b) => a.label.localeCompare(b.label));
    }

    function hourlyCountsFor(points) {
      const counts = new Map();

      for (let hour = 0; hour < 24; hour += 1) {
        counts.set(`${String(hour).padStart(2, "0")}:00`, 0);
      }

      points.forEach(point => {
        if (!parseChartTime(point.time)) return;

        const label = localHourLabel(point.time);
        counts.set(label, (counts.get(label) || 0) + 1);
      });

      return Array.from(counts.entries())
        .map(([label, count]) => ({ label, count }))
        .sort((a, b) => a.label.localeCompare(b.label));
    }

    function numericValue(value) {
      if (value === null || value === undefined || value === "") {
        return null;
      }

      const number = Number(value);
      return Number.isFinite(number) ? number : null;
    }

    function downsampleRows(rows, maxPoints = MAX_SCATTER_POINTS) {
      if (!Array.isArray(rows) || rows.length <= maxPoints) return rows;
      if (maxPoints <= 0) return [];

      const step = rows.length / maxPoints;
      const sampled = [];

      for (let index = 0; index < maxPoints; index += 1) {
        sampled.push(rows[Math.floor(index * step)]);
      }

      return sampled;
    }

    function samplingNote(sampledCount, totalCount) {
      if (totalCount <= sampledCount) return "";
      return `Showing ${sampledCount.toLocaleString()} of ${totalCount.toLocaleString()} points.`;
    }

    function chartTitleWithSampling(title, notes) {
      const note = notes.filter(Boolean).join(" ");
      return note ? `${title}<br><sup>${note}</sup>` : title;
    }

    function pressurePointSamplingNote(label, sampledCount, totalCount) {
      if (totalCount <= sampledCount) return "";
      return `${label}: showing ${sampledCount.toLocaleString()} of ${totalCount.toLocaleString()} points.`;
    }

    function pressurePointValue(point) {
      const pressurePsi = numericValue(point.pressure_psi);

      if (pressurePsi !== null) {
        return {
          normalizedPsi: pressurePsi,
          originalValue: pressurePsi,
          originalUnit: "PSI"
        };
      }

      const pressureKpa = numericValue(point.pressure_kpa);

      if (pressureKpa !== null) {
        return {
          normalizedPsi: pressureKpa * 0.145038,
          originalValue: pressureKpa,
          originalUnit: "kPa"
        };
      }

      return null;
    }

    function formatPressure(value) {
      return Number(value).toFixed(1);
    }

    function pressureHoverText(row, isSuspicious = false) {
      const model = row.point.model || "Unknown";
      const protocol = row.point.protocol || "Unknown";
      const temperatureC = numericValue(row.point.temperature_c);
      const temperatureText = temperatureC !== null
        ? `<br>Temperature C: ${temperatureC.toFixed(1)}`
        : "";
      return [
        isSuspicious ? "Suspicious high pressure<br>" : "",
        `Sensor ID: ${row.point.sensor_id}`,
        `<br>Model: ${model}`,
        `<br>Protocol: ${protocol}`,
        temperatureText,
        `<br>Original pressure: ${formatPressure(row.originalValue)} ${row.originalUnit}`,
        `<br>Normalized pressure: ${formatPressure(row.normalizedPsi)} PSI`
      ].join("");
    }

    function pressureTrace(name, rows, isSuspicious = false) {
      return {
        name,
        x: rows.map(row => row.point.time),
        y: rows.map(row => Number(formatPressure(row.normalizedPsi))),
        mode: "markers",
        type: "scatter",
        text: rows.map(row => pressureHoverText(row, isSuspicious)),
        hovertemplate: "%{text}<extra></extra>",
        marker: {
          size: isSuspicious ? 8 : 7,
          symbol: isSuspicious ? "x" : "circle"
        }
      };
    }

    function updatePressureChartNote(hiddenSuspiciousCount) {
      const note = document.getElementById("pressureChartNote");

      if (!note) return;

      note.textContent = `Suspicious pressure points above ${PRESSURE_SUSPICIOUS_PSI} PSI are hidden by default. Hidden suspicious points: ${hiddenSuspiciousCount}`;
    }

    function categoryValue(value) {
      const text = String(value || "").trim();
      return text || "Unknown";
    }

    function batteryStatus(value) {
      if (value === null || value === undefined || String(value).trim() === "") {
        return "Unknown";
      }

      if (typeof value === "boolean") {
        return value ? "Battery OK" : "Battery Low";
      }

      const text = String(value).trim().toLowerCase();

      if (["1", "true", "ok", "yes", "y", "good"].includes(text)) {
        return "Battery OK";
      }

      if (["0", "false", "low", "no", "n", "bad"].includes(text)) {
        return "Battery Low";
      }

      return "Unknown";
    }

    function maybeBatteryTraceRows(points) {
      return points
        .map(point => ({
          point,
          value: numericValue(point.maybe_battery)
        }))
        .filter(row => row.value !== null);
    }

    function maybeBatteryTraces(rows) {
      const byModel = new Map();

      rows.forEach(row => {
        const model = categoryValue(row.point.model);

        if (!byModel.has(model)) {
          byModel.set(model, []);
        }

        byModel.get(model).push(row);
      });

      return Array.from(byModel.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([model, rows]) => ({
          name: model,
          x: rows.map(row => row.point.time),
          y: rows.map(row => row.value),
          mode: "markers",
          type: "scatter",
          text: rows.map(row => `${row.point.sensor_id || "Unknown"}<br>${row.point.model || "Unknown"}<br>Protocol: ${row.point.protocol || "Unknown"}<br>maybe_battery: ${row.value}`),
          hovertemplate: "%{text}<extra></extra>",
          marker: { size: 7 }
        }));
    }

    function metricTrace(name, rows) {
      if (rows.length < 2) {
        return null;
      }

      return {
        name,
        x: rows.map(row => row.point.time),
        y: rows.map(row => row.value),
        mode: "markers",
        type: "scatter",
        text: rows.map(row => `${row.point.sensor_id || "Unknown"} ${name}`),
        marker: { size: 7 }
      };
    }

    function metricRows(points, field) {
      return points
        .map(point => ({ point, value: numericValue(point[field]) }))
        .filter(row => row.value !== null);
    }

    function emptyChart(chartId, title, message, yAxisTitle = "") {
      Plotly.newPlot(chartId, [], {
        title,
        xaxis: { title: "Time" },
        yaxis: { title: yAxisTitle },
        annotations: [{
          text: message,
          xref: "paper",
          yref: "paper",
          x: 0.5,
          y: 0.5,
          showarrow: false,
          font: { size: 14 }
        }],
        margin: { l: 80, r: 30, t: 50, b: 60 }
      });
    }

    function renderChartSafely(chartId, chartTitle, yAxisTitle, renderFn) {
      try {
        renderFn();
      } catch (error) {
        console.error(`${chartTitle} failed to render`, error);

        try {
          emptyChart(chartId, chartTitle, "Chart failed to render; check browser console", yAxisTitle);
        } catch (emptyError) {
          console.error(`${chartTitle} error annotation failed to render`, emptyError);
        }
      }
    }

    function renderBarChart(chartId, title, rows, xTitle, yTitle, emptyMessage) {
      if (!rows.length) {
        emptyChart(chartId, title, emptyMessage, yTitle);
        return;
      }

      Plotly.newPlot(chartId, [{
        x: rows.map(row => row.label),
        y: rows.map(row => row.count),
        type: "bar",
        text: rows.map(row => row.hoverText || `${row.label}<br>Events: ${row.count}`),
        hovertemplate: "%{text}<extra></extra>"
      }], {
        title,
        xaxis: { title: xTitle },
        yaxis: { title: yTitle },
        margin: { l: 70, r: 30, t: 50, b: 80 }
      });
    }

    function renderCharts() {
      const points = getFilteredChartPointsByTime();
      const emptyMessage = "No data for selected time range";
      const suspiciousPressureToggle = document.getElementById("chart-show-suspicious-pressure");
      const showSuspiciousPressure = Boolean(suspiciousPressureToggle && suspiciousPressureToggle.checked);

      if (!points.length) {
        updatePressureChartNote(0);
        renderChartSafely("timelineChart", "TPMS detections by sensor ID", "TPMS Sensor ID", () => {
          emptyChart("timelineChart", "TPMS detections by sensor ID", emptyMessage, "TPMS Sensor ID");
        });
        renderChartSafely("dailyChart", "TPMS events per day", "Event count", () => {
          emptyChart("dailyChart", "TPMS events per day", emptyMessage, "Event count");
        });
        renderChartSafely("hourlyChart", "TPMS events by hour of day", "Event count", () => {
          emptyChart("hourlyChart", "TPMS events by hour of day", emptyMessage, "Event count");
        });
        renderChartSafely("pressureChart", "TPMS pressure values, normalized to PSI", "Pressure (PSI)", () => {
          emptyChart("pressureChart", "TPMS pressure values, normalized to PSI", emptyMessage, "Pressure (PSI)");
        });
        renderChartSafely("temperatureChart", "TPMS temperature values", "Temperature (°C)", () => {
          emptyChart("temperatureChart", "TPMS temperature values", "Not enough temperature data for this time range", "Temperature (°C)");
        });
        renderChartSafely("modelChart", "Events by model", "Event count", () => {
          emptyChart("modelChart", "Events by model", emptyMessage, "Event count");
        });
        renderChartSafely("batteryChart", "Confirmed Battery Status", "Event count", () => {
          emptyChart("batteryChart", "Confirmed Battery Status", emptyMessage, "Event count");
        });
        renderChartSafely("maybeBatteryChart", "Unconfirmed battery signal", "maybe_battery raw value", () => {
          emptyChart("maybeBatteryChart", "Unconfirmed battery signal", "Not enough maybe_battery data for this time range", "maybe_battery raw value");
        });
        renderChartSafely("signalChart", "TPMS signal quality", "Signal value", () => {
          emptyChart("signalChart", "TPMS signal quality", "Not enough signal data for this time range", "Signal value");
        });
        return;
      }

      renderChartSafely("timelineChart", "TPMS detections by sensor ID", "TPMS Sensor ID", () => {
        const timelineRows = downsampleRows(points);

        Plotly.newPlot("timelineChart", [{
          x: timelineRows.map(point => point.time),
          y: timelineRows.map(point => point.sensor_id),
          mode: "markers",
          type: "scatter",
          text: timelineRows.map(point => `${point.sensor_id} ${point.model || ""}`),
          marker: { size: 7 }
        }], {
          title: chartTitleWithSampling("TPMS detections by sensor ID", [
            samplingNote(timelineRows.length, points.length)
          ]),
          xaxis: { title: "Time" },
          yaxis: { title: "TPMS Sensor ID", type: "category" },
          margin: { l: 170, r: 30, t: 70, b: 60 }
        });
      });

      renderChartSafely("dailyChart", "TPMS events per day", "Event count", () => {
        renderBarChart(
          "dailyChart",
          "TPMS events per day",
          countByDate(points),
          "Date",
          "Event count",
          emptyMessage
        );
      });

      renderChartSafely("hourlyChart", "TPMS events by hour of day", "Event count", () => {
        renderBarChart(
          "hourlyChart",
          "TPMS events by hour of day",
          hourlyCountsFor(points),
          "Hour",
          "Event count",
          emptyMessage
        );
      });

      renderChartSafely("pressureChart", "TPMS pressure values, normalized to PSI", "Pressure (PSI)", () => {
        const pressurePoints = points
          .map(point => {
            const pressure = pressurePointValue(point);

            if (!pressure) return null;

            return {
              point,
              normalizedPsi: pressure.normalizedPsi,
              originalValue: pressure.originalValue,
              originalUnit: pressure.originalUnit,
              isSuspicious: pressure.normalizedPsi > PRESSURE_SUSPICIOUS_PSI
            };
          })
          .filter(row => row !== null);
        const normalPressurePoints = pressurePoints.filter(row => !row.isSuspicious);
        const suspiciousPressurePoints = pressurePoints.filter(row => row.isSuspicious);
        const hiddenSuspiciousCount = showSuspiciousPressure ? 0 : suspiciousPressurePoints.length;

        updatePressureChartNote(hiddenSuspiciousCount);

        if (pressurePoints.length) {
          const pressureTraces = [];
          const sampledNormalPressurePoints = downsampleRows(normalPressurePoints);
          const sampledSuspiciousPressurePoints = downsampleRows(suspiciousPressurePoints);
          const pressureSamplingNotes = [
            pressurePointSamplingNote("Normal", sampledNormalPressurePoints.length, normalPressurePoints.length)
          ];

          if (normalPressurePoints.length) {
            pressureTraces.push(pressureTrace("Pressure", sampledNormalPressurePoints));
          }

          if (showSuspiciousPressure && suspiciousPressurePoints.length) {
            pressureTraces.push(pressureTrace("Suspicious pressure", sampledSuspiciousPressurePoints, true));
            pressureSamplingNotes.push(
              pressurePointSamplingNote("Suspicious", sampledSuspiciousPressurePoints.length, suspiciousPressurePoints.length)
            );
          }

          if (pressureTraces.length) {
            Plotly.newPlot("pressureChart", pressureTraces, {
              title: chartTitleWithSampling("TPMS pressure values, normalized to PSI", pressureSamplingNotes),
              xaxis: { title: "Time" },
              yaxis: { title: "Pressure (PSI)" },
              margin: { l: 80, r: 30, t: 70, b: 60 }
            });
          } else {
            emptyChart("pressureChart", "TPMS pressure values, normalized to PSI", "Only suspicious pressure points in this time range", "Pressure (PSI)");
          }
        } else {
          emptyChart("pressureChart", "TPMS pressure values, normalized to PSI", emptyMessage, "Pressure (PSI)");
        }
      });

      renderChartSafely("temperatureChart", "TPMS temperature values", "Temperature (°C)", () => {
        const temperaturePoints = points
          .map(point => ({
            point,
            value: numericValue(point.temperature_c)
          }))
          .filter(row => row.value !== null);

        if (temperaturePoints.length >= 2) {
          const sampledTemperaturePoints = downsampleRows(temperaturePoints);

          Plotly.newPlot("temperatureChart", [{
            name: "Temperature",
            x: sampledTemperaturePoints.map(row => row.point.time),
            y: sampledTemperaturePoints.map(row => row.value),
            mode: "markers",
            type: "scatter",
            text: sampledTemperaturePoints.map(row => `${row.point.sensor_id || "Unknown"}<br>${row.point.model || "Unknown"}<br>Protocol: ${row.point.protocol || "Unknown"}<br>Temperature C: ${row.value.toFixed(1)}`),
            hovertemplate: "%{text}<extra></extra>",
            marker: { size: 5 }
          }], {
            title: chartTitleWithSampling("TPMS temperature values", [
              samplingNote(sampledTemperaturePoints.length, temperaturePoints.length)
            ]),
            xaxis: { title: "Time" },
            yaxis: { title: "Temperature (°C)" },
            margin: { l: 80, r: 30, t: 70, b: 60 }
          });
        } else {
          emptyChart("temperatureChart", "TPMS temperature values", "Not enough temperature data for this time range", "Temperature (°C)");
        }
      });

      renderChartSafely("modelChart", "Events by model", "Event count", () => {
        renderBarChart(
          "modelChart",
          "Events by model",
          countByModelWithProtocols(points),
          "Model",
          "Event count",
          emptyMessage
        );
      });

      renderChartSafely("batteryChart", "Confirmed Battery Status", "Event count", () => {
        renderBarChart(
          "batteryChart",
          "Confirmed Battery Status",
          countBy(points, point => batteryStatus(point.battery_ok)),
          "Battery status",
          "Event count",
          emptyMessage
        );
      });

      renderChartSafely("maybeBatteryChart", "Unconfirmed battery signal", "maybe_battery raw value", () => {
        const maybeBatteryRows = maybeBatteryTraceRows(points);
        const sampledMaybeBatteryRows = downsampleRows(maybeBatteryRows);
        const maybeBatteryTracesForPlot = maybeBatteryTraces(sampledMaybeBatteryRows);

        if (maybeBatteryRows.length >= 2 && maybeBatteryTracesForPlot.length) {
          Plotly.newPlot("maybeBatteryChart", maybeBatteryTracesForPlot, {
            title: chartTitleWithSampling("Unconfirmed battery signal", [
              samplingNote(sampledMaybeBatteryRows.length, maybeBatteryRows.length)
            ]),
            xaxis: { title: "Time" },
            yaxis: { title: "maybe_battery raw value" },
            margin: { l: 80, r: 30, t: 70, b: 60 }
          });
        } else {
          emptyChart("maybeBatteryChart", "Unconfirmed battery signal", "Not enough maybe_battery data for this time range", "maybe_battery raw value");
        }
      });

      renderChartSafely("signalChart", "TPMS signal quality", "Signal value", () => {
        const signalRows = [
          ["RSSI", metricRows(points, "rssi")],
          ["SNR", metricRows(points, "snr")],
          ["Noise", metricRows(points, "noise")]
        ];
        const signalSamplingNotes = [];
        const signalTraces = signalRows
          .map(([name, rows]) => {
            const sampledRows = downsampleRows(rows);
            const note = pressurePointSamplingNote(name, sampledRows.length, rows.length);

            if (note) {
              signalSamplingNotes.push(note);
            }

            return metricTrace(name, sampledRows);
          })
          .filter(Boolean);

        if (signalTraces.length) {
          Plotly.newPlot("signalChart", signalTraces, {
            title: chartTitleWithSampling("TPMS signal quality", signalSamplingNotes),
            xaxis: { title: "Time" },
            yaxis: { title: "Signal value" },
            margin: { l: 80, r: 30, t: 70, b: 60 }
          });
        } else {
          emptyChart("signalChart", "TPMS signal quality", "Not enough signal data for this time range", "Signal value");
        }
      });
    }

    const chartTimeFilter = document.getElementById("chart-time-filter");
    const suspiciousPressureToggle = document.getElementById("chart-show-suspicious-pressure");

    if (chartTimeFilter) {
      chartTimeFilter.addEventListener("change", () => {
        if (chartsRendered) renderChartsSoon();
      });
    }

    if (suspiciousPressureToggle) {
      suspiciousPressureToggle.addEventListener("change", () => {
        if (chartsRendered) renderChartsSoon();
      });
    }
"""
