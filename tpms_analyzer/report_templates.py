CANDIDATE_DRAWER_HTML = """
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
  <div id="vehicleEditModal" class="vehicle-edit-modal" role="dialog" aria-modal="true" aria-hidden="true" aria-labelledby="vehicleEditModalTitle">
    <div class="vehicle-edit-modal-backdrop" onclick="closeVehicleEditModal()"></div>
    <div class="vehicle-edit-modal-panel">
      <div class="vehicle-edit-modal-header">
        <strong id="vehicleEditModalTitle">Edit vehicle</strong>
        <button type="button" class="candidate-drawer-close" onclick="closeVehicleEditModal()">&#x2715; Close</button>
      </div>

      <label class="vehicle-edit-field">
        <span>Name <span class="muted">(required)</span></span>
        <input id="vehicleEditNameInput" class="vehicle-edit-input" type="text" maxlength="120" autocomplete="off" />
        <span id="vehicleEditNameCount" class="vehicle-edit-counter">0/120</span>
      </label>

      <label class="vehicle-edit-field">
        <span>Description / notes</span>
        <textarea id="vehicleEditNotesInput" class="vehicle-edit-textarea" maxlength="500" rows="5"></textarea>
        <span id="vehicleEditNotesCount" class="vehicle-edit-counter">0/500</span>
      </label>

      <div id="vehicleEditError" class="vehicle-edit-error" hidden></div>

      <div class="vehicle-edit-actions">
        <button type="button" class="small-action-button" onclick="closeVehicleEditModal()">Cancel</button>
        <button id="vehicleEditSaveButton" type="button" class="small-action-button watch-action">Save</button>
      </div>
    </div>
  </div>
  <div id="infoModal" class="info-modal" aria-hidden="true" onclick="closeInfoModal()">
    <div class="info-modal-panel"
         role="dialog"
         aria-modal="true"
         aria-labelledby="infoModalTitle"
         onclick="event.stopPropagation()">
      <div class="vehicle-edit-modal-header">
        <h2 id="infoModalTitle"></h2>
        <button type="button" class="info-modal-close"
                onclick="closeInfoModal()"
                aria-label="Close info modal">&#x00D7;</button>
      </div>
      <div id="infoModalBody" class="info-modal-body"></div>
    </div>
  </div>
  <button id="backToTopButton" class="back-to-top-button" type="button" aria-label="Back to top">
    &#x2191; Top
  </button>
"""
