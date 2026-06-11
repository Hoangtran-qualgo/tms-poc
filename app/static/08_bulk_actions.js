// -----------------------------------------------------------------------
// Bulk selection + actions for the folder-detail test-case list.
//
// Scope: the DIRECT test cases of one folder (the server lists only direct
// `features`; sub-folder cases are never in this table). Self-contained,
// classic global-scope module (no build step). Binds itself on every
// htmx swap via `tmsBulkScan`; a `data-bulk-bound` guard prevents
// double-binding when an unrelated pane swaps (spec 03, U3).
//
// All four actions follow the all-or-nothing rule (spec 03 / D3): a
// read-only pre-flight verification over EVERY selected case, and only if
// all pass does a SEQUENTIAL fan-out over the existing single-item
// endpoints run. Any pre-flight failure aborts before a single write; a
// mid-fan-out failure stops and surfaces the offending case (earlier
// writes are not rolled back).
// -----------------------------------------------------------------------

async function _tmsBulkErr(r) {
  let msg = r.statusText;
  try {
    const j = await r.json();
    if (j && j.error && j.error.message) msg = j.error.message;
  } catch (_) {}
  return msg;
}

async function _tmsBulkGet(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await _tmsBulkErr(r));
  return r.json();
}

async function _tmsBulkSend(method, url, body) {
  const opt = { method, headers: {} };
  if (body !== undefined) {
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  const r = await fetch(url, opt);
  if (!r.ok) throw new Error(await _tmsBulkErr(r));
  return r;
}

// Sequential fan-out. Stops at the first failure (TOCTOU after a clean
// pre-flight) and returns the failures collected so far.
async function _tmsBulkFanout(paths, fn) {
  const failures = [];
  for (const p of paths) {
    try {
      await fn(p);
    } catch (e) {
      failures.push({ path: p, reason: e.message });
      break;
    }
  }
  return failures;
}

function _tmsBulkShowFailures(errEl, failures) {
  errEl.innerHTML = "";
  const intro = document.createElement("p");
  intro.className = "font-medium";
  intro.textContent =
    failures.length + " case(s) blocked the action — nothing was changed:";
  const ul = document.createElement("ul");
  ul.className = "list-disc ml-5 mt-1";
  for (const f of failures) {
    const li = document.createElement("li");
    li.textContent = f.path + " — " + f.reason;
    ul.appendChild(li);
  }
  errEl.appendChild(intro);
  errEl.appendChild(ul);
  errEl.classList.remove("hidden");
}

function _tmsBulkErrEl() {
  const el = document.createElement("div");
  el.className = "hidden mt-3 text-sm text-red-600";
  el.setAttribute("data-role", "error");
  return el;
}

// Tag grammar mirror of app/models/_feature.py:_is_valid_tag — non-empty,
// every char in 0x21..0x7E, excluding '@' and ','.
function _tmsValidTag(t) {
  if (!t) return false;
  for (const ch of t) {
    const c = ch.charCodeAt(0);
    if (c < 0x21 || c > 0x7e) return false;
    if (ch === "@" || ch === ",") return false;
  }
  return true;
}

// Parse a free-text tag field into a normalised, de-duped tag list.
// Splits on commas and whitespace; strips a leading '@'. Returns
// {tags, invalid:[...]}. An empty result is valid (= clear all tags).
function _tmsParseTags(raw) {
  const parts = (raw || "").split(/[\s,]+/).filter(Boolean);
  const tags = [];
  const invalid = [];
  for (let p of parts) {
    if (p.startsWith("@")) p = p.slice(1);
    if (!p) continue;
    if (!_tmsValidTag(p)) {
      invalid.push(p);
      continue;
    }
    if (!tags.includes(p)) tags.push(p);
  }
  return { tags, invalid };
}

const tmsBulkActions = {
  // ---- Move (D4: same project only) -----------------------------------
  async move(folderPath, paths, done) {
    const project = folderPath.split("/")[0];
    let tree;
    try {
      tree = await _tmsBulkGet("/api/tree");
    } catch (e) {
      alert("Could not load folders: " + e.message);
      return;
    }
    const candidates = [];
    (function walk(node) {
      for (const c of node.children || []) {
        if (c.type !== "folder") continue;
        const depth = c.path.split("/").length;
        if (depth >= 2 && depth <= 10 && c.path.split("/")[0] === project) {
          candidates.push(c.path);
        }
        walk(c);
      }
    })(tree);
    candidates.sort();

    const select = document.createElement("select");
    select.className =
      "w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white";
    const prompt = document.createElement("option");
    prompt.value = "";
    prompt.textContent = "— pick a destination folder —";
    select.appendChild(prompt);
    for (const path of candidates) {
      const opt = document.createElement("option");
      opt.value = path;
      const rel = path.split("/").slice(1).join("/");
      // The source folder is a no-op destination: show it, disabled.
      opt.textContent = path === folderPath ? rel + "  (current)" : rel;
      if (path === folderPath) opt.disabled = true;
      select.appendChild(opt);
    }

    const body = document.createElement("div");
    const label = document.createElement("p");
    label.className = "text-sm text-slate-600 mb-2";
    label.textContent = "Move " + paths.length + " test case(s) to:";
    const errEl = _tmsBulkErrEl();
    body.appendChild(label);
    body.appendChild(select);
    body.appendChild(errEl);

    tmsOpenModal({
      title: "Move test cases",
      body,
      confirmLabel: "Move",
      onConfirm: async ({ close }) => {
        errEl.classList.add("hidden");
        const dest = select.value;
        if (!dest) return;
        // Pre-flight: same-parent + name conflict at destination.
        let existing = new Set();
        try {
          const contents = await _tmsBulkGet(
            "/api/folders/" + dest + "/contents"
          );
          existing = new Set((contents.features || []).map((f) => f.file_name));
        } catch (e) {
          errEl.textContent = "Could not verify destination: " + e.message;
          errEl.classList.remove("hidden");
          return;
        }
        const failures = [];
        for (const p of paths) {
          const leaf = p.split("/").pop();
          if (dest === folderPath) {
            failures.push({ path: p, reason: "already in this folder" });
          } else if (existing.has(leaf)) {
            failures.push({ path: p, reason: "a file with this name exists at the destination" });
          }
        }
        if (failures.length) {
          _tmsBulkShowFailures(errEl, failures);
          return;
        }
        const fo = await _tmsBulkFanout(paths, (p) =>
          _tmsBulkSend("PATCH", "/api/files/" + p + "/move", { parent: dest })
        );
        if (fo.length) {
          _tmsBulkShowFailures(errEl, fo);
          return;
        }
        close();
        done();
      },
    });
  },

  // ---- Delete ---------------------------------------------------------
  async delete(folderPath, paths, done) {
    const body = document.createElement("div");
    const label = document.createElement("p");
    label.className = "text-sm text-slate-600 mb-2";
    label.textContent =
      "Permanently delete these " + paths.length + " test case(s)?";
    const ul = document.createElement("ul");
    ul.className = "list-disc ml-5 text-sm text-slate-700 max-h-48 overflow-auto";
    for (const p of paths) {
      const li = document.createElement("li");
      li.textContent = p;
      ul.appendChild(li);
    }
    const errEl = _tmsBulkErrEl();
    body.appendChild(label);
    body.appendChild(ul);
    body.appendChild(errEl);

    tmsOpenModal({
      title: "Delete test cases",
      body,
      confirmLabel: "Delete",
      onConfirm: async ({ close }) => {
        errEl.classList.add("hidden");
        const fo = await _tmsBulkFanout(paths, (p) =>
          _tmsBulkSend("DELETE", "/api/files/" + p)
        );
        if (fo.length) {
          _tmsBulkShowFailures(errEl, fo);
          return;
        }
        close();
        done();
      },
    });
  },

  // ---- Re-tag (D1: feature-level tags only; scenario untouched) -------
  async retag(folderPath, paths, done) {
    const body = document.createElement("div");
    const label = document.createElement("p");
    label.className = "text-sm text-slate-600 mb-2";
    label.textContent =
      "Replace feature-level tags on " +
      paths.length +
      " test case(s). Comma- or space-separated; leave empty to clear.";
    const input = document.createElement("input");
    input.type = "text";
    input.className =
      "w-full border border-slate-300 rounded px-2 py-1.5 text-sm font-mono";
    input.placeholder = "@smoke @regression";
    const errEl = _tmsBulkErrEl();
    body.appendChild(label);
    body.appendChild(input);
    body.appendChild(errEl);

    tmsOpenModal({
      title: "Re-tag test cases",
      body,
      confirmLabel: "Apply tags",
      onConfirm: async ({ close }) => {
        errEl.classList.add("hidden");
        const { tags, invalid } = _tmsParseTags(input.value);
        if (invalid.length) {
          errEl.textContent =
            "Invalid tag(s): " +
            invalid.join(", ") +
            ". Tags must be non-empty, no whitespace, '@', or ','.";
          errEl.classList.remove("hidden");
          return;
        }
        const fo = await _tmsBulkFanout(paths, async (p) => {
          const feature = await _tmsBulkGet("/api/files/" + p);
          feature.tags = tags;
          await _tmsBulkSend("PATCH", "/api/files/" + p, feature);
        });
        if (fo.length) {
          _tmsBulkShowFailures(errEl, fo);
          return;
        }
        close();
        done();
      },
    });
  },

  // ---- Run (D2: add to an existing run only) --------------------------
  async run(folderPath, paths, done) {
    const project = folderPath.split("/")[0];
    let runs = [];
    try {
      const data = await _tmsBulkGet("/api/runs/" + project);
      runs = data.runs || [];
    } catch (e) {
      alert("Could not load test runs: " + e.message);
      return;
    }
    if (!runs.length) {
      tmsOpenModal({
        title: "Add to test run",
        body:
          "This project has no test runs yet. Create a run first, then add cases to it.",
        confirmLabel: null,
      });
      return;
    }

    const select = document.createElement("select");
    select.className =
      "w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white";
    runs.forEach((run, i) => {
      const opt = document.createElement("option");
      opt.value = String(i);
      opt.textContent = run.group + " / " + run.name;
      select.appendChild(opt);
    });

    const body = document.createElement("div");
    const label = document.createElement("p");
    label.className = "text-sm text-slate-600 mb-2";
    label.textContent = "Add " + paths.length + " test case(s) to run:";
    const errEl = _tmsBulkErrEl();
    body.appendChild(label);
    body.appendChild(select);
    body.appendChild(errEl);

    tmsOpenModal({
      title: "Add to test run",
      body,
      confirmLabel: "Add to run",
      onConfirm: async ({ close }) => {
        errEl.classList.add("hidden");
        const picked = runs[Number(select.value)];
        if (!picked) return;
        const base =
          "/api/runs/" + project + "/" + picked.group + "/" + picked.file_name;
        // Pre-flight: de-dup against the run's current cases.
        let inRun = new Set();
        try {
          const run = await _tmsBulkGet(base);
          inRun = new Set((run.results || []).map((r) => r.file_path));
        } catch (e) {
          errEl.textContent = "Could not verify the run: " + e.message;
          errEl.classList.remove("hidden");
          return;
        }
        const failures = paths
          .filter((p) => inRun.has(p))
          .map((p) => ({ path: p, reason: "already in this run" }));
        if (failures.length) {
          _tmsBulkShowFailures(errEl, failures);
          return;
        }
        const fo = await _tmsBulkFanout(paths, (p) =>
          _tmsBulkSend("POST", base + "/cases", { file_path: p })
        );
        if (fo.length) {
          _tmsBulkShowFailures(errEl, fo);
          return;
        }
        close();
        done();
      },
    });
  },
};

function _tmsBulkRefresh(folderPath) {
  tmsRefreshFolder(folderPath);
  tmsRefreshTreePane("tree-pane");
}

function tmsBulkBind(root) {
  const folderPath = root.getAttribute("data-folder-path");
  const selectAll = root.querySelector('[data-role="select-all"]');
  const rowBoxes = Array.from(root.querySelectorAll('[data-role="select"]'));
  const countEl = root.querySelector('[data-role="count"]');
  const actionBtns = Array.from(root.querySelectorAll("[data-bulk-action]"));
  if (!selectAll || !countEl) return;

  const selected = () =>
    rowBoxes.filter((b) => b.checked).map((b) => b.getAttribute("data-case-path"));

  const update = () => {
    const n = rowBoxes.filter((b) => b.checked).length;
    countEl.textContent = n + " selected";
    actionBtns.forEach((b) => {
      b.disabled = n === 0;
    });
    selectAll.checked = n > 0 && n === rowBoxes.length;
    selectAll.indeterminate = n > 0 && n < rowBoxes.length;
  };

  selectAll.addEventListener("change", () => {
    rowBoxes.forEach((b) => {
      b.checked = selectAll.checked;
    });
    update();
  });
  rowBoxes.forEach((b) => b.addEventListener("change", update));
  actionBtns.forEach((btn) =>
    btn.addEventListener("click", () => {
      const action = btn.getAttribute("data-bulk-action");
      const paths = selected();
      if (!paths.length) return;
      const fn = tmsBulkActions[action];
      if (fn) fn(folderPath, paths, () => _tmsBulkRefresh(folderPath));
    })
  );
  update();
}

// Idempotent scan: bind any unbound bulk-root. The `data-bulk-bound` guard
// makes this safe to call on every swap (a replaced #main-pane yields a
// fresh, unbound root; an untouched root is skipped).
function tmsBulkScan() {
  document
    .querySelectorAll("[data-bulk-root]:not([data-bulk-bound])")
    .forEach((root) => {
      root.setAttribute("data-bulk-bound", "1");
      tmsBulkBind(root);
    });
}

// Bind on htmx:load (fires for each swapped-in content block — covers
// folder navigation and tmsRefreshFolder) plus the initial DOMContentLoaded.
// NOT htmx:afterSwap: the editor / tree / run-editor wiring smokes assume a
// single body-level afterSwap listener, and the data-bulk-bound guard already
// makes htmx:load sufficient + idempotent.
document.addEventListener("DOMContentLoaded", tmsBulkScan);
document.body.addEventListener("htmx:load", tmsBulkScan);
