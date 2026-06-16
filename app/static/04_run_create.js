// -----------------------------------------------------------------------
// Test-run create flow — relocated to the Test-run sidebar tab as part
// of the "Relocate + simplify the + New run flow" change (see
// DONE.md § Should have).
//
// `tmsCreateRun()` (no args) is wired to the sidebar header button. It
// is always callable: it fetches /api/run-groups, then opens a modal
// in one of two shapes.
//
//   - Zero-projects branch (projects: []): a single info message
//     "No projects yet — create one first." and a Cancel-only footer
//     (Confirm button suppressed via tmsOpenModal({ confirmLabel: null })).
//
//   - Base shape: two visible fields.
//       * Where — <select> with one <optgroup label="proj"> per project
//         that has groups, listing each group as an <option value="proj|grp">.
//         A trailing non-grouped <option value="__new__"> reveals an
//         inline sub-form (project <select> of all existing projects +
//         free-text group name input).
//       * Run name — <input>, plus a live slug preview "will save as
//         <slug>.yaml" so silent slug collisions surface before submit.
//
// On confirm:
//   1. If a new group was chosen, POST /api/runs/<project>/groups first;
//      a 409 surfaces inline under the group-name input (uniqueness
//      within project is enforced by Storage.create_run_group).
//   2. POST /api/runs with case_paths=[] and description=""; a 409
//      surfaces inline under the run-name input (uniqueness within
//      group is enforced by Storage.create_run).
//   3. On success, the modal closes and the main pane is navigated to
//      /ui/run/<project>/<group>/<file_name>.yaml so the user can fill
//      in description / add cases / set results in the editor.
//
// The case-picker helpers (tmsSlugifyForFilename, tmsFetchProjectFeaturePaths,
// tmsBuildCasePicker) are kept because the run editor's "+ Add test case"
// modal still uses them; only `tmsCreateRun` itself was rewritten.
// -----------------------------------------------------------------------

/**
 * Derive a YAML filename stem from a human run name.
 *
 * Rules (kept deliberately simple — the server's `_validate_segment` is
 * the source of truth; this is only a UX convenience):
 *   - Lowercase.
 *   - Whitespace collapses to single hyphens.
 *   - Strip anything that isn't [a-z0-9_-].
 *   - Trim leading / trailing hyphens.
 * The server appends `.yaml` automatically (see `_normalize_run_filename`).
 */
function tmsSlugifyForFilename(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9_-]+/g, "")
    .replace(/^-+|-+$/g, "");
}

/**
 * Fetch the full directory tree from /api/tree and return a flat array
 * of {path, file_name, folder_path, rel_path, rel_folder} for every
 * .feature file under the given project, sorted by folder_path ASC then
 * file_name ASC. `path`/`folder_path` are full (from the data root) and
 * used as stored values; `rel_path`/`rel_folder` drop the redundant
 * `<project>/` prefix for display (the project is already chosen in the
 * modal). A file directly under the project root has `rel_folder === ""`.
 */
