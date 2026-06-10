// -----------------------------------------------------------------------
// File editor controller (PLAN.md §9.4)
// -----------------------------------------------------------------------

/**
 * The `tmsEditor` controller is bootstrapped whenever the file_editor.html
 * partial is swapped into the main pane (the partial's tail-end <script>
 * calls `tmsBootEditor()`). It owns:
 *   - the in-memory Feature state
 *   - dirty tracking + beforeunload guard
 *   - structured tab render & input handlers
 *   - raw tab text + Save raw
 *   - rename action
 *   - save-click cleanup + Save flow
 *   - external-change detection via SSE
 */
const tmsEditor = {
  state: null,

  // Module-level session cache for project-level enums vocabularies.
  // Keyed by project name; value is a Promise resolving to
  // `{ status: 'ok'|'missing'|'error', vocab?, message? }`. Persists across
  // editor mounts so navigating between files in the same project does
  // not re-fetch. See specs/features/11-feature-testcase-component-NEW.md.
  _vocabCache: Object.create(null),

  /** Initial bootstrap from the embedded JSON payload. */
  boot() {
    const dataEl = document.getElementById("editor-data");
    if (!dataEl) return;
    const data = JSON.parse(dataEl.textContent);
    this.state = {
      path: data.path,
      file_name: data.file_name,
      feature: data.feature,
      raw: data.raw,
      // The on-load snapshot is what we compare against to detect "external
      // change" via SSE: if disk content matches our `snapshot`, nothing
      // external happened; if it diverges and we're not dirty, we silently
      // reload; if dirty, we show a banner.
      snapshotJson: JSON.stringify(data.feature),
      snapshotRaw: data.raw,
      dirty: false,
      tab: "structured",
      // Project-level enums plumbing (spec 11). Loaded async from
      // GET /api/enums/<project>; render is a no-op until status flips
      // off 'loading'. The vocab is normalised to {kind: {key: label}}.
      enumsProject: (data.path || "").split("/")[0] || null,
      enumsStatus: "loading",
      enumsVocab: undefined,
      enumsMessage: "",
    };
    this.renderStructured();
    this.renderRaw();
    this.wireHeaderButtons();
    this.wireStructuredInputs();
    this.wireRawInputs();
    this.wireTabButtons();
    this.wireEnumsInit();
    this.updateSaveButton();
    // Fire-and-forget enums fetch; renderEnums runs again on resolve.
    this._loadEnums();
  },

  // ---- Tab management ------------------------------------------------

  wireTabButtons() {
    document.getElementById("tab-btn-structured").addEventListener(
      "click", () => this.switchTab("structured")
    );
    document.getElementById("tab-btn-raw").addEventListener(
      "click", () => this.switchTab("raw")
    );
  },

  switchTab(target) {
    if (this.state.tab === target) return;
    if (this.state.dirty) {
      const ok = window.confirm(
        "You have unsaved changes in the current tab. " +
        "Switching tabs will discard them. Continue?"
      );
      if (!ok) return;
      // Discard: reset to snapshot.
      this.state.feature = JSON.parse(this.state.snapshotJson);
      this.state.raw = this.state.snapshotRaw;
      this.markDirty(false);
      this.renderStructured();
      this.renderRaw();
      this.hideRawError();
    }
    this.state.tab = target;
    const isStruct = target === "structured";
    document.getElementById("tab-structured").classList.toggle("hidden", !isStruct);
    document.getElementById("tab-raw").classList.toggle("hidden", isStruct);
    for (const id of ["tab-btn-structured", "tab-btn-raw"]) {
      const btn = document.getElementById(id);
      const active = (id === "tab-btn-structured") === isStruct;
      btn.classList.toggle("border-slate-800", active);
      btn.classList.toggle("text-slate-800", active);
      btn.classList.toggle("font-medium", active);
      btn.classList.toggle("border-transparent", !active);
      btn.classList.toggle("text-slate-500", !active);
    }
  },

  // ---- Dirty + Save-button bookkeeping ------------------------------

  markDirty(d) {
    this.state.dirty = !!d;
    document.getElementById("dirty-indicator").classList.toggle("hidden", !this.state.dirty);
    this.updateSaveButton();
    // Any new edit invalidates a prior "Saved" flash so the badge does
    // not linger over fresh unsaved changes.
    if (this.state.dirty) this._hideSavedBadge();
  },

  /**
   * Show the topbar "Saved" badge for ~1.5s. Called from the success
   * branches of both `save` (structured) and `saveRaw` (raw tab).
   */
  flashSaved() {
    const el = document.getElementById("saved-indicator");
    if (!el) return;
    el.classList.remove("hidden");
    if (this._savedTimer) clearTimeout(this._savedTimer);
    this._savedTimer = setTimeout(() => {
      el.classList.add("hidden");
      this._savedTimer = null;
    }, 1500);
  },

  _hideSavedBadge() {
    const el = document.getElementById("saved-indicator");
    if (el) el.classList.add("hidden");
    if (this._savedTimer) {
      clearTimeout(this._savedTimer);
      this._savedTimer = null;
    }
  },

  updateSaveButton() {
    const btn = document.getElementById("btn-save");
    // R3: Save disabled when description is empty/whitespace-only.
    const desc = (this.state?.feature?.description || "").trim();
    btn.disabled = !desc;
  },

  // ---- Structured render --------------------------------------------

  renderStructured() {
    const f = this.state.feature;
    document.getElementById("feature-description").value = f.description || "";
    this.renderChips("feature", f.tags);
    document.getElementById("kind-scenario").checked = f.scenario.kind === "scenario";
    document.getElementById("kind-outline").checked = f.scenario.kind === "outline";
    document.getElementById("scenario-name").value = f.scenario.name || "";
    this.renderChips("scenario", f.scenario.tags);
    this.renderSteps("background", f.background.steps);
    this.renderSteps("scenario", f.scenario.steps);
    this.renderExamplesSection();
    this.updateBackgroundCount();
    this.renderEnums();
  },

  renderRaw() {
    document.getElementById("raw-text").value = this.state.raw || "";
  },

  renderChips(prefix, tags) {
    const container = document.getElementById(prefix + "-tags-chips");
    const input = document.getElementById(prefix + "-tags-input");
    // Clear existing chips (keep the input).
    Array.from(container.querySelectorAll(".chip")).forEach((c) => c.remove());
    tags.forEach((tag) => {
      const chip = document.createElement("span");
      chip.className = "chip inline-flex items-center gap-1 px-1.5 py-0.5 text-xs rounded bg-slate-200 text-slate-700";
      chip.innerHTML =
        `<span>@${tmsEscape(tag)}</span>` +
        `<button type="button" class="text-slate-500 hover:text-slate-900" aria-label="remove">&times;</button>`;
      chip.querySelector("button").addEventListener("click", () => {
        const list = (prefix === "feature")
          ? this.state.feature.tags
          : this.state.feature.scenario.tags;
        const i = list.indexOf(tag);
        if (i >= 0) list.splice(i, 1);
        this.markDirty(true);
        this.renderChips(prefix, list);
      });
      container.insertBefore(chip, input);
    });
  },

  renderSteps(target, steps) {
    const container = document.getElementById(target + "-steps");
    container.innerHTML = "";
    steps.forEach((step, idx) => {
      const wrap = document.createElement("div");
      wrap.className = "space-y-1";

      const row = document.createElement("div");
      row.className = "flex items-center gap-2";
      row.innerHTML =
        `<select class="border border-slate-300 rounded px-1 py-0.5 text-sm bg-white" data-field="keyword">` +
        ["Given", "When", "Then", "And", "But"].map(
          (k) => `<option value="${k}"${step.keyword === k ? " selected" : ""}>${k}</option>`
        ).join("") +
        `</select>` +
        `<input type="text" class="flex-1 border border-slate-300 rounded px-2 py-0.5 text-sm font-mono" ` +
        `data-field="text" value="${tmsEscape(step.text)}" placeholder="(empty steps are dropped on save)">` +
        `<button type="button" class="text-slate-400 hover:text-red-600 text-sm" data-action="remove" title="remove">&times;</button>`;
      row.querySelector('[data-field="keyword"]').addEventListener("change", (e) => {
        step.keyword = e.target.value;
        this.markDirty(true);
      });
      row.querySelector('[data-field="text"]').addEventListener("input", (e) => {
        step.text = e.target.value;
        this.markDirty(true);
      });
      row.querySelector('[data-action="remove"]').addEventListener("click", () => {
        steps.splice(idx, 1);
        this.renderSteps(target, steps);
        if (target === "background") this.updateBackgroundCount();
        this.markDirty(true);
      });
      wrap.appendChild(row);

      // Per-step data table (PLAN.md §4, models.Step.data_table). Row 0 is
      // treated as the header by tool convention. The rerender callback
      // re-runs `renderSteps` so add/remove operations show their effect.
      const dtRegion = document.createElement("div");
      dtRegion.className = "ml-8";
      this._renderStepDataTable(dtRegion, step, () => this.renderSteps(target, steps));
      wrap.appendChild(dtRegion);

      container.appendChild(wrap);
    });
  },

  /**
   * Render the inline DataTable editor for one step.
   *
   * Layout (mirrors `_renderExamplesGrid` but compact and self-contained):
   *   - When `step.data_table` is null, show a single `+ table` button that
   *     seeds a default `[["col1"]]`.
   *   - When present, show a small grid with:
   *       * header inputs (row 0) with per-column remove buttons inside the
   *         column header cell (refuse if it would leave 0 columns);
   *       * body row inputs with a per-row remove button at the right edge;
   *       * footer: `+ col`, `+ row`, `× remove table`.
   *
   * Column naming follows decision G4 (smallest unused positive integer in
   * `colN`). Body rows are seeded with empty strings to keep the table
   * rectangular for the serializer.
   */
  _renderStepDataTable(container, step, rerender) {
    container.innerHTML = "";
    if (step.data_table == null) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "text-xs text-slate-500 hover:text-slate-800";
      btn.textContent = "+ table";
      btn.addEventListener("click", () => {
        step.data_table = [["col1"]];
        this.markDirty(true);
        rerender();
      });
      container.appendChild(btn);
      return;
    }

    const dt = step.data_table;
    const card = document.createElement("div");
    card.className = "border border-slate-200 rounded bg-slate-50 p-2";
    // Width is half the viewport, but never overflows the editor pane
    // (see helpers block above).
    card.style.width = "50vw";
    card.style.maxWidth = "100%";

    const tableEl = document.createElement("table");
    tableEl.className = "w-full text-xs border-collapse mb-1";
    tableEl.style.tableLayout = "fixed";

    // Colgroup: N equal data columns + a narrow remove-button column.
    const colgroup = document.createElement("colgroup");
    for (let i = 0; i < dt[0].length; i++) colgroup.appendChild(document.createElement("col"));
    const colRm = document.createElement("col");
    colRm.style.width = "28px";
    colgroup.appendChild(colRm);
    tableEl.appendChild(colgroup);

    // Header row (row 0).
    const trHead = document.createElement("tr");
    dt[0].forEach((h, colIdx) => {
      const th = document.createElement("th");
      th.className = "border border-slate-300 bg-white p-0 align-top";
      const wrap = document.createElement("div");
      wrap.className = "flex items-start gap-1";
      const ta = this._makeGridCell(h, (v) => { dt[0][colIdx] = v; this.markDirty(true); }, { header: true });
      const rmCol = document.createElement("button");
      rmCol.type = "button";
      rmCol.className = "text-slate-400 hover:text-red-600 text-xs px-1 pt-0.5 shrink-0";
      rmCol.innerHTML = "&times;";
      rmCol.title = "remove column";
      rmCol.addEventListener("click", () => {
        if (dt[0].length === 1) {
          alert("A data table must have at least one column.");
          return;
        }
        dt.forEach((row) => row.splice(colIdx, 1));
        this.markDirty(true);
        rerender();
      });
      wrap.appendChild(ta);
      wrap.appendChild(rmCol);
      th.appendChild(wrap);
      trHead.appendChild(th);
    });
    // Placeholder <th> aligning with the per-row remove column in tbody.
    trHead.appendChild(document.createElement("th"));
    tableEl.appendChild(trHead);

    // Body rows (rows 1..N-1).
    for (let rowIdx = 1; rowIdx < dt.length; rowIdx++) {
      const tr = document.createElement("tr");
      dt[rowIdx].forEach((cell, colIdx) => {
        const td = document.createElement("td");
        td.className = "border border-slate-300 bg-white p-0 align-top";
        const ta = this._makeGridCell(cell, (v) => { dt[rowIdx][colIdx] = v; this.markDirty(true); });
        td.appendChild(ta);
        tr.appendChild(td);
      });
      const rmTd = document.createElement("td");
      rmTd.className = "px-1 align-top";
      const rmBtn = document.createElement("button");
      rmBtn.type = "button";
      rmBtn.className = "text-slate-400 hover:text-red-600 text-xs";
      rmBtn.innerHTML = "&times;";
      rmBtn.title = "remove row";
      // Snapshot rowIdx into the closure (loop var is `let` so this is safe,
      // but capturing explicitly documents the intent).
      const capturedRow = rowIdx;
      rmBtn.addEventListener("click", () => {
        dt.splice(capturedRow, 1);
        this.markDirty(true);
        rerender();
      });
      rmTd.appendChild(rmBtn);
      tr.appendChild(rmTd);
      tableEl.appendChild(tr);
    }
    card.appendChild(tableEl);

    // Footer: add col / add row / remove table.
    const footer = document.createElement("div");
    footer.className = "flex items-center gap-2 text-xs";
    footer.innerHTML =
      `<button type="button" class="text-slate-600 hover:text-slate-900" data-action="add-col">+ col</button>` +
      `<button type="button" class="text-slate-600 hover:text-slate-900" data-action="add-row">+ row</button>` +
      `<div class="flex-1"></div>` +
      `<button type="button" class="text-slate-400 hover:text-red-600" data-action="remove-table">&times; remove table</button>`;
    footer.querySelector('[data-action="add-col"]').addEventListener("click", () => {
      const used = new Set();
      dt[0].forEach((h) => {
        const m = /^col(\d+)$/.exec(h);
        if (m) used.add(parseInt(m[1], 10));
      });
      let n = 1;
      while (used.has(n)) n++;
      dt[0].push("col" + n);
      for (let r = 1; r < dt.length; r++) dt[r].push("");
      this.markDirty(true);
      rerender();
    });
    footer.querySelector('[data-action="add-row"]').addEventListener("click", () => {
      dt.push(dt[0].map(() => ""));
      this.markDirty(true);
      rerender();
    });
    footer.querySelector('[data-action="remove-table"]').addEventListener("click", () => {
      if (!window.confirm("Remove the data table from this step?")) return;
      step.data_table = null;
      this.markDirty(true);
      rerender();
    });
    card.appendChild(footer);

    container.appendChild(card);
    this._finalizeGridSizing(tableEl);
  },

  // ---- Shared grid cell helpers -------------------------------------
  //
  // Both the per-step `data_table` grid and the outline `Examples` grid
  // share three requirements:
  //   1. The grid renders at ~1/2 of the viewport width (50vw), capped to
  //      the editor pane (`max-width: 100%`). Columns split the available
  //      width evenly via `table-layout: fixed`.
  //   2. Long cell values wrap (`white-space: pre-wrap`) and the row
  //      grows up to 5x the header row's measured height. Beyond that
  //      cap the cell scrolls internally.
  //   3. Cells stay single-line at the data layer because the Gherkin
  //      pipe-table syntax has no in-cell newline escape. We block Enter
  //      keydown and strip CR/LF from pastes.

  /**
   * Build one textarea-backed grid cell.
   *
   * @param {string} initialValue
   * @param {(value: string) => void} onChange called on every keystroke
   * @param {{header?: boolean}} opts
   * @returns {HTMLTextAreaElement}
   */
  _makeGridCell(initialValue, onChange, opts = {}) {
    const ta = document.createElement("textarea");
    ta.rows = 1;
    ta.value = initialValue || "";
    ta.spellcheck = false;
    let cls = "block w-full resize-none px-1 py-0.5 font-mono text-xs leading-tight " +
              "border-0 outline-none bg-transparent overflow-hidden break-words";
    if (opts.header) cls += " font-medium";
    ta.className = cls;
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter") e.preventDefault();
    });
    ta.addEventListener("paste", (e) => {
      const cb = e.clipboardData;
      if (!cb) return;
      const text = cb.getData("text") || "";
      if (!/[\r\n]/.test(text)) return;
      e.preventDefault();
      document.execCommand("insertText", false, text.replace(/[\r\n]+/g, " "));
    });
    ta.addEventListener("input", () => {
      onChange(ta.value);
      this._autoSizeCell(ta);
    });
    return ta;
  },

  /**
   * Recompute one cell's height: max(content height, single-row) capped by
   * `ta._maxHeight` (set in `_finalizeGridSizing`). Falls back to a 100px
   * default until the cap is established.
   */
  _autoSizeCell(ta) {
    const max = ta._maxHeight || 100;
    ta.style.height = "auto";
    const next = Math.min(ta.scrollHeight, max);
    ta.style.height = next + "px";
    ta.style.overflowY = ta.scrollHeight > max ? "auto" : "hidden";
  },

  /**
   * Establish the height cap for a freshly rendered grid by measuring the
   * first textarea (always a header cell). Body cells are then capped at
   * 5x that height and initial-resized. Deferred to the next animation
   * frame when the table is not yet in the DOM so `offsetHeight` is real.
   */
  _finalizeGridSizing(tableEl) {
    const doIt = () => {
      if (!tableEl || !tableEl.isConnected) return;
      const first = tableEl.querySelector("textarea");
      if (!first) return;
      // Let the header reach its natural single-line height first.
      first._maxHeight = 9999;
      this._autoSizeCell(first);
      const headerH = first.offsetHeight || 20;
      const maxH = headerH * 5;
      tableEl.querySelectorAll("textarea").forEach((ta) => {
        ta._maxHeight = maxH;
        this._autoSizeCell(ta);
      });
    };
    if (tableEl && tableEl.isConnected) doIt();
    else requestAnimationFrame(doIt);
  },

  updateBackgroundCount() {
    const n = this.state.feature.background.steps.length;
    const el = document.getElementById("background-count");
    el.textContent = n ? ` (${n} step${n === 1 ? "" : "s"})` : " (empty)";
  },

  renderExamplesSection() {
    const isOutline = this.state.feature.scenario.kind === "outline";
    document.getElementById("examples-section").classList.toggle("hidden", !isOutline);
    if (!isOutline) return;
    const examples = this.state.feature.scenario.examples;
    // Ensure at least one block exists on outline (mirrors plan kind-toggle behavior).
    if (examples.length === 0) {
      examples.push({ tags: [], name: "", header: ["col1"], rows: [] });
    }
    const container = document.getElementById("examples-tables");
    container.innerHTML = "";
    examples.forEach((ex, exIdx) => {
      const card = document.createElement("div");
      card.className = "border border-slate-200 rounded p-3 bg-slate-50";
      card.innerHTML =
        `<div class="flex items-center gap-2 mb-2">` +
        `  <input type="text" class="border border-slate-300 rounded px-2 py-0.5 text-sm" ` +
        `         placeholder="examples name (optional)" data-field="name" value="${tmsEscape(ex.name)}">` +
        `  <div class="flex-1"></div>` +
        `  <button type="button" class="text-xs text-slate-600 hover:text-slate-900" data-action="add-col">+ Col</button>` +
        `  <button type="button" class="text-xs text-slate-600 hover:text-slate-900" data-action="add-row">+ Row</button>` +
        `  <button type="button" class="text-xs text-slate-400 hover:text-red-600" data-action="remove-block" title="remove block">&times; block</button>` +
        `</div>` +
        `<div style="width: 50vw; max-width: 100%; overflow-x: auto;">` +
        `  <table class="w-full text-sm border-collapse" style="table-layout: fixed;" data-role="examples-table"></table>` +
        `</div>`;
      card.querySelector('[data-field="name"]').addEventListener("input", (e) => {
        ex.name = e.target.value;
        this.markDirty(true);
      });
      card.querySelector('[data-action="add-col"]').addEventListener("click", () => {
        // colN where N is smallest unused positive integer (decision G4).
        const used = new Set();
        ex.header.forEach((h) => {
          const m = /^col(\d+)$/.exec(h);
          if (m) used.add(parseInt(m[1], 10));
        });
        let n = 1;
        while (used.has(n)) n++;
        ex.header.push("col" + n);
        ex.rows.forEach((r) => r.push(""));
        this.renderExamplesSection();
        this.markDirty(true);
      });
      card.querySelector('[data-action="add-row"]').addEventListener("click", () => {
        ex.rows.push(ex.header.map(() => ""));
        this.renderExamplesSection();
        this.markDirty(true);
      });
      card.querySelector('[data-action="remove-block"]').addEventListener("click", () => {
        if (!window.confirm("Remove this examples block?")) return;
        examples.splice(exIdx, 1);
        this.renderExamplesSection();
        this.markDirty(true);
      });
      this._renderExamplesGrid(card.querySelector('[data-role="examples-table"]'), ex);
      container.appendChild(card);
    });
  },

  _renderExamplesGrid(tableEl, ex) {
    // Colgroup: N equal data columns + a narrow remove-button column.
    const colgroup = document.createElement("colgroup");
    for (let i = 0; i < ex.header.length; i++) colgroup.appendChild(document.createElement("col"));
    const colRm = document.createElement("col");
    colRm.style.width = "28px";
    colgroup.appendChild(colRm);
    tableEl.appendChild(colgroup);

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ex.header.forEach((h, colIdx) => {
      const th = document.createElement("th");
      th.className = "border border-slate-300 bg-white p-0 align-top";
      const wrap = document.createElement("div");
      wrap.className = "flex items-start gap-1";
      const ta = this._makeGridCell(h, (v) => { ex.header[colIdx] = v; this.markDirty(true); }, { header: true });
      const rmCol = document.createElement("button");
      rmCol.type = "button";
      rmCol.className = "text-slate-400 hover:text-red-600 text-xs px-1 pt-0.5 shrink-0";
      rmCol.innerHTML = "&times;";
      rmCol.title = "remove column";
      rmCol.addEventListener("click", () => {
        if (ex.header.length === 1) {
          alert("An examples block must have at least one column.");
          return;
        }
        ex.header.splice(colIdx, 1);
        ex.rows.forEach((r) => r.splice(colIdx, 1));
        this.renderExamplesSection();
        this.markDirty(true);
      });
      wrap.appendChild(ta);
      wrap.appendChild(rmCol);
      th.appendChild(wrap);
      headerRow.appendChild(th);
    });
    // Placeholder <th> aligning with the per-row remove column in tbody.
    headerRow.appendChild(document.createElement("th"));
    thead.appendChild(headerRow);
    tableEl.appendChild(thead);

    const tbody = document.createElement("tbody");
    ex.rows.forEach((row, rowIdx) => {
      const tr = document.createElement("tr");
      row.forEach((cell, colIdx) => {
        const td = document.createElement("td");
        td.className = "border border-slate-300 bg-white p-0 align-top";
        const ta = this._makeGridCell(cell, (v) => { row[colIdx] = v; this.markDirty(true); });
        td.appendChild(ta);
        tr.appendChild(td);
      });
      const rmTd = document.createElement("td");
      rmTd.className = "border border-slate-300 bg-white px-1 align-top";
      const rmBtn = document.createElement("button");
      rmBtn.type = "button";
      rmBtn.className = "text-slate-400 hover:text-red-600 text-xs";
      rmBtn.innerHTML = "&times;";
      rmBtn.title = "remove row";
      rmBtn.addEventListener("click", () => {
        ex.rows.splice(rowIdx, 1);
        this.renderExamplesSection();
        this.markDirty(true);
      });
      rmTd.appendChild(rmBtn);
      tr.appendChild(rmTd);
      tbody.appendChild(tr);
    });
    tableEl.appendChild(tbody);
    // tableEl may not yet be in the DOM at this call site (the parent card
    // is appended later in `renderExamplesSection`); _finalizeGridSizing
    // defers via rAF in that case.
    this._finalizeGridSizing(tableEl);
  },

  // ---- Structured input wiring --------------------------------------

  wireStructuredInputs() {
    document.getElementById("feature-description").addEventListener("input", (e) => {
      this.state.feature.description = e.target.value;
      this.markDirty(true);
    });
    document.getElementById("scenario-name").addEventListener("input", (e) => {
      this.state.feature.scenario.name = e.target.value;
      this.markDirty(true);
    });
    document.getElementById("kind-scenario").addEventListener("change", () => this._setKind("scenario"));
    document.getElementById("kind-outline").addEventListener("change", () => this._setKind("outline"));
    for (const prefix of ["feature", "scenario"]) {
      const input = document.getElementById(prefix + "-tags-input");
      const err = document.getElementById(prefix + "-tags-error");
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " " || e.key === ",") {
          e.preventDefault();
          this._commitChip(prefix);
        } else if (e.key === "Backspace" && !input.value) {
          // Pop last chip on backspace-in-empty-input.
          const list = (prefix === "feature")
            ? this.state.feature.tags
            : this.state.feature.scenario.tags;
          if (list.length > 0) {
            list.pop();
            this.renderChips(prefix, list);
            this.markDirty(true);
          }
        } else {
          err.classList.add("hidden");
        }
      });
      input.addEventListener("blur", () => this._commitChip(prefix));
    }
  },

  _setKind(kind) {
    const sc = this.state.feature.scenario;
    if (sc.kind === kind) return;
    if (kind === "scenario") {
      // Per plan: refuse to switch out of outline if examples differ from
      // the default; otherwise drop the default-only examples silently.
      const isDefault = sc.examples.length === 1
        && JSON.stringify(sc.examples[0]) === JSON.stringify({tags: [], name: "", header: ["col1"], rows: []});
      const isEmpty = sc.examples.length === 0;
      if (!isDefault && !isEmpty) {
        alert("Clear or modify the examples block(s) before switching back to Scenario.");
        document.getElementById("kind-outline").checked = true;
        return;
      }
      sc.examples = [];
    } else {
      // Switching to outline; ensure default examples block exists.
      if (sc.examples.length === 0) {
        sc.examples = [{ tags: [], name: "", header: ["col1"], rows: [] }];
      }
    }
    sc.kind = kind;
    this.renderExamplesSection();
    this.markDirty(true);
  },

  _commitChip(prefix) {
    const input = document.getElementById(prefix + "-tags-input");
    const err = document.getElementById(prefix + "-tags-error");
    const raw = input.value.trim().replace(/^@/, "");
    if (!raw) {
      err.classList.add("hidden");
      return;
    }
    if (!tmsIsValidTag(raw)) {
      err.textContent = "Tag must be non-empty, ASCII-printable, no whitespace, no '@' or ','.";
      err.classList.remove("hidden");
      return;
    }
    const list = (prefix === "feature")
      ? this.state.feature.tags
      : this.state.feature.scenario.tags;
    if (!list.includes(raw)) {
      list.push(raw);
      this.markDirty(true);
    }
    input.value = "";
    err.classList.add("hidden");
    this.renderChips(prefix, list);
  },

  addStep(target) {
    const arr = (target === "background")
      ? this.state.feature.background.steps
      : this.state.feature.scenario.steps;
    arr.push({ keyword: "Given", text: "", data_table: null });
    this.renderSteps(target, arr);
    if (target === "background") this.updateBackgroundCount();
    this.markDirty(true);
  },

  addExamplesBlock() {
    this.state.feature.scenario.examples.push({
      tags: [], name: "", header: ["col1"], rows: [],
    });
    this.renderExamplesSection();
    this.markDirty(true);
  },

  // ---- Raw input wiring ---------------------------------------------

  wireRawInputs() {
    const ta = document.getElementById("raw-text");
    ta.addEventListener("input", () => {
      this.state.raw = ta.value;
      this.markDirty(true);
      this.hideRawError();
    });
    document.getElementById("btn-save-raw").addEventListener("click", () => this.saveRaw());
  },

  hideRawError() {
    document.getElementById("raw-error").classList.add("hidden");
  },

  showRawError(msg) {
    const el = document.getElementById("raw-error");
    el.textContent = msg;
    el.classList.remove("hidden");
  },

  // ---- Header wiring ------------------------------------------------

  wireHeaderButtons() {
    document.getElementById("btn-rename").addEventListener("click", () => this.rename());
    document.getElementById("btn-move").addEventListener("click", () => this.move());
    document.getElementById("btn-reload").addEventListener("click", () => this.reload());
    document.getElementById("btn-save").addEventListener("click", () => this.save());
  },

  /**
   * Manual reload from disk. Discards any unsaved structured + raw edits
   * (with a confirm when dirty). Symmetric to the tree-refresh button — a
   * safety net when the SSE / watcher path doesn't auto-reload the editor.
   */
  async reload() {
    if (
      this.state.dirty &&
      !window.confirm("Discard unsaved changes and reload from disk?")
    ) return;
    try {
      await this._refreshFromDisk();
      this._hideBanner();
      this.hideRawError();
      this._hideSavedBadge();
    } catch (e) {
      alert("Reload failed: " + e.message);
    }
  },

  /**
   * Open the folder-picker modal and PATCH /api/files/<p>/move on confirm.
   * Folders are sourced from GET /api/tree and filtered to paths that are
   * valid `.feature` parents (depth 2..MAX_FOLDER_DEPTH); the current
   * parent is rendered but disabled so the user can see it in context.
   * On a dirty buffer we confirm with the user before discarding edits —
   * the move is server-side only, the in-memory buffer is reset by the
   * navigation that follows.
   */
  async move() {
    if (
      this.state.dirty &&
      !window.confirm("Discard unsaved changes and move the file?")
    ) return;

    let tree;
    try {
      const r = await fetch("/api/tree");
      if (!r.ok) throw new Error(r.statusText);
      tree = await r.json();
    } catch (e) {
      alert("Could not load folder list: " + e.message);
      return;
    }

    const sourcePath = this.state.path;
    const segments = sourcePath.split("/");
    const currentParent = segments.slice(0, -1).join("/");
    // Recursively walk the tree; collect every folder with 2..10 path
    // segments — matches Storage.move_file's depth guard exactly.
    const candidates = [];
    const walk = (node) => {
      for (const child of node.children || []) {
        if (child.type !== "folder") continue;
        const depth = child.path.split("/").length;
        if (depth >= 2 && depth <= 10) candidates.push(child.path);
        walk(child);
      }
    };
    walk(tree);
    candidates.sort();

    const select = document.createElement("select");
    select.className =
      "w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white";
    // Leading prompt so users have to make a deliberate pick.
    const promptOpt = document.createElement("option");
    promptOpt.value = "";
    promptOpt.textContent = "— pick a destination folder —";
    select.appendChild(promptOpt);
    for (const path of candidates) {
      const opt = document.createElement("option");
      opt.value = path;
      opt.textContent = path === currentParent ? path + "  (current)" : path;
      if (path === currentParent) opt.disabled = true;
      select.appendChild(opt);
    }

    const error = document.createElement("p");
    error.className = "hidden mt-2 text-sm text-red-600";

    const body = document.createElement("div");
    const label = document.createElement("p");
    label.className = "text-sm text-slate-600 mb-2";
    label.textContent = "Move " + sourcePath + " to:";
    body.appendChild(label);
    body.appendChild(select);
    body.appendChild(error);

    const modal = tmsOpenModal({
      title: "Move test case",
      body,
      confirmLabel: "Move",
      confirmDisabled: true,
      onConfirm: async ({ close }) => {
        const destParent = select.value;
        if (!destParent) return;
        error.classList.add("hidden");
        try {
          const r = await fetch(
            "/api/files/" + sourcePath + "/move",
            {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ parent: destParent }),
            }
          );
          if (!r.ok) {
            let msg = r.statusText;
            try {
              const j = await r.json();
              if (j?.error?.message) msg = j.error.message;
            } catch (_) {}
            error.textContent = msg;
            error.classList.remove("hidden");
            return;
          }
          close();
          // Navigate to the file at its new path; the tree refreshes on
          // the SSE `change` event the server publishes after the move.
          const newPath = destParent + "/" + segments[segments.length - 1];
          htmx.ajax("GET", "/ui/file/" + newPath, {
            target: "#main-pane",
            swap: "innerHTML",
          });
        } catch (e) {
          error.textContent = e.message;
          error.classList.remove("hidden");
        }
      },
    });

    // Confirm is gated on a real destination being picked.
    select.addEventListener("change", () => {
      modal.setConfirmDisabled(!select.value);
    });
  },

  // ---- Project-level enums (spec 11) --------------------------------

  /**
   * Resolve the project's enums.yaml vocabulary via GET /api/enums/<project>.
   * Idempotent and session-cached on `tmsEditor._vocabCache[project]` so
   * navigating across files within the same project reuses the same
   * Promise. Triggers `renderEnums()` once resolved. Status branches:
   *   - 'ok'      : `state.enumsVocab = {kind: {key: label}}`
   *   - 'missing' : project has no enums.yaml (legacy / pre-init)
   *   - 'error'   : network or other failure; `state.enumsMessage` set
   * Manual hand-edits to the file take effect on the next page reload;
   * v1 deliberately has no SSE-driven live refresh (spec Operational notes).
   */
  async _loadEnums() {
    const project = this.state.enumsProject;
    if (!project) {
      this.state.enumsStatus = "missing";
      this.renderEnums();
      return;
    }
    let entry = tmsEditor._vocabCache[project];
    if (!entry) {
      entry = (async () => {
        const r = await fetch("/api/enums/" + encodeURIComponent(project));
        if (r.status === 404) return { status: "missing" };
        if (!r.ok) {
          const j = await r.json().catch(() => null);
          return {
            status: "error",
            message: (j && j.error && j.error.message) || r.statusText,
          };
        }
        const vocab = await r.json();
        return { status: "ok", vocab };
      })();
      tmsEditor._vocabCache[project] = entry;
    }
    let resolved;
    try {
      resolved = await entry;
    } catch (e) {
      resolved = { status: "error", message: e.message };
    }
    // Only apply if the editor is still mounted on this same file.
    // (Late-resolving fetches across rapid file swaps would otherwise
    // overwrite state belonging to a newly-opened file.)
    if (!this.state || this.state.enumsProject !== project) return;
    this.state.enumsStatus = resolved.status;
    this.state.enumsVocab = resolved.vocab;
    this.state.enumsMessage = resolved.message || "";
    this.renderEnums();
  },

  /** Render the Enums section per current vocab + feature.enums. */
  renderEnums() {
    if (!this.state) return;
    const missingEl = document.getElementById("feature-enums-missing");
    const emptyEl = document.getElementById("feature-enums-empty");
    const pickersEl = document.getElementById("feature-enums-pickers");
    const orphansEl = document.getElementById("feature-enums-orphans");
    if (!pickersEl || !orphansEl || !missingEl || !emptyEl) return;
    pickersEl.innerHTML = "";
    orphansEl.innerHTML = "";
    missingEl.classList.add("hidden");
    emptyEl.classList.add("hidden");

    const status = this.state.enumsStatus;
    const vocab = this.state.enumsVocab || {};

    if (status === "loading") {
      // Wait for _loadEnums() to resolve; orphans are not meaningful yet
      // because we don't know which keys are defined.
      return;
    }
    if (status === "missing") {
      missingEl.classList.remove("hidden");
      // Skip orphan rendering — there's no vocab to compare against, and
      // the Initialize button is the only meaningful action.
      return;
    }
    if (status === "error") {
      const err = document.createElement("div");
      err.className = "text-xs text-red-700";
      err.textContent = "Failed to load enums: " +
        (this.state.enumsMessage || "unknown error");
      pickersEl.appendChild(err);
      return;
    }
    // status === 'ok'
    if (Object.keys(vocab).length === 0) {
      emptyEl.classList.remove("hidden");
    } else {
      for (const kind of Object.keys(vocab)) {
        pickersEl.appendChild(this._buildEnumPicker(kind, vocab[kind] || {}));
      }
    }
    this._renderEnumOrphans();
  },

  _buildEnumPicker(kind, entries) {
    const row = document.createElement("div");
    row.className = "flex items-center gap-2 text-sm";
    row.dataset.kind = kind;

    const label = document.createElement("label");
    label.className = "w-32 text-xs text-slate-600 truncate";
    label.textContent = kind;
    label.setAttribute("for", "feature-enum-" + kind);
    row.appendChild(label);

    const select = document.createElement("select");
    select.id = "feature-enum-" + kind;
    select.className = "border border-slate-300 rounded px-2 py-0.5 text-sm bg-white";
    select.dataset.kind = kind;
    select.dataset.field = "enum";

    const enumsMap = this.state.feature.enums || {};
    const selectedKey = enumsMap[kind] || "";
    const keys = Object.keys(entries);

    const noneOpt = document.createElement("option");
    noneOpt.value = "";
    noneOpt.textContent = "\u2014 not set \u2014";
    if (!selectedKey) noneOpt.selected = true;
    select.appendChild(noneOpt);
    for (const key of keys) {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = entries[key];
      if (key === selectedKey) opt.selected = true;
      select.appendChild(opt);
    }

    if (keys.length === 0) {
      select.disabled = true;
      row.appendChild(select);
      const hint = document.createElement("span");
      hint.className = "text-xs text-slate-500";
      hint.textContent =
        "No " + kind + " entries defined yet \u2014 edit enums.yaml to add some.";
      row.appendChild(hint);
    } else {
      row.appendChild(select);
    }

    select.addEventListener("change", (e) => {
      if (!this.state.feature.enums) this.state.feature.enums = {};
      this.state.feature.enums[kind] = e.target.value;
      this.markDirty(true);
      // Picker change can never CREATE an orphan (we only offer known
      // keys + "unset"), but clearing a kind back to unset may remove an
      // orphan banner if it had been there from a previous YAML edit.
      this._renderEnumOrphans();
    });

    return row;
  },

  /**
   * Render orphan rows for (kind, key) pairs in feature.enums whose
   * kind/key are not in the current vocab. Per spec error-handling
   * subsection: the data is preserved on read so transient YAML edits
   * don't silently drop it, but the save is blocked until the user
   * clears or re-adds the kind. The actual save-time block is enforced
   * by Storage._cross_check_enums; here we surface the warning UI.
   */
  _renderEnumOrphans() {
    const orphansEl = document.getElementById("feature-enums-orphans");
    if (!orphansEl) return;
    orphansEl.innerHTML = "";
    if (this.state.enumsStatus !== "ok") return;
    const vocab = this.state.enumsVocab || {};
    const enumsMap = this.state.feature.enums || {};
    for (const kind of Object.keys(enumsMap)) {
      const key = enumsMap[kind];
      if (!key) continue;  // unset is never orphan
      const kindEntries = vocab[kind];
      const isOrphan = kindEntries === undefined || !(key in kindEntries);
      if (!isOrphan) continue;
      const row = document.createElement("div");
      row.className = "flex items-center gap-2 text-sm";
      row.dataset.kind = kind;
      row.dataset.orphan = "1";
      const badge = document.createElement("span");
      badge.className =
        "inline-flex items-center gap-1 px-1.5 py-0.5 text-xs rounded bg-amber-100 text-amber-900";
      badge.title =
        "Not defined in enums.yaml \u2014 clear or re-add the kind to save";
      badge.innerHTML =
        '<span>' + tmsEscape(kind) + ": " + tmsEscape(key) + "</span>";
      row.appendChild(badge);
      const clearBtn = document.createElement("button");
      clearBtn.type = "button";
      clearBtn.className =
        "text-xs text-slate-600 hover:text-slate-900 underline";
      clearBtn.dataset.action = "clear-orphan";
      clearBtn.textContent = "Clear";
      clearBtn.addEventListener("click", () => {
        this.state.feature.enums[kind] = "";
        this.markDirty(true);
        this._renderEnumOrphans();
      });
      row.appendChild(clearBtn);
      orphansEl.appendChild(row);
    }
  },

  wireEnumsInit() {
    const btn = document.getElementById("feature-enums-init-btn");
    if (!btn) return;
    btn.addEventListener("click", () => this._initEnumsFile());
  },

  /** POST /api/enums/<project> → hydrate cache + re-render on 201. */
  async _initEnumsFile() {
    const project = this.state.enumsProject;
    if (!project) return;
    const errEl = document.getElementById("feature-enums-init-error");
    if (errEl) {
      errEl.classList.add("hidden");
      errEl.textContent = "";
    }
    try {
      const r = await fetch(
        "/api/enums/" + encodeURIComponent(project),
        { method: "POST" }
      );
      if (!r.ok) {
        const j = await r.json().catch(() => null);
        const msg = (j && j.error && j.error.message) || r.statusText;
        if (errEl) {
          errEl.textContent = msg;
          errEl.classList.remove("hidden");
        }
        return;
      }
      const vocab = await r.json();
      // Hydrate the session cache so a subsequent file open in this
      // project does not refetch.
      tmsEditor._vocabCache[project] = Promise.resolve({
        status: "ok",
        vocab,
      });
      this.state.enumsStatus = "ok";
      this.state.enumsVocab = vocab;
      this.state.enumsMessage = "";
      this.renderEnums();
    } catch (e) {
      if (errEl) {
        errEl.textContent = e.message;
        errEl.classList.remove("hidden");
      }
    }
  },

  // ---- Save flow ----------------------------------------------------

  /** Apply the save-click cleanup pass per PLAN.md §9.4. */
  cleanupBuffer() {
    const f = this.state.feature;
    // Helper: tidy up one step's data_table. Strips trailing/interior body
    // rows whose cells are all-empty; if the entire table (header included)
    // is all-empty, drop the table back to null. Mirrors the empty-row
    // policy used for the outline Examples grid.
    const cleanStepDT = (step) => {
      if (step.data_table == null) return;
      const dt = step.data_table;
      const allEmpty = dt.every((r) => r.every((c) => (c || "").trim() === ""));
      if (allEmpty) { step.data_table = null; return; }
      step.data_table = [dt[0]].concat(
        dt.slice(1).filter((r) => r.some((c) => (c || "").trim() !== ""))
      );
    };
    f.background.steps = f.background.steps.filter((s) => (s.text || "").trim() !== "");
    f.background.steps.forEach(cleanStepDT);
    f.scenario.steps = f.scenario.steps.filter((s) => (s.text || "").trim() !== "");
    f.scenario.steps.forEach(cleanStepDT);
    if (f.scenario.kind === "outline") {
      f.scenario.examples.forEach((ex) => {
        ex.rows = ex.rows.filter((r) => r.some((c) => (c || "").trim() !== ""));
      });
      // Refuse if cleanup yielded no examples rows AND no remaining examples block.
      const blocks = f.scenario.examples.length;
      if (blocks === 0) {
        return "An outline must have at least one Examples block.";
      }
    }
    return null;
  },

  async save() {
    if (this.state.tab === "raw") return this.saveRaw();
    const err = this.cleanupBuffer();
    if (err) {
      alert("Cannot save: " + err);
      this.renderExamplesSection();
      this.renderSteps("background", this.state.feature.background.steps);
      this.renderSteps("scenario", this.state.feature.scenario.steps);
      return;
    }
    // Rerender so the user can see the cleaned-up state.
    this.renderSteps("background", this.state.feature.background.steps);
    this.renderSteps("scenario", this.state.feature.scenario.steps);
    this.renderExamplesSection();
    this.updateBackgroundCount();

    try {
      const r = await fetch("/api/files/" + this.state.path, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.state.feature),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => null);
        alert("Save failed: " + (j?.error?.message || r.statusText));
        return;
      }
      // Refetch to capture the canonicalised on-disk version.
      await this._refreshFromDisk();
      this.flashSaved();
    } catch (e) {
      alert("Save failed: " + e.message);
    }
  },

  async saveRaw() {
    this.hideRawError();
    try {
      const r = await fetch("/api/files/" + this.state.path + "/raw", {
        method: "PUT",
        headers: { "Content-Type": "text/plain" },
        body: this.state.raw,
      });
      if (!r.ok) {
        const j = await r.json().catch(() => null);
        const msg = j?.error?.message || r.statusText;
        const loc = j?.error?.details;
        this.showRawError(
          (loc && loc.line)
            ? `Line ${loc.line}, col ${loc.column}: ${msg}`
            : msg
        );
        return;
      }
      await this._refreshFromDisk();
      this.flashSaved();
    } catch (e) {
      this.showRawError(e.message);
    }
  },

  async _refreshFromDisk() {
    const [structuredR, rawR] = await Promise.all([
      fetch("/api/files/" + this.state.path),
      fetch("/api/files/" + this.state.path + "/raw"),
    ]);
    if (!structuredR.ok || !rawR.ok) return;
    const feature = await structuredR.json();
    const raw = await rawR.text();
    this.state.feature = feature;
    this.state.raw = raw;
    this.state.snapshotJson = JSON.stringify(feature);
    this.state.snapshotRaw = raw;
    this.markDirty(false);
    this.renderStructured();
    this.renderRaw();
  },

  // ---- External-change banner (PLAN.md §9.5) ------------------------

  /**
   * Called by the body-level `sse:change` handler. Compares disk content
   * with the current snapshot:
   *   - file removed on disk → "removed" banner with Discard
   *   - file changed and we're not dirty → silent reload
   *   - file changed and we're dirty → "external change" banner with Reload
   */
  async onExternalChange() {
    if (!this.state) return;
    let diskFeature, diskRaw, removed = false;
    try {
      const r = await fetch("/api/files/" + this.state.path);
      if (r.status === 404) {
        removed = true;
      } else if (r.ok) {
        diskFeature = await r.json();
        const rawR = await fetch("/api/files/" + this.state.path + "/raw");
        if (rawR.ok) diskRaw = await rawR.text();
      } else {
        return;
      }
    } catch (_e) {
      return;
    }
    if (removed) {
      this._showBanner({
        kind: "error",
        message: "This file was removed on disk.",
        actions: [
          { label: "Discard", action: () => this._closeEditor() },
        ],
      });
      return;
    }
    const diskJson = JSON.stringify(diskFeature);
    if (diskJson === this.state.snapshotJson && diskRaw === this.state.snapshotRaw) {
      return;  // No change relative to our snapshot.
    }
    if (!this.state.dirty) {
      this.state.feature = diskFeature;
      this.state.raw = diskRaw;
      this.state.snapshotJson = diskJson;
      this.state.snapshotRaw = diskRaw;
      this.renderStructured();
      this.renderRaw();
      this._showBanner({
        kind: "info",
        message: "File was updated externally; the editor reloaded.",
        actions: [{ label: "Dismiss", action: () => this._hideBanner() }],
      });
      return;
    }
    this._showBanner({
      kind: "warn",
      message: "File changed externally while you have unsaved changes.",
      actions: [
        {
          label: "Reload (discard mine)",
          action: () => {
            this.state.feature = diskFeature;
            this.state.raw = diskRaw;
            this.state.snapshotJson = diskJson;
            this.state.snapshotRaw = diskRaw;
            this.markDirty(false);
            this.renderStructured();
            this.renderRaw();
            this._hideBanner();
          },
        },
        { label: "Keep editing", action: () => this._hideBanner() },
      ],
    });
  },

  _showBanner({ kind, message, actions }) {
    const el = document.getElementById("editor-banner");
    const colors = {
      info: "bg-blue-50 border-blue-200 text-blue-800",
      warn: "bg-amber-50 border-amber-200 text-amber-800",
      error: "bg-red-50 border-red-200 text-red-800",
    }[kind] || "bg-slate-50 border-slate-200 text-slate-800";
    el.className = "mb-3 px-3 py-2 rounded border flex items-center gap-3 " + colors;
    el.innerHTML = `<span class="flex-1">${tmsEscape(message)}</span>`;
    actions.forEach((a) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "px-2 py-1 text-xs border border-current rounded hover:bg-white/50";
      btn.textContent = a.label;
      btn.addEventListener("click", a.action);
      el.appendChild(btn);
    });
  },

  _hideBanner() {
    const el = document.getElementById("editor-banner");
    el.className = "hidden mb-3";
    el.innerHTML = "";
  },

  _closeEditor() {
    this.state = null;
    htmx.ajax("GET", "/ui/folder/", { target: "#main-pane", swap: "innerHTML" });
  },

  // ---- Rename -------------------------------------------------------

  async rename() {
    const current = this.state.file_name;
    const next = (window.prompt("Rename file to:", current) || "").trim();
    if (!next || next === current) return;
    try {
      const r = await fetch(
        "/api/files/" + this.state.path + "/rename",
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file_name: next }),
        }
      );
      if (!r.ok) {
        const j = await r.json().catch(() => null);
        alert("Rename failed: " + (j?.error?.message || r.statusText));
        return;
      }
      // Reload the editor at the new path; pick up auto-appended .feature ext.
      const parent = this.state.path.replace(/\/[^/]+$/, "");
      const newName = next.toLowerCase().endsWith(".feature") ? next : next + ".feature";
      const newPath = parent ? parent + "/" + newName : newName;
      htmx.ajax("GET", "/ui/file/" + newPath, {
        target: "#main-pane",
        swap: "innerHTML",
      });
    } catch (e) {
      alert("Rename failed: " + e.message);
    }
  },
};

/** Called by the file_editor.html partial after it lands in the DOM. */
function tmsBootEditor() {
  tmsEditor.boot();
}

