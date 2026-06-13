// -----------------------------------------------------------------------
// Run editor controller — Phase 3.D of `10-feature-test-run-NEW.md`.
//
// Singleton mirroring `tmsEditor`: bootstrapped by run_editor.html's
// tail <script> on every htmx swap. Owns dirty tracking, Save (PATCH),
// Reload (re-fetch the partial), and the transient Saved badge. Add /
// remove case rows + tombstone styling + SSE listener land in 3.E–3.G.
//
// Dirty is computed by comparing a JSON snapshot of {name, description,
// results[]} against the live DOM read; this gives us a single
// source-of-truth check that costs ~one stringify per keystroke (cheap
// for v1; revisit if runs grow past ~200 rows).
// -----------------------------------------------------------------------

const tmsRunEditor = {
  state: null,
  // Banner message deferred across an htmx.ajax re-mount; consumed by
  // the next boot() so the announcement survives the swap.
  _pendingBanner: null,

  /** Boot from the rendered #run-editor partial. */
  boot() {
    const root = document.getElementById("run-editor");
    if (!root) {
      this.state = null;
      return;
    }
    this.state = {
      project: root.dataset.project,
      group: root.dataset.group,
      file_name: root.dataset.fileName,
      created_at: root.dataset.createdAt,
      dirty: false,
      baselineJson: "",
      _savedTimer: null,
    };
    this.state.baselineJson = this._compareJson(this._readCurrent());
    this._wireInputs();
    this._wireHeaderButtons();
    this._refreshDirty();
    // Surface any banner queued by a prior instance's external-change
    // / discard-mine flow.
    if (this._pendingBanner) {
      const b = this._pendingBanner;
      this._pendingBanner = null;
      this._showBanner({
        kind: b.kind,
        message: b.message,
        actions: [{ label: "Dismiss", action: () => this._hideBanner() }],
      });
    }
  },

  /** Snapshot the live DOM into the shape patch_run expects.
   *  E2: only `tr[data-file-path]` rows are results — folder heading rows
   *  (`tr.run-group-head`) carry no data-file-path and are skipped. The
   *  result order is the visual (grouped) DOM order, which Save persists. */
  _readCurrent() {
    const nameEl = document.getElementById("run-name");
    const descEl = document.getElementById("run-description");
    const rows = document.querySelectorAll("#run-results tbody tr[data-file-path]");
    const results = [];
    rows.forEach((tr) => {
      results.push({
        file_path: tr.dataset.filePath,
        result: tr.querySelector(".run-result-select").value,
        remark: tr.querySelector(".run-remark").value,
      });
    });
    return {
      name: nameEl ? nameEl.value : "",
      description: descEl ? descEl.value : "",
      results,
    };
  },

  /** Order-insensitive projection for baseline / live / disk comparisons.
   *  E2: folder grouping reorders the DOM relative to on-disk order, but
   *  dirty-tracking and external-change detection are about *content*, not
   *  display order. Sort results by file_path before stringify so merely
   *  opening an ungrouped run never flashes a false "changed" state. (Save
   *  still serialises `_readCurrent()` in grouped DOM order.) */
  _compareJson(snapshot) {
    const results = [...snapshot.results].sort((a, b) =>
      a.file_path < b.file_path ? -1 : a.file_path > b.file_path ? 1 : 0
    );
    return JSON.stringify({
      name: snapshot.name,
      description: snapshot.description,
      results,
    });
  },

  _wireInputs() {
    const onChange = () => this._refreshDirty();
    document.getElementById("run-name").addEventListener("input", onChange);
    document.getElementById("run-description").addEventListener("input", onChange);
    // Delegated handlers on the tbody so rows added by "+ Add test case"
    // (Phase 3.E) participate without per-row re-wiring.
    const tbody = document.querySelector("#run-results tbody");
    if (tbody) {
      tbody.addEventListener("input", (e) => {
        if (e.target.matches(".run-remark")) onChange();
      });
      tbody.addEventListener("change", (e) => {
        if (e.target.matches(".run-result-select")) {
          // E3: keep the colour hook in lock-step with the chosen value
          // so app.css's [data-status] palette recolours the closed select.
          e.target.dataset.status = e.target.value;
          onChange();
        }
      });
      tbody.addEventListener("click", (e) => {
        if (e.target.matches(".run-row-remove")) {
          const row = e.target.closest("tr");
          const head = this._groupHeadFor(row);
          row.remove();
          // E2: drop the folder heading once its group has no result rows.
          if (head && this._groupIsEmpty(head)) head.remove();
          this._afterRowsChanged();
        }
      });
    }
  },

  _wireHeaderButtons() {
    document
      .getElementById("btn-run-save")
      .addEventListener("click", () => this.save());
    document
      .getElementById("btn-run-reload")
      .addEventListener("click", () => this.reload());
    document
      .getElementById("btn-run-add-case")
      .addEventListener("click", () => this._onAddCaseClicked());
  },

  /** Clone a fresh row from the server-rendered <template> prototype. */
  _createResultRow(file_path) {
    const tpl = document.getElementById("run-result-row-template");
    const tr = tpl.content.firstElementChild.cloneNode(true);
    tr.dataset.filePath = file_path;
    const linkCell = tr.children[0];
    linkCell.setAttribute("title", file_path);
    const link = linkCell.querySelector(".run-row-link");
    // E2: rows are filename-only; the folder is carried by the group heading.
    // Defensive split via lastIndexOf so zero-slash paths render the whole
    // string as the filename — mirrors the Jinja `rsplit('/', 1)` branch.
    const idx = file_path.lastIndexOf("/");
    const name = idx >= 0 ? file_path.slice(idx + 1) : file_path;
    link.querySelector('[data-role="filename"]').textContent = name;
    link.setAttribute("hx-get", `/ui/file/${file_path}`);
    // Result defaults to PENDING (spec: "newly-checked row is appended
    // as a fresh PENDING row with empty remark").
    const sel = tr.querySelector(".run-result-select");
    sel.value = "PENDING";
    sel.dataset.status = sel.value; // E3: colour hook for the shared palette
    tr.querySelector(".run-remark").value = "";
    // tech-05 (RD-1b): scenario name is display-only and not carried by the
    // case picker, so fetch it lazily from the feature read API and fill the
    // cell once resolved. The cell is never read by _readCurrent(), so this
    // async fill never affects dirty tracking.
    this._fillScenarioName(tr.querySelector(".run-scenario-name"), file_path);
    return tr;
  },

  /** Populate a row's display-only scenario-name cell from the feature API. */
  async _fillScenarioName(cell, file_path) {
    if (!cell) return;
    try {
      const r = await fetch(`/api/files/${file_path}`, {
        headers: { Accept: "application/json" },
      });
      if (!r.ok) return;
      const data = await r.json();
      const name = (data.scenario && data.scenario.name) || "";
      cell.textContent = name;
      cell.setAttribute("title", name);
    } catch (_e) {
      /* leave the cell blank on any failure (RD-4) */
    }
  },

  /** Folder of a data-root-relative file_path ("" when zero-slash). */
  _folderOf(file_path) {
    const idx = file_path.lastIndexOf("/");
    return idx >= 0 ? file_path.slice(0, idx) : "";
  },

  /** Clone a folder heading row from the server-rendered <template>. */
  _createGroupHead(folder) {
    const tpl = document.getElementById("run-group-head-template");
    const tr = tpl.content.firstElementChild.cloneNode(true);
    tr.dataset.groupFolder = folder;
    tr.querySelector("td span").textContent = folder || "(ungrouped)";
    return tr;
  },

  /** The folder heading governing `row` (null if rows aren't grouped). */
  _groupHeadFor(row) {
    let cur = row.previousElementSibling;
    while (cur && !cur.classList.contains("run-group-head")) {
      cur = cur.previousElementSibling;
    }
    return cur;
  },

  /** True when a heading's group has no remaining result rows. */
  _groupIsEmpty(head) {
    let cur = head.nextElementSibling;
    while (cur && !cur.classList.contains("run-group-head")) {
      if (cur.matches("tr[data-file-path]")) return false;
      cur = cur.nextElementSibling;
    }
    return true;
  },

  /** Insert a result row into its folder group, creating a heading if new. */
  _insertResultRow(tbody, row, folder) {
    let head = null;
    tbody.querySelectorAll("tr.run-group-head").forEach((h) => {
      if (h.dataset.groupFolder === folder) head = h;
    });
    if (!head) {
      tbody.appendChild(this._createGroupHead(folder));
      tbody.appendChild(row);
      return;
    }
    // Place after the last row of this group (before the next heading / end).
    let last = head;
    let cur = head.nextElementSibling;
    while (cur && !cur.classList.contains("run-group-head")) {
      last = cur;
      cur = cur.nextElementSibling;
    }
    last.after(row);
  },

  /** Toggle table / empty-state visibility + refresh dirty. */
  _afterRowsChanged() {
    const tbody = document.querySelector("#run-results tbody");
    const hasRows = !!(
      tbody && tbody.querySelectorAll("tr[data-file-path]").length > 0
    );
    const table = document.getElementById("run-results");
    const empty = document.getElementById("run-results-empty");
    if (table) table.classList.toggle("hidden", !hasRows);
    if (empty) empty.classList.toggle("hidden", hasRows);
    this._refreshDirty();
  },

  async _onAddCaseClicked() {
    if (!this.state) return;
    const { project } = this.state;
    let features;
    try {
      features = await tmsFetchProjectFeaturePaths(project);
    } catch (e) {
      alert("Could not load test cases: " + e.message);
      return;
    }
    // Exclude cases that are already in the run (spec: "filtered to
    // exclude cases already in `results`").
    const existing = new Set();
    document
      .querySelectorAll("#run-results tbody tr[data-file-path]")
      .forEach((tr) => existing.add(tr.dataset.filePath));

    const body = document.createElement("div");
    let modalRef = null;
    const picker = tmsBuildCasePicker(features, {
      exclude: existing,
      onChange: () => {
        if (!modalRef) return;
        modalRef.setConfirmDisabled(picker.getSelected().length === 0);
      },
    });
    body.appendChild(picker.node);

    modalRef = tmsOpenModal({
      title: "Add test cases",
      body,
      size: "lg",
      confirmLabel: "Add cases",
      confirmDisabled: true,
      onConfirm: ({ close }) => {
        const paths = picker.getSelected();
        if (paths.length === 0) return;
        const tbody = document.querySelector("#run-results tbody");
        for (const p of paths) {
          // E2: land each new case in its folder group (creating a heading).
          this._insertResultRow(tbody, this._createResultRow(p), this._folderOf(p));
        }
        // Tell htmx to process the new hx-get attributes on the cloned
        // file-path links so clicks behave like the server-rendered
        // rows.
        if (window.htmx && tbody) htmx.process(tbody);
        close();
        this._afterRowsChanged();
      },
    });
  },

  _refreshDirty() {
    if (!this.state) return;
    const liveJson = this._compareJson(this._readCurrent());
    const dirty = liveJson !== this.state.baselineJson;
    this._setDirty(dirty);
  },

  _setDirty(d) {
    this.state.dirty = !!d;
    const dirtyEl = document.getElementById("run-dirty-indicator");
    const saveBtn = document.getElementById("btn-run-save");
    if (dirtyEl) dirtyEl.classList.toggle("hidden", !this.state.dirty);
    if (saveBtn) saveBtn.disabled = !this.state.dirty;
    if (this.state.dirty) this._hideSavedBadge();
  },

  flashSaved() {
    const el = document.getElementById("run-saved-indicator");
    if (!el) return;
    el.classList.remove("hidden");
    if (this.state._savedTimer) clearTimeout(this.state._savedTimer);
    this.state._savedTimer = setTimeout(() => {
      el.classList.add("hidden");
      this.state._savedTimer = null;
    }, 1500);
  },

  _hideSavedBadge() {
    const el = document.getElementById("run-saved-indicator");
    if (el) el.classList.add("hidden");
    if (this.state && this.state._savedTimer) {
      clearTimeout(this.state._savedTimer);
      this.state._savedTimer = null;
    }
  },

  async save() {
    if (!this.state || !this.state.dirty) return;
    const { project, group, file_name, created_at } = this.state;
    const current = this._readCurrent();
    const payload = {
      name: current.name,
      created_at,
      description: current.description,
      results: current.results,
    };
    const saveBtn = document.getElementById("btn-run-save");
    saveBtn.disabled = true;
    try {
      const r = await fetch(
        `/api/runs/${project}/${group}/${file_name}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      if (!r.ok) {
        let msg = r.statusText;
        try {
          const j = await r.json();
          if (j && j.error && j.error.message) msg = j.error.message;
        } catch (_) {}
        throw new Error(msg);
      }
      this.state.baselineJson = this._compareJson(current);
      this._setDirty(false);
      this.flashSaved();
    } catch (e) {
      alert("Could not save run: " + e.message);
      this._refreshDirty();
    }
  },

  async reload() {
    if (!this.state) return;
    if (this.state.dirty) {
      const ok = window.confirm(
        "Reload from disk? Your unsaved changes will be discarded."
      );
      if (!ok) return;
    }
    const { project, group, file_name } = this.state;
    // Re-render the whole partial; the tail <script> calls tmsBootRunEditor
    // again, which captures a fresh baseline and clears the dirty flag.
    htmx.ajax("GET", `/ui/run/${project}/${group}/${file_name}`, {
      target: "#main-pane",
      swap: "innerHTML",
    });
  },

  // ---- External-change handling — Phase 3.G (mirrors tmsEditor) -----

  /**
   * Called by the body-level `sse:change` handler. Same state machine
   * as the file editor's `onExternalChange`:
   *   - run YAML removed on disk → "removed" banner with Discard
   *   - run changed and we're not dirty → silent reload + info banner
   *   - run changed and we're dirty → "external change" banner with
   *     Reload (discard mine) / Keep editing
   *
   * The reload path goes through `/ui/run/...` (not the JSON API) so
   * the server re-renders the partial with fresh tombstone flags;
   * tombstone state is therefore always live with respect to the
   * filesystem.
   */
  async onExternalChange() {
    if (!this.state) return;
    const { project, group, file_name } = this.state;
    let diskJson;
    let removed = false;
    try {
      const r = await fetch(`/api/runs/${project}/${group}/${file_name}`);
      if (r.status === 404) {
        removed = true;
      } else if (r.ok) {
        const data = await r.json();
        // Project into the same shape baselineJson uses so the
        // comparison is apples-to-apples (no created_at, no missing).
        diskJson = this._compareJson({
          name: data.name,
          description: data.description,
          results: (data.results || []).map((rr) => ({
            file_path: rr.file_path,
            result: rr.result,
            remark: rr.remark,
          })),
        });
      } else {
        return;
      }
    } catch (_e) {
      return;
    }
    if (removed) {
      this._showBanner({
        kind: "error",
        message: "This run was removed on disk.",
        actions: [
          { label: "Discard", action: () => this._navigateToGroup() },
        ],
      });
      return;
    }
    if (diskJson === this.state.baselineJson) return;
    if (!this.state.dirty) {
      this._reloadAndAnnounce(
        "info",
        "Run was updated externally; the editor reloaded."
      );
      return;
    }
    this._showBanner({
      kind: "warn",
      message: "Run changed externally while you have unsaved changes.",
      actions: [
        {
          label: "Reload (discard mine)",
          action: () => {
            this._setDirty(false);
            this._reloadAndAnnounce(
              "info",
              "Run reloaded from disk; your edits were discarded."
            );
          },
        },
        { label: "Keep editing", action: () => this._hideBanner() },
      ],
    });
  },

  _reloadAndAnnounce(kind, message) {
    if (!this.state) return;
    this._pendingBanner = { kind, message };
    const { project, group, file_name } = this.state;
    htmx.ajax("GET", `/ui/run/${project}/${group}/${file_name}`, {
      target: "#main-pane",
      swap: "innerHTML",
    });
  },

  _navigateToGroup() {
    if (!this.state) return;
    const { project, group } = this.state;
    htmx.ajax("GET", `/ui/folder/${project}/test-run/${group}`, {
      target: "#main-pane",
      swap: "innerHTML",
    });
  },

  _showBanner({ kind, message, actions }) {
    const el = document.getElementById("run-editor-banner");
    if (!el) return;
    const colors =
      {
        info: "bg-blue-50 border-blue-200 text-blue-800",
        warn: "bg-amber-50 border-amber-200 text-amber-800",
        error: "bg-red-50 border-red-200 text-red-800",
      }[kind] || "bg-slate-50 border-slate-200 text-slate-800";
    el.className =
      "mb-3 px-3 py-2 rounded border flex items-center gap-3 " + colors;
    el.innerHTML = `<span class="flex-1">${tmsEscape(message)}</span>`;
    actions.forEach((a) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "px-2 py-1 text-xs border border-current rounded hover:bg-white/50";
      btn.textContent = a.label;
      btn.addEventListener("click", a.action);
      el.appendChild(btn);
    });
  },

  _hideBanner() {
    const el = document.getElementById("run-editor-banner");
    if (el) {
      el.className = "hidden mb-3";
      el.innerHTML = "";
    }
  },
};

/** Called by run_editor.html's tail <script> on every htmx swap. */
function tmsBootRunEditor() {
  tmsRunEditor.boot();
}