async function tmsFetchProjectFeaturePaths(project) {
  const r = await fetch("/api/tree", { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error("Could not load tree: " + r.statusText);
  const tree = await r.json();
  const projectNode = (tree.children || []).find(
    (c) => c.type === "folder" && c.name === project
  );
  if (!projectNode) return [];
  const prefix = project + "/";
  const out = [];
  const walk = (node) => {
    if (!node) return;
    if (node.type === "feature") {
      const path = node.path;
      const slash = path.lastIndexOf("/");
      const folder_path = slash === -1 ? "" : path.slice(0, slash);
      out.push({
        path,
        file_name: slash === -1 ? path : path.slice(slash + 1),
        folder_path,
        rel_path: path.startsWith(prefix) ? path.slice(prefix.length) : path,
        rel_folder:
          folder_path === project
            ? ""
            : folder_path.startsWith(prefix)
            ? folder_path.slice(prefix.length)
            : folder_path,
      });
    } else if (Array.isArray(node.children)) {
      for (const c of node.children) walk(c);
    }
  };
  walk(projectNode);
  out.sort((a, b) => {
    if (a.folder_path !== b.folder_path) {
      return a.folder_path < b.folder_path ? -1 : 1;
    }
    return a.file_name < b.file_name ? -1 : a.file_name > b.file_name ? 1 : 0;
  });
  return out;
}

/**
 * Build a flat checkbox table picker for .feature files.
 *
 * @param {{path: string, file_name: string, folder_path: string}[]} features
 * @param {object} [opts]
 * @param {Set<string>} [opts.exclude] Paths to filter OUT (already-included).
 * @param {() => void} [opts.onChange] Called after every selection change.
 *
 * @returns {{
 *   node: HTMLElement,
 *   getSelected: () => string[],
 *   countVisible: () => number,
 * }}
 */
function tmsBuildCasePicker(features, opts = {}) {
  const exclude = opts.exclude instanceof Set ? opts.exclude : new Set();
  const visible = features.filter((f) => !exclude.has(f.path));

  const wrap = document.createElement("div");
  wrap.className = "border border-slate-200 rounded bg-white";

  const head = document.createElement("div");
  head.className = "px-2 py-2 border-b border-slate-200 flex items-center gap-2";
  head.innerHTML =
    '<input type="search" data-role="case-filter" placeholder="Filter cases\u2026" autocomplete="off"' +
    ' class="flex-1 border border-slate-300 rounded px-2 py-1 text-sm" />' +
    '<span data-role="case-count" class="text-xs text-slate-500"></span>';
  wrap.appendChild(head);

  const scroll = document.createElement("div");
  scroll.className = "max-h-72 overflow-auto";
  wrap.appendChild(scroll);

  const table = document.createElement("table");
  table.className = "w-full text-sm";
  table.innerHTML =
    '<thead class="bg-slate-50 text-slate-600 sticky top-0">' +
    "  <tr>" +
    '    <th class="text-left px-2 py-1.5 font-medium w-8">' +
    '      <input type="checkbox" data-role="select-all" aria-label="Select all visible" class="rounded border-slate-300" />' +
    '    </th>' +
    '    <th class="text-left px-2 py-1.5 font-medium">Folder</th>' +
    '    <th class="text-left px-2 py-1.5 font-medium">File</th>' +
    "  </tr>" +
    "</thead>";
  const tbody = document.createElement("tbody");
  table.appendChild(tbody);
  scroll.appendChild(table);

  // Empty-state row when nothing is available (project has no features,
  // or all features are already in the run). When the table is replaced
  // by the empty-state div, `headerBox` stays null so every header-state
  // helper short-circuits via its early-return guard.
  let headerBox = null;
  if (visible.length === 0) {
    const empty = document.createElement("div");
    empty.className = "px-3 py-6 text-center text-slate-400 italic text-sm";
    empty.textContent =
      features.length === 0
        ? "No .feature files in this project yet."
        : "All test cases are already in this run.";
    scroll.innerHTML = "";
    scroll.appendChild(empty);
  } else {
    for (const f of visible) {
      const tr = document.createElement("tr");
      tr.className = "border-t border-slate-100 hover:bg-slate-50";
      const relFolder = f.rel_folder != null ? f.rel_folder : f.folder_path;
      tr.dataset.path = f.path;
      tr.dataset.folder = (relFolder || "").toLowerCase();
      tr.dataset.file = f.file_name.toLowerCase();
      tr.innerHTML =
        '<td class="px-2 py-1.5 align-top">' +
        '  <input type="checkbox" class="rounded border-slate-300" />' +
        "</td>" +
        '<td class="px-2 py-1.5 text-slate-500"></td>' +
        '<td class="px-2 py-1.5 text-slate-800"></td>';
      tr.children[1].textContent = relFolder;
      tr.children[2].textContent = f.file_name;
      tbody.appendChild(tr);
    }
    headerBox = table.querySelector('[data-role="select-all"]');
  }

  const countSpan = head.querySelector('[data-role="case-count"]');
  const filterInput = head.querySelector('[data-role="case-filter"]');

  const updateCount = () => {
    const checked = tbody.querySelectorAll('input[type="checkbox"]:checked').length;
    countSpan.textContent =
      checked === 0
        ? `${visible.length} cases`
        : `${checked} of ${visible.length} selected`;
  };

  // Refresh the header's tri-state to reflect the currently-visible rows.
  // Hidden-but-checked rows are intentionally excluded so the header always
  // describes what "select all" would act on. When no rows are visible
  // (filter matched nothing, or empty-state) the header resets to a plain
  // unchecked state; clicking it then is a self-correcting no-op.
  const _refreshHeaderState = () => {
    if (!headerBox) return;
    const total = tbody.querySelectorAll('tr:not(.hidden)').length;
    const sel = tbody.querySelectorAll(
      'tr:not(.hidden) input[type="checkbox"]:checked'
    ).length;
    headerBox.checked = total > 0 && sel === total;
    headerBox.indeterminate = total > 0 && sel > 0 && sel < total;
  };
  updateCount();
  _refreshHeaderState();

  tbody.addEventListener("change", (e) => {
    if (e.target.matches('input[type="checkbox"]')) {
      updateCount();
      opts.onChange?.();
      _refreshHeaderState();
    }
  });

  // Click anywhere on the row to toggle (cheaper than clicking the box).
  tbody.addEventListener("click", (e) => {
    if (e.target.tagName === "INPUT") return;
    const tr = e.target.closest("tr");
    if (!tr) return;
    const box = tr.querySelector('input[type="checkbox"]');
    if (!box) return;
    box.checked = !box.checked;
    updateCount();
    opts.onChange?.();
    _refreshHeaderState();
  });

  filterInput.addEventListener("input", () => {
    const q = filterInput.value.trim().toLowerCase();
    let shown = 0;
    for (const tr of tbody.children) {
      const hit =
        !q || tr.dataset.folder.includes(q) || tr.dataset.file.includes(q);
      tr.classList.toggle("hidden", !hit);
      if (hit) shown += 1;
    }
    // Update the count to reflect the filter without changing selection.
    const checked = tbody.querySelectorAll('input[type="checkbox"]:checked').length;
    countSpan.textContent =
      q && shown !== visible.length
        ? `${shown} shown · ${checked} selected`
        : checked === 0
        ? `${visible.length} cases`
        : `${checked} of ${visible.length} selected`;
    _refreshHeaderState();
  });

  // Header select-all: bulk-toggles every currently-visible row to match
  // the header's new checked state, then recomputes header state. Hidden
  // selections are preserved across this operation by design (see spec
  // 10 § Case picker). Listener is attached only when the header exists
  // (i.e. the non-empty-state path).
  if (headerBox) {
    headerBox.addEventListener("change", () => {
      const target = headerBox.checked;
      for (const tr of tbody.querySelectorAll('tr:not(.hidden)')) {
        const box = tr.querySelector('input[type="checkbox"]');
        if (box) box.checked = target;
      }
      updateCount();
      opts.onChange?.();
      _refreshHeaderState();
    });
  }

  return {
    node: wrap,
    getSelected: () =>
      Array.from(tbody.querySelectorAll('input[type="checkbox"]:checked'))
        .map((box) => box.closest("tr").dataset.path),
    countVisible: () => visible.length,
  };
}

/**
 * Open the "+ New run" modal (no arguments).
 *
 * Wired to the sidebar header button. Fetches /api/run-groups, then
 * renders one of two modal shapes. See the section header above for
 * the full state machine + payload contract.
 */
async function tmsCreateRun() {
  // 1. Fetch projects + existing groups in one round trip.
  let projects, groups;
  try {
    const r = await fetch("/api/run-groups", {
      headers: { Accept: "application/json" },
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    ({ projects, groups } = await r.json());
  } catch (e) {
    alert("Could not load run groups: " + e.message);
    return;
  }

  // 2. Zero-projects branch — information-only modal.
  if (!projects || projects.length === 0) {
    const body = document.createElement("div");
    body.innerHTML =
      '<p class="text-sm text-slate-700">No projects yet — create one first.</p>';
    tmsOpenModal({
      title: "Create test run",
      body,
      confirmLabel: null,
    });
    return;
  }

  // 3. Base modal body.
  const body = document.createElement("div");
  body.innerHTML =
    '<label class="block text-sm text-slate-600 mb-1" for="tms-cr-where">Where</label>' +
    '<select id="tms-cr-where"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>' +
    '<p data-role="where-error" class="hidden mt-1 text-xs text-rose-600"></p>' +
    '<div id="tms-cr-newgroup" class="hidden mt-3 space-y-2 pl-3 border-l-2 border-slate-100">' +
    '  <div>' +
    '    <label class="block text-sm text-slate-600 mb-1" for="tms-cr-newproj">Project</label>' +
    '    <select id="tms-cr-newproj"' +
    '      class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>' +
    '  </div>' +
    '  <div>' +
    '    <label class="block text-sm text-slate-600 mb-1" for="tms-cr-newgrp">Group name</label>' +
    '    <input id="tms-cr-newgrp" type="text" autocomplete="off"' +
    '      class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '    <p data-role="group-error" class="hidden mt-1 text-xs text-rose-600"></p>' +
    '  </div>' +
    '</div>' +
    '<label class="block text-sm text-slate-600 mt-3 mb-1" for="tms-cr-name">Run name</label>' +
    '<input id="tms-cr-name" type="text" autocomplete="off"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '<p data-role="slug-preview" class="mt-1 text-xs text-slate-500"></p>' +
    '<p data-role="name-error" class="hidden mt-1 text-xs text-rose-600"></p>';

  const whereSel = body.querySelector("#tms-cr-where");
  const newGroupBlock = body.querySelector("#tms-cr-newgroup");
  const newProjSel = body.querySelector("#tms-cr-newproj");
  const newGrpInput = body.querySelector("#tms-cr-newgrp");
  const nameInput = body.querySelector("#tms-cr-name");
  const slugPreview = body.querySelector('[data-role="slug-preview"]');
  const whereError = body.querySelector('[data-role="where-error"]');
  const groupError = body.querySelector('[data-role="group-error"]');
  const nameError = body.querySelector('[data-role="name-error"]');

  // 4. Populate the "Where" <select> with one <optgroup> per project
  //    that has groups; bare projects are reachable via the new-group
  //    sub-select so they don't need an empty <optgroup> here.
  const byProj = new Map();
  for (const g of groups || []) {
    if (!byProj.has(g.project)) byProj.set(g.project, []);
    byProj.get(g.project).push(g.group);
  }
  let firstExistingVal = "";
  for (const [proj, gs] of byProj) {
    const og = document.createElement("optgroup");
    og.label = proj;
    for (const grp of gs) {
      const opt = document.createElement("option");
      opt.value = proj + "|" + grp;
      opt.textContent = grp;
      og.appendChild(opt);
      if (!firstExistingVal) firstExistingVal = opt.value;
    }
    whereSel.appendChild(og);
  }
  const newOpt = document.createElement("option");
  newOpt.value = "__new__";
  newOpt.textContent = "+ Create new group\u2026";
  whereSel.appendChild(newOpt);
  whereSel.value = firstExistingVal || "__new__";

  // 5. Populate the new-group project sub-select with every project
  //    (including those that have no test-run/ folder yet — storage
  //    lazy-creates the area on the first POST).
  for (const p of projects) {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    newProjSel.appendChild(opt);
  }

  // 6. Confirm-button gating helper. Forward-declared so the listeners
  //    below can call it before modalRef is wired.
  let modalRef = null;
  const refreshGate = () => {
    if (!modalRef) return;
    const nameOk = tmsSlugifyForFilename(nameInput.value).length > 0;
    let pathOk;
    if (whereSel.value === "__new__") {
      pathOk =
        newProjSel.value.length > 0 && newGrpInput.value.trim().length > 0;
    } else {
      pathOk = whereSel.value.length > 0 && whereSel.value !== "__new__";
    }
    modalRef.setConfirmDisabled(!(nameOk && pathOk));
  };

  // 7. Reveal-on-select toggling for the new-group sub-form.
  const updateNewGroupVisibility = () => {
    const isNew = whereSel.value === "__new__";
    newGroupBlock.classList.toggle("hidden", !isNew);
    if (isNew) groupError.classList.add("hidden");
    refreshGate();
  };

  // 8. Live slug preview under the run-name input.
  const updateSlugPreview = () => {
    nameError.classList.add("hidden");
    const slug = tmsSlugifyForFilename(nameInput.value);
    slugPreview.textContent = slug
      ? `will save as ${slug}.yaml`
      : "(enter a name to see the file name)";
    refreshGate();
  };

  whereSel.addEventListener("change", updateNewGroupVisibility);
  newProjSel.addEventListener("change", refreshGate);
  newGrpInput.addEventListener("input", () => {
    groupError.classList.add("hidden");
    refreshGate();
  });
  nameInput.addEventListener("input", updateSlugPreview);

  // 9. Open the modal. Submit handler issues a conditional group POST
  //    then the run POST, surfacing 409s inline next to the offending
  //    input. On success, the run editor opens in the main pane.
  modalRef = tmsOpenModal({
    title: "Create test run",
    body,
    confirmLabel: "Create",
    confirmDisabled: true,
    onConfirm: async ({ close }) => {
      whereError.classList.add("hidden");
      groupError.classList.add("hidden");
      nameError.classList.add("hidden");

      const isNew = whereSel.value === "__new__";
      let project, group;
      if (isNew) {
        project = newProjSel.value;
        group = newGrpInput.value.trim();
      } else {
        [project, group] = whereSel.value.split("|");
      }
      const name = nameInput.value.trim();
      const file_name = tmsSlugifyForFilename(name);
      if (!project || !group || !name || !file_name) return;

      // 9a. Create the group first when needed; preserve the user's
      //     other inputs on failure so they can correct just the name.
      if (isNew) {
        try {
          await tmsApiPost(
            `/api/runs/${encodeURIComponent(project)}/groups`,
            { name: group }
          );
        } catch (e) {
          groupError.textContent =
            /already exists/i.test(e.message)
              ? "Group already exists in this project."
              : e.message;
          groupError.classList.remove("hidden");
          return;
        }
      }

      // 9b. Create the run. case_paths starts empty; the user adds
      //     cases in the run editor afterwards.
      try {
        await tmsApiPost("/api/runs", {
          project,
          group,
          name,
          file_name,
          case_paths: [],
          description: "",
        });
      } catch (e) {
        nameError.textContent =
          /already exists/i.test(e.message)
            ? "A run with this name already exists in this group."
            : e.message;
        nameError.classList.remove("hidden");
        return;
      }

      // 9c. Success: close and open the run editor.
      close();
      tmsRefreshTreePane("test-run-pane"); // E5: show the new run in the tree
      htmx.ajax(
        "GET",
        `/ui/run/${project}/${group}/${file_name}.yaml`,
        { target: "#main-pane", swap: "innerHTML" }
      );
    },
  });

  // 10. Initial render: sync reveal-on-select state, render slug hint,
  //     and focus the most useful input.
  updateNewGroupVisibility();
  updateSlugPreview();
  setTimeout(() => {
    if (whereSel.value === "__new__") newGrpInput.focus();
    else nameInput.focus();
  }, 0);
}


// ===========================================================================
// Import test run (feature-15)
// ---------------------------------------------------------------------------
// Top-bar launcher (wired via `onclick="tmsImportRun()"` in base.html, beside
// "Import test cases"). Uploads an Allure 2 single-file HTML report, previews
// each scenario's resolution against the chosen project's cases, and on
// confirm writes ONE run .yaml with per-case results.
//
// Structural sibling of `tmsImportFile` (03_folder_actions.js) for the modal /
// preview / error shell, and of `tmsCreateRun` (above) for the /api/run-groups
// destination picker + success "open the run" landing. Two deliberate deltas:
//   - The uploaded report is transient: parsed in-memory only, never stored.
//     On success the file input + cached html are cleared client-side.
//   - HTTP uses raw `fetch` (NOT tmsApiPost) so the all-or-nothing 422's
//     `error.details.reasons` survive to the per-line error list.
// ===========================================================================
async function tmsImportRun() {
  // 1. Fetch projects + existing run groups (same source as tmsCreateRun).
  let projects, groups;
  try {
    const r = await fetch("/api/run-groups", {
      headers: { Accept: "application/json" },
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    ({ projects, groups } = await r.json());
  } catch (e) {
    alert("Could not load run groups: " + e.message);
    return;
  }

  // 2. Zero-groups branch — info-only modal (IR-6: no "+ create group" row).
  if (!groups || groups.length === 0) {
    const info = document.createElement("div");
    info.innerHTML =
      '<p class="text-sm text-slate-700">No run groups yet — create one first.</p>';
    tmsOpenModal({ title: "Import test run", body: info, confirmLabel: null });
    return;
  }

  // 3. Modal body.
  const body = document.createElement("div");
  body.innerHTML =
    '<label class="block text-sm text-slate-600 mb-1" for="tms-ir-where">Where</label>' +
    '<select id="tms-ir-where"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>' +
    '<div class="grid grid-cols-2 gap-3 mt-3">' +
    '  <div>' +
    '    <label class="block text-sm text-slate-600 mb-1" for="tms-ir-name">Run name</label>' +
    '    <input id="tms-ir-name" type="text" autocomplete="off"' +
    '      class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '  </div>' +
    '  <div>' +
    '    <label class="block text-sm text-slate-600 mb-1" for="tms-ir-filename">Run file name</label>' +
    '    <input id="tms-ir-filename" type="text" autocomplete="off"' +
    '      class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '    <p data-role="filename-hint" class="mt-1 text-xs text-slate-500"></p>' +
    '  </div>' +
    '</div>' +
    '<label class="block text-sm text-slate-600 mt-3 mb-1" for="tms-ir-desc">Run description (optional)</label>' +
    '<textarea id="tms-ir-desc" rows="2"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></textarea>' +
    '<label class="block text-sm text-slate-600 mt-3 mb-1" for="tms-ir-file">Allure HTML report</label>' +
    '<input id="tms-ir-file" type="file" accept=".html,.htm"' +
    ' class="w-full text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-4 file:rounded file:border-2 file:border-slate-400 file:bg-slate-100 file:text-slate-700 file:text-sm file:font-semibold hover:file:bg-slate-200 hover:file:border-slate-500 file:cursor-pointer" />' +
    '<p class="text-xs text-slate-400 mt-1">One Allure single-file report, max 30 MB. The report is parsed in-memory and never stored.</p>' +
    '<div data-role="preview" class="mt-3"></div>' +
    '<p data-role="error" class="hidden mt-2 text-sm text-red-600"></p>';

  const whereSel = body.querySelector("#tms-ir-where");
  const nameInput = body.querySelector("#tms-ir-name");
  const fileNameInput = body.querySelector("#tms-ir-filename");
  const fileNameHint = body.querySelector('[data-role="filename-hint"]');
  const descInput = body.querySelector("#tms-ir-desc");
  const fileInput = body.querySelector("#tms-ir-file");
  const previewBox = body.querySelector('[data-role="preview"]');
  const error = body.querySelector('[data-role="error"]');

  // Preview state captured for the commit step. `reportHtml` is the transient
  // report text; it is cleared after a successful commit (never retained).
  let reportHtml = "";
  let scenarios = [];
  let blockingErrors = [];
  let modalRef = null;

  // 4. Populate the "Where" <select> with one <optgroup> per project.
  const byProj = new Map();
  for (const g of groups) {
    if (!byProj.has(g.project)) byProj.set(g.project, []);
    byProj.get(g.project).push(g.group);
  }
  let firstVal = "";
  for (const [proj, gs] of byProj) {
    const og = document.createElement("optgroup");
    og.label = proj;
    for (const grp of gs) {
      const opt = document.createElement("option");
      opt.value = proj + "|" + grp;
      opt.textContent = grp;
      og.appendChild(opt);
      if (!firstVal) firstVal = opt.value;
    }
    whereSel.appendChild(og);
  }
  whereSel.value = firstVal;

  const showError = (msg, reasons) => {
    error.innerHTML = "";
    const head = document.createElement("div");
    head.textContent = msg;
    error.appendChild(head);
    if (reasons && reasons.length) {
      const ul = document.createElement("ul");
      ul.className = "list-disc ml-5 mt-1";
      for (const rsn of reasons) {
        const li = document.createElement("li");
        li.textContent = rsn;
        ul.appendChild(li);
      }
      error.appendChild(ul);
    }
    error.classList.remove("hidden");
  };

  // Mirror the server's `_normalize_run_filename` (append .yaml when absent)
  // so the success "open the run" URL matches the file actually written.
  const runLeaf = () => {
    const fn = fileNameInput.value.trim();
    return /\.yaml$/i.test(fn) ? fn : fn + ".yaml";
  };

  const updateFileNameHint = () => {
    const fn = fileNameInput.value.trim();
    fileNameHint.textContent = fn
      ? `will save as ${runLeaf()}`
      : "(enter a file name)";
    refreshGate();
  };

  const refreshGate = () => {
    if (!modalRef) return;
    const whereOk = !!whereSel.value;
    const nameOk = nameInput.value.trim().length > 0;
    const fileNameOk = fileNameInput.value.trim().length > 0;
    const previewOk = scenarios.length > 0 && blockingErrors.length === 0;
    modalRef.setConfirmDisabled(
      !(whereOk && nameOk && fileNameOk && previewOk)
    );
  };

  const renderPreview = () => {
    previewBox.innerHTML = "";
    if (!scenarios.length) return;
    const header = document.createElement("p");
    header.className = "text-sm text-slate-600 mb-2";
    header.textContent = scenarios.length + " scenario(s) in the report:";
    previewBox.appendChild(header);

    const scroll = document.createElement("div");
    scroll.className =
      "border border-slate-200 rounded max-h-72 overflow-auto";
    const table = document.createElement("table");
    table.className = "w-full text-sm";
    table.innerHTML =
      '<thead class="bg-slate-50 text-slate-600 sticky top-0">' +
      "  <tr>" +
      '    <th class="text-left px-2 py-1.5 font-medium">#</th>' +
      '    <th class="text-left px-2 py-1.5 font-medium">Scenario</th>' +
      '    <th class="text-left px-2 py-1.5 font-medium">Result</th>' +
      '    <th class="text-left px-2 py-1.5 font-medium">Matched case</th>' +
      "  </tr>" +
      "</thead>";
    const tbody = document.createElement("tbody");
    table.appendChild(tbody);

    scenarios.forEach((sc) => {
      const tr = document.createElement("tr");
      tr.className = "border-t border-slate-100";
      const blocked = sc.match !== "matched";
      if (blocked) tr.className += " bg-rose-50";

      const noTd = document.createElement("td");
      noTd.className = "px-2 py-1.5 text-slate-400";
      noTd.textContent = sc.no;

      const nameTd = document.createElement("td");
      nameTd.className = "px-2 py-1.5 text-slate-800";
      const full = sc.name || "(unnamed scenario)";
      nameTd.textContent = full.length > 40 ? full.slice(0, 40) + "…" : full;
      nameTd.title = full;

      const resTd = document.createElement("td");
      resTd.className = "px-2 py-1.5 text-slate-600 whitespace-nowrap";
      resTd.textContent = sc.result;

      const matchTd = document.createElement("td");
      matchTd.className = "px-2 py-1.5 whitespace-nowrap";
      if (sc.match === "matched") {
        matchTd.className += " text-slate-500";
        matchTd.textContent = sc.file_path;
        matchTd.title = sc.file_path;
      } else {
        matchTd.className += " text-rose-600";
        matchTd.textContent = sc.match === "ambiguous" ? "ambiguous" : "no match";
      }

      tr.appendChild(noTd);
      tr.appendChild(nameTd);
      tr.appendChild(resTd);
      tr.appendChild(matchTd);
      tbody.appendChild(tr);
    });

    scroll.appendChild(table);
    previewBox.appendChild(scroll);
  };

  const resetPreview = () => {
    reportHtml = "";
    scenarios = [];
    blockingErrors = [];
    previewBox.innerHTML = "";
    error.classList.add("hidden");
    refreshGate();
  };

  // Preview runs on file change AND on project change (resolution is
  // project-scoped, so switching "Where" re-resolves the same report).
  const runPreview = async () => {
    resetPreview();
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;
    if (!/\.html?$/i.test(file.name)) {
      showError("Please choose an .html report.");
      return;
    }
    if (file.size > 30 * 1024 * 1024) {
      showError("Report exceeds the 30 MB limit.");
      return;
    }
    const project = (whereSel.value || "").split("|")[0];
    if (!project) return;
    let text;
    try {
      text = await file.text();
    } catch (_) {
      showError("Could not read the file.");
      return;
    }
    let data;
    try {
      const r = await fetch("/api/runs/import/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project, html: text }),
      });
      data = await r.json();
      if (!r.ok) {
        const err = data.error || {};
        showError(
          err.message || r.statusText,
          err.details && err.details.reasons
        );
        return;
      }
    } catch (e) {
      showError(e.message);
      return;
    }
    reportHtml = text;
    scenarios = data.scenarios || [];
    blockingErrors = data.errors || [];
    if (!scenarios.length) {
      showError("No scenarios found to import.");
      return;
    }
    renderPreview();
    if (blockingErrors.length) {
      showError(
        "Some scenarios cannot be imported — every scenario must match exactly one case:",
        blockingErrors
      );
    }
    refreshGate();
  };

  fileInput.addEventListener("change", runPreview);
  whereSel.addEventListener("change", runPreview);
  nameInput.addEventListener("input", refreshGate);
  fileNameInput.addEventListener("input", updateFileNameHint);

  // 5. Open the modal. Confirm re-validates server-side (preview is advisory).
  modalRef = tmsOpenModal({
    title: "Import test run",
    body,
    confirmLabel: "Import",
    confirmDisabled: true,
    size: "xl",
    onConfirm: async ({ close }) => {
      error.classList.add("hidden");
      const [project, group] = (whereSel.value || "").split("|");
      const name = nameInput.value.trim();
      const file_name = fileNameInput.value.trim();
      const description = descInput.value.trim();
      if (
        !project ||
        !group ||
        !name ||
        !file_name ||
        !scenarios.length ||
        blockingErrors.length
      ) {
        return;
      }
      let data;
      try {
        const r = await fetch("/api/runs/import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project,
            group,
            name,
            file_name,
            description,
            html: reportHtml,
          }),
        });
        data = await r.json();
        if (!r.ok) {
          const err = data.error || {};
          showError(
            err.message || r.statusText,
            err.details && err.details.reasons
          );
          return;
        }
      } catch (e) {
        showError(e.message);
        return;
      }
      // Success: the report is not retained — clear the file input + cached
      // html, then open the new run by default in the main pane.
      const leaf = runLeaf();
      fileInput.value = "";
      reportHtml = "";
      close();
      tmsRefreshTreePane("test-run-pane");
      htmx.ajax(
        "GET",
        "/ui/run/" +
          encodeURIComponent(project) +
          "/" +
          encodeURIComponent(group) +
          "/" +
          encodeURIComponent(leaf),
        { target: "#main-pane", swap: "innerHTML" }
      );
    },
  });

  updateFileNameHint();
  setTimeout(() => nameInput.focus(), 0);
}

