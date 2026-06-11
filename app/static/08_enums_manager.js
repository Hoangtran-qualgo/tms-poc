// -----------------------------------------------------------------------
// Enums manager — main-pane controller for the Enums sidebar tab.
// specs/features/13-feature-enums-crud-NEW.md (S4).
//
// Renders the per-project enums vocabulary as editable kind sections from
// the embedded TMS_ENUMS payload. Add / remove / edit-label are batched in
// memory and persisted with Save (PUT /api/enums/<project>). Rename-key and
// Clear are dedicated server ops (POST .../rename, POST .../clear) that
// reload the view. Booted by an inline script in enums_manager.html on every
// HTMX swap into #main-pane.
// -----------------------------------------------------------------------

const ENUM_ID_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
const ENUM_KEY_RE = /^[A-Za-z_][A-Za-z0-9_-]*$/;

const tmsEnumsManager = {
  state: null,

  /** Bootstrap from the embedded TMS_ENUMS payload (re-run on every swap). */
  boot() {
    const data = window.TMS_ENUMS;
    if (!data) return;
    if (data.missing) {
      const initBtn = document.getElementById("enums-init-btn");
      if (initBtn) initBtn.addEventListener("click", () => this._initFile(data.project));
      this.state = null;
      return;
    }
    // Deep-clone so in-memory edits don't mutate the embedded payload.
    this.state = {
      project: data.project,
      vocab: JSON.parse(JSON.stringify(data.vocab || {})),
    };
    document.getElementById("enums-add-kind-btn")
      .addEventListener("click", () => this._addKind());
    document.getElementById("enums-save-btn")
      .addEventListener("click", () => this._save());
    document.getElementById("enums-clear-btn")
      .addEventListener("click", () => this._clear());
    this.render();
  },

  render() {
    const host = document.getElementById("enums-kinds");
    if (!host) return;
    host.innerHTML = "";
    const kinds = Object.keys(this.state.vocab);
    if (kinds.length === 0) {
      const empty = document.createElement("div");
      empty.className = "text-sm text-slate-500 italic";
      empty.textContent = "No kinds yet — click \u201c+ Add kind\u201d below.";
      host.appendChild(empty);
      return;
    }
    for (const kind of kinds) {
      host.appendChild(this._buildKind(kind, this.state.vocab[kind]));
    }
  },

  _buildKind(kind, entries) {
    const section = document.createElement("section");
    section.className = "border border-slate-200 rounded";
    section.dataset.kind = kind;

    const head = document.createElement("div");
    head.className =
      "flex items-center gap-2 px-3 py-2 bg-slate-50 border-b border-slate-100";
    const title = document.createElement("span");
    title.className = "font-medium text-slate-800 flex-1";
    title.textContent = kind;
    head.appendChild(title);

    const addEntry = document.createElement("button");
    addEntry.type = "button";
    addEntry.className = "text-xs text-slate-600 hover:text-slate-900";
    addEntry.textContent = "+ Add entry";
    addEntry.addEventListener("click", () => this._addEntry(kind));
    head.appendChild(addEntry);

    const rmKind = document.createElement("button");
    rmKind.type = "button";
    rmKind.className = "text-xs text-rose-600 hover:text-rose-800";
    rmKind.textContent = "Remove kind";
    rmKind.addEventListener("click", () => this._removeKind(kind));
    head.appendChild(rmKind);

    section.appendChild(head);

    const body = document.createElement("div");
    body.className = "divide-y divide-slate-100";
    const keys = Object.keys(entries);
    if (keys.length === 0) {
      const none = document.createElement("div");
      none.className = "px-3 py-2 text-xs text-slate-400 italic";
      none.textContent = "No entries.";
      body.appendChild(none);
    } else {
      for (const key of keys) {
        body.appendChild(this._buildEntry(kind, key, entries[key]));
      }
    }
    section.appendChild(body);
    return section;
  },

  _buildEntry(kind, key, label) {
    const row = document.createElement("div");
    row.className = "flex items-center gap-2 px-3 py-1.5 text-sm";
    row.dataset.key = key;

    const keyEl = document.createElement("code");
    keyEl.className = "w-40 truncate text-slate-700";
    keyEl.textContent = key;
    row.appendChild(keyEl);

    const input = document.createElement("input");
    input.type = "text";
    input.className =
      "flex-1 border border-slate-300 rounded px-2 py-0.5 text-sm";
    input.value = label;
    input.addEventListener("input", (e) => {
      this.state.vocab[kind][key] = e.target.value;
    });
    row.appendChild(input);

    const renameBtn = document.createElement("button");
    renameBtn.type = "button";
    renameBtn.className = "text-xs text-slate-600 hover:text-slate-900";
    renameBtn.textContent = "Rename";
    renameBtn.addEventListener("click", () => this._renameKey(kind, key));
    row.appendChild(renameBtn);

    const rmBtn = document.createElement("button");
    rmBtn.type = "button";
    rmBtn.className = "text-xs text-rose-600 hover:text-rose-800";
    rmBtn.textContent = "Remove";
    rmBtn.addEventListener("click", () => this._removeEntry(kind, key));
    row.appendChild(rmBtn);

    return row;
  },

  // ---- In-memory edits (persisted on Save) --------------------------

  _addKind() {
    const name = (window.prompt("New kind name (snake_case identifier):") || "").trim();
    if (!name) return;
    if (!ENUM_ID_RE.test(name)) {
      this._showError(`Invalid kind name: ${name}`);
      return;
    }
    if (name in this.state.vocab) {
      this._showError(`Kind already exists: ${name}`);
      return;
    }
    this.state.vocab[name] = {};
    this.render();
  },

  _removeKind(kind) {
    delete this.state.vocab[kind];
    this.render();
  },

  _addEntry(kind) {
    const key = (window.prompt("New entry key (identifier; dash allowed):") || "").trim();
    if (!key) return;
    if (!ENUM_KEY_RE.test(key)) {
      this._showError(`Invalid key: ${key}`);
      return;
    }
    if (key in this.state.vocab[kind]) {
      this._showError(`Key already exists under ${kind}: ${key}`);
      return;
    }
    const label = (window.prompt("Label for this entry:") || "").trim();
    if (!label) return;
    this.state.vocab[kind][key] = label;
    this.render();
  },

  /**
   * Remove a single entry. Validates usage up-front (GET .../usage) and
   * blocks immediately if a test case still references it, mirroring the
   * server's PUT-time guard message — so the user is stopped at the click,
   * not at Save. Newly-added (unsaved) keys report 0 usage and remove freely.
   */
  async _removeEntry(kind, key) {
    this._hideError();
    const project = this.state.project;
    try {
      const r = await fetch(
        `/api/enums/${encodeURIComponent(project)}/usage` +
          `?kind=${encodeURIComponent(kind)}&key=${encodeURIComponent(key)}`
      );
      const j = await r.json().catch(() => null);
      if (!r.ok) {
        this._showError((j && j.error && j.error.message) || r.statusText);
        return;
      }
      if (j.count > 0) {
        const first = (j.sample && j.sample[0]) || "?";
        const more = j.count > 1 ? ` (and ${j.count - 1} more)` : "";
        this._showError(
          `enum ${kind}: ${key} is in use by test case ${first}${more} ` +
            "\u2014 please clear that enum in the test case first."
        );
        return;
      }
      delete this.state.vocab[kind][key];
      this.render();
    } catch (e) {
      this._showError(e.message);
    }
  },

  // ---- Dedicated server ops -----------------------------------------

  /** Rename a key with a cascade across features (POST .../rename). */
  async _renameKey(kind, oldKey) {
    const newKey = (window.prompt(`Rename ${kind}.${oldKey} to:`, oldKey) || "").trim();
    if (!newKey || newKey === oldKey) return;
    const project = this.state.project;
    try {
      const r = await fetch(
        `/api/enums/${encodeURIComponent(project)}/rename`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind, old_key: oldKey, new_key: newKey }),
        }
      );
      const j = await r.json().catch(() => null);
      if (!r.ok) {
        this._showError((j && j.error && j.error.message) || r.statusText);
        return;
      }
      this._invalidateEditorCache(project);
      this._reloadView();
    } catch (e) {
      this._showError(e.message);
    }
  },

  /** Persist the whole document (PUT). 409 surfaces the in-use message. */
  async _save() {
    const project = this.state.project;
    this._hideError();
    try {
      const r = await fetch(`/api/enums/${encodeURIComponent(project)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.state.vocab),
      });
      const j = await r.json().catch(() => null);
      if (!r.ok) {
        this._showError((j && j.error && j.error.message) || r.statusText);
        return;
      }
      this.state.vocab = j;
      this._invalidateEditorCache(project, j);
      this._showSaved();
      this.render();
    } catch (e) {
      this._showError(e.message);
    }
  },

  /** Reset to the seed (POST .../clear). 409 surfaces the in-use message. */
  async _clear() {
    if (!window.confirm(
      "Reset this project's enum vocabulary to a fresh start? " +
      "This is blocked if any test case still uses an enum."
    )) return;
    const project = this.state.project;
    this._hideError();
    try {
      const r = await fetch(
        `/api/enums/${encodeURIComponent(project)}/clear`,
        { method: "POST" }
      );
      const j = await r.json().catch(() => null);
      if (!r.ok) {
        this._showError((j && j.error && j.error.message) || r.statusText);
        return;
      }
      this._invalidateEditorCache(project);
      this._reloadView();
    } catch (e) {
      this._showError(e.message);
    }
  },

  /** POST /api/enums/<project> to initialize a legacy project, then reload. */
  async _initFile(project) {
    const errEl = document.getElementById("enums-init-error");
    try {
      const r = await fetch(`/api/enums/${encodeURIComponent(project)}`, {
        method: "POST",
      });
      if (!r.ok) {
        const j = await r.json().catch(() => null);
        if (errEl) {
          errEl.textContent = (j && j.error && j.error.message) || r.statusText;
          errEl.classList.remove("hidden");
        }
        return;
      }
      this._invalidateEditorCache(project);
      this._reloadView(project);
    } catch (e) {
      if (errEl) {
        errEl.textContent = e.message;
        errEl.classList.remove("hidden");
      }
    }
  },

  // ---- Helpers ------------------------------------------------------

  /** Re-fetch the manager view for the current (or given) project. */
  _reloadView(project) {
    const proj = project || (this.state && this.state.project);
    if (!proj || !window.htmx) return;
    htmx.ajax("GET", `/ui/enums/${encodeURIComponent(proj)}`, {
      target: "#main-pane",
      swap: "innerHTML",
    });
  },

  /**
   * Keep an open file editor's vocab cache in lock-step with a manager
   * write so its pickers reflect the change without a reload (D6, own-tab).
   */
  _invalidateEditorCache(project, vocab) {
    if (!window.tmsEditor) return;
    if (vocab) {
      tmsEditor._vocabCache[project] = Promise.resolve({ status: "ok", vocab });
    } else {
      delete tmsEditor._vocabCache[project];
    }
  },

  _showError(msg) {
    const el = document.getElementById("enums-error");
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
  },

  _hideError() {
    const el = document.getElementById("enums-error");
    if (el) el.classList.add("hidden");
    const ok = document.getElementById("enums-saved");
    if (ok) ok.classList.add("hidden");
  },

  _showSaved() {
    const ok = document.getElementById("enums-saved");
    if (ok) ok.classList.remove("hidden");
  },
};
