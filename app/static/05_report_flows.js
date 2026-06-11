// -----------------------------------------------------------------------
// Quality reports — create flow + run picker (S3 of
// `12-feature-quality-report-NEW.md`).
//
// `tmsCreateReport()` (no args) is wired to the Reports sidebar header.
// It fetches the project list, then opens a modal whose config section
// re-renders per chosen type. `tmsBuildRunPicker` is the run analogue of
// `tmsBuildCasePicker`; `tmsAddReportRuns` re-opens it for the detail
// view's "+ Add runs" action and PATCHes the report's run_paths.
// -----------------------------------------------------------------------

/**
 * Build a flat checkbox table picker for test runs (run analogue of
 * tmsBuildCasePicker). `runs` come from GET /api/runs/<project>.
 *
 * @param {{path,group,file_name,name,created_at}[]} runs
 * @param {object} [opts]
 * @param {Set<string>} [opts.selected] Paths pre-checked on render.
 * @param {() => void} [opts.onChange]
 * @returns {{node:HTMLElement, getSelected:()=>string[], countVisible:()=>number}}
 */
function tmsBuildRunPicker(runs, opts = {}) {
  const selected = opts.selected instanceof Set ? opts.selected : new Set();

  const wrap = document.createElement("div");
  wrap.className = "border border-slate-200 rounded bg-white";

  const head = document.createElement("div");
  head.className = "px-2 py-2 border-b border-slate-200 flex items-center gap-2";
  head.innerHTML =
    '<input type="search" data-role="run-filter" placeholder="Filter runs\u2026" autocomplete="off"' +
    ' class="flex-1 border border-slate-300 rounded px-2 py-1 text-sm" />' +
    '<span data-role="run-count" class="text-xs text-slate-500"></span>';
  wrap.appendChild(head);

  const scroll = document.createElement("div");
  scroll.className = "max-h-64 overflow-auto";
  wrap.appendChild(scroll);

  const table = document.createElement("table");
  table.className = "w-full text-sm";
  table.innerHTML =
    '<thead class="bg-slate-50 text-slate-600 sticky top-0"><tr>' +
    '<th class="text-left px-2 py-1.5 font-medium w-8"></th>' +
    '<th class="text-left px-2 py-1.5 font-medium">Run</th>' +
    '<th class="text-left px-2 py-1.5 font-medium">Group</th>' +
    '<th class="text-left px-2 py-1.5 font-medium">Created</th>' +
    "</tr></thead>";
  const tbody = document.createElement("tbody");
  table.appendChild(tbody);
  scroll.appendChild(table);

  if (runs.length === 0) {
    const empty = document.createElement("div");
    empty.className = "px-3 py-6 text-center text-slate-400 italic text-sm";
    empty.textContent = "No test runs in this project yet.";
    scroll.innerHTML = "";
    scroll.appendChild(empty);
  } else {
    for (const r of runs) {
      const tr = document.createElement("tr");
      tr.className = "border-t border-slate-100 hover:bg-slate-50";
      tr.dataset.path = r.path;
      tr.dataset.hay = `${r.name} ${r.group} ${r.file_name}`.toLowerCase();
      tr.innerHTML =
        '<td class="px-2 py-1.5 align-top"><input type="checkbox" class="rounded border-slate-300" /></td>' +
        '<td class="px-2 py-1.5 text-slate-800"></td>' +
        '<td class="px-2 py-1.5 text-slate-500"></td>' +
        '<td class="px-2 py-1.5 text-slate-400 text-xs font-mono"></td>';
      tr.children[1].textContent = r.name || r.file_name;
      tr.children[2].textContent = r.group;
      tr.children[3].textContent = r.created_at;
      if (selected.has(r.path)) tr.querySelector("input").checked = true;
      tbody.appendChild(tr);
    }
  }

  const countSpan = head.querySelector('[data-role="run-count"]');
  const filterInput = head.querySelector('[data-role="run-filter"]');
  const updateCount = () => {
    const checked = tbody.querySelectorAll("input:checked").length;
    countSpan.textContent = `${checked} selected \u00b7 max 10`;
  };
  updateCount();

  tbody.addEventListener("change", (e) => {
    if (e.target.matches('input[type="checkbox"]')) {
      updateCount();
      opts.onChange?.();
    }
  });
  tbody.addEventListener("click", (e) => {
    if (e.target.tagName === "INPUT") return;
    const tr = e.target.closest("tr");
    if (!tr) return;
    const box = tr.querySelector("input");
    if (!box) return;
    box.checked = !box.checked;
    updateCount();
    opts.onChange?.();
  });
  filterInput.addEventListener("input", () => {
    const q = filterInput.value.trim().toLowerCase();
    for (const tr of tbody.children) {
      tr.classList.toggle("hidden", !!q && !tr.dataset.hay.includes(q));
    }
  });

  return {
    node: wrap,
    getSelected: () =>
      Array.from(tbody.querySelectorAll("input:checked")).map(
        (b) => b.closest("tr").dataset.path
      ),
    countVisible: () => runs.length,
  };
}

/**
 * Fetch the directory tree and return every folder path under `project`
 * (the project itself plus all sub-folders), used for the tag_inventory
 * scope <select>. Reserved areas (test-run/, report/) are already hidden
 * from /api/tree, so they never appear as scope options.
 */
async function tmsFetchProjectFolderPaths(project) {
  const r = await fetch("/api/tree", { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error("Could not load tree: " + r.statusText);
  const tree = await r.json();
  const node = (tree.children || []).find(
    (c) => c.type === "folder" && c.name === project
  );
  const out = [];
  const walk = (n) => {
    if (!n || n.type !== "folder") return;
    out.push(n.path);
    for (const c of n.children || []) walk(c);
  };
  if (node) walk(node);
  return out;
}

function tmsFillSelect(sel, values, { placeholder } = {}) {
  sel.innerHTML = "";
  if (placeholder) {
    const o = document.createElement("option");
    o.value = "";
    o.textContent = placeholder;
    o.disabled = true;
    o.selected = true;
    sel.appendChild(o);
  }
  for (const v of values) {
    const o = document.createElement("option");
    if (Array.isArray(v)) {
      o.value = v[0];
      o.textContent = v[1];
    } else {
      o.value = v;
      o.textContent = v;
    }
    sel.appendChild(o);
  }
}

async function tmsCreateReport() {
  let projects;
  try {
    const r = await fetch("/api/run-groups", {
      headers: { Accept: "application/json" },
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    ({ projects } = await r.json());
  } catch (e) {
    alert("Could not load projects: " + e.message);
    return;
  }

  if (!projects || projects.length === 0) {
    const body = document.createElement("div");
    body.innerHTML =
      '<p class="text-sm text-slate-700">No projects yet — create one first.</p>';
    tmsOpenModal({ title: "Create report", body, confirmLabel: null });
    return;
  }

  const REPORT_TYPES = [
    ["enum_ranking", "Enum ranking"],
    ["tag_ranking", "Tag ranking"],
    ["case_trend", "Case trend"],
    ["tag_inventory", "Tag inventory"],
  ];
  const RUN_SET = new Set(["enum_ranking", "tag_ranking", "case_trend"]);
  const RESULTS = window.TMS_RUN_RESULTS || ["PENDING", "PASSED", "FAILED"];

  const body = document.createElement("div");
  body.innerHTML =
    '<div class="grid grid-cols-2 gap-3">' +
    '  <div>' +
    '    <label class="block text-sm text-slate-600 mb-1" for="tms-rp-project">Project</label>' +
    '    <select id="tms-rp-project" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>' +
    "  </div>" +
    "  <div>" +
    '    <label class="block text-sm text-slate-600 mb-1" for="tms-rp-type">Type</label>' +
    '    <select id="tms-rp-type" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>' +
    "  </div>" +
    "</div>" +
    '<label class="block text-sm text-slate-600 mt-3 mb-1" for="tms-rp-title">Title</label>' +
    '<input id="tms-rp-title" type="text" autocomplete="off" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '<label class="block text-sm text-slate-600 mt-3 mb-1" for="tms-rp-file">File name</label>' +
    '<input id="tms-rp-file" type="text" autocomplete="off" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '<p data-role="slug-preview" class="mt-1 text-xs text-slate-500"></p>' +
    '<div id="tms-rp-config" class="mt-3 space-y-3"></div>' +
    '<p data-role="error" class="hidden mt-2 text-sm text-rose-600"></p>';

  const projectSel = body.querySelector("#tms-rp-project");
  const typeSel = body.querySelector("#tms-rp-type");
  const titleInput = body.querySelector("#tms-rp-title");
  const fileInput = body.querySelector("#tms-rp-file");
  const slugPreview = body.querySelector('[data-role="slug-preview"]');
  const configHost = body.querySelector("#tms-rp-config");
  const error = body.querySelector('[data-role="error"]');

  tmsFillSelect(projectSel, projects);
  tmsFillSelect(typeSel, REPORT_TYPES);

  // Per-type config widgets are rebuilt on every type/project change.
  // `cfg` exposes a `collect()` returning the type-specific report fields
  // and an optional `runPicker` handle.
  let cfg = { collect: () => ({}), runPicker: null };

  const renderConfig = async () => {
    const type = typeSel.value;
    const project = projectSel.value;
    configHost.innerHTML =
      '<div class="text-xs text-slate-400 italic">Loading options\u2026</div>';

    const frag = document.createElement("div");
    frag.className = "space-y-3";
    const widgets = {};

    if (type === "enum_ranking" || type === "tag_ranking") {
      const d = document.createElement("div");
      d.innerHTML =
        '<label class="block text-sm text-slate-600 mb-1">Status</label>' +
        '<select data-role="status" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>';
      tmsFillSelect(d.querySelector("[data-role=status]"), RESULTS);
      widgets.status = d.querySelector("[data-role=status]");
      frag.appendChild(d);
    }

    if (type === "enum_ranking") {
      const d = document.createElement("div");
      d.innerHTML =
        '<label class="block text-sm text-slate-600 mb-1">Enum kind</label>' +
        '<select data-role="kind" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>' +
        '<p data-role="kind-note" class="hidden mt-1 text-xs text-amber-600"></p>';
      widgets.kind = d.querySelector("[data-role=kind]");
      let kinds = [];
      try {
        const r = await fetch(`/api/enums/${encodeURIComponent(project)}`, {
          headers: { Accept: "application/json" },
        });
        if (r.ok) kinds = Object.keys(await r.json());
      } catch (_) {}
      tmsFillSelect(widgets.kind, kinds, {
        placeholder: kinds.length ? undefined : "(no enums defined)",
      });
      if (!kinds.length) {
        const note = d.querySelector("[data-role=kind-note]");
        note.textContent = "This project has no enums.yaml kinds yet.";
        note.classList.remove("hidden");
      }
      frag.appendChild(d);
    }

    if (type === "case_trend") {
      const d = document.createElement("div");
      d.innerHTML =
        '<label class="block text-sm text-slate-600 mb-1">Test case</label>' +
        '<select data-role="case" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>';
      widgets.caseSel = d.querySelector("[data-role=case]");
      let features = [];
      try {
        features = await tmsFetchProjectFeaturePaths(project);
      } catch (_) {}
      tmsFillSelect(
        widgets.caseSel,
        features.map((f) => [f.path, f.rel_path != null ? f.rel_path : f.path]),
        { placeholder: features.length ? undefined : "(no test cases)" }
      );
      frag.appendChild(d);
    }

    if (type === "tag_inventory") {
      const d = document.createElement("div");
      d.innerHTML =
        '<div class="grid grid-cols-2 gap-3">' +
        "  <div>" +
        '    <label class="block text-sm text-slate-600 mb-1">Tag</label>' +
        '    <input data-role="tag" type="text" autocomplete="off" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" placeholder="smoke" />' +
        "  </div>" +
        "  <div>" +
        '    <label class="block text-sm text-slate-600 mb-1">Scope</label>' +
        '    <select data-role="scope" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>' +
        "  </div>" +
        "</div>";
      widgets.tag = d.querySelector("[data-role=tag]");
      widgets.scope = d.querySelector("[data-role=scope]");
      let folders = [project];
      try {
        const fetched = await tmsFetchProjectFolderPaths(project);
        if (fetched.length) folders = fetched;
      } catch (_) {}
      tmsFillSelect(widgets.scope, folders);
      frag.appendChild(d);
    }

    let runPicker = null;
    if (RUN_SET.has(type)) {
      const label = document.createElement("label");
      label.className = "block text-sm text-slate-600 mb-1";
      label.textContent = "Runs (optional, max 10)";
      let runs = [];
      try {
        const r = await fetch(`/api/runs/${encodeURIComponent(project)}`, {
          headers: { Accept: "application/json" },
        });
        if (r.ok) ({ runs } = await r.json());
      } catch (_) {}
      runPicker = tmsBuildRunPicker(runs);
      const block = document.createElement("div");
      block.appendChild(label);
      block.appendChild(runPicker.node);
      frag.appendChild(block);
    }

    cfg = {
      runPicker,
      collect: () => {
        const out = {};
        if (widgets.status) out.status = widgets.status.value;
        if (widgets.kind) out.kind = widgets.kind.value;
        if (widgets.caseSel) out.case_path = widgets.caseSel.value;
        if (widgets.tag) out.tag = widgets.tag.value.trim();
        if (widgets.scope) out.scope = widgets.scope.value;
        if (runPicker) out.run_paths = runPicker.getSelected();
        return out;
      },
    };

    configHost.innerHTML = "";
    configHost.appendChild(frag);
  };

  const updateSlug = () => {
    const slug = tmsSlugifyForFilename(fileInput.value || titleInput.value);
    slugPreview.textContent = slug
      ? `will save as ${slug}.yaml`
      : "(enter a file name to see the saved file)";
  };

  projectSel.addEventListener("change", renderConfig);
  typeSel.addEventListener("change", renderConfig);
  titleInput.addEventListener("input", updateSlug);
  fileInput.addEventListener("input", updateSlug);

  tmsOpenModal({
    title: "Create report",
    body,
    confirmLabel: "Create",
    size: "lg",
    onConfirm: async ({ close }) => {
      error.classList.add("hidden");
      const project = projectSel.value;
      const type = typeSel.value;
      const title = titleInput.value.trim();
      const file_name = tmsSlugifyForFilename(fileInput.value || titleInput.value);
      if (!project || !title || !file_name) {
        error.textContent = "Project, title, and file name are required.";
        error.classList.remove("hidden");
        return;
      }
      const payload = { file_name, type, title, ...cfg.collect() };
      if (Array.isArray(payload.run_paths) && payload.run_paths.length > 10) {
        error.textContent = "A report may reference at most 10 runs.";
        error.classList.remove("hidden");
        return;
      }
      try {
        await tmsApiPost(`/api/reports/${encodeURIComponent(project)}`, payload);
      } catch (e) {
        error.textContent = e.message;
        error.classList.remove("hidden");
        return;
      }
      close();
      tmsRefreshTreePane("reports-pane"); // E5: show the new report in the tree
      htmx.ajax("GET", `/ui/report/${project}/${file_name}.yaml`, {
        target: "#main-pane",
        swap: "innerHTML",
      });
    },
  });

  await renderConfig();
  updateSlug();
  setTimeout(() => titleInput.focus(), 0);
}

/**
 * "+ Add runs" on the report detail. Loads the current report + the
 * project's runs, opens a pre-checked run picker, then PATCHes the full
 * report doc with the new run_paths (≤ 10 guard). On success the detail
 * re-renders from the fresh document.
 */
async function tmsAddReportRuns(project, fileName) {
  let report, runs;
  try {
    const [rr, ru] = await Promise.all([
      fetch(`/api/reports/${encodeURIComponent(project)}/${encodeURIComponent(fileName)}`, {
        headers: { Accept: "application/json" },
      }),
      fetch(`/api/runs/${encodeURIComponent(project)}`, {
        headers: { Accept: "application/json" },
      }),
    ]);
    if (!rr.ok) throw new Error("Could not load report (HTTP " + rr.status + ")");
    if (!ru.ok) throw new Error("Could not load runs (HTTP " + ru.status + ")");
    report = await rr.json();
    ({ runs } = await ru.json());
  } catch (e) {
    alert(e.message);
    return;
  }

  const picker = tmsBuildRunPicker(runs, {
    selected: new Set(report.run_paths || []),
  });
  const body = document.createElement("div");
  const hint = document.createElement("p");
  hint.className = "text-sm text-slate-600 mb-2";
  hint.textContent = "Select the runs this report should aggregate (max 10).";
  body.appendChild(hint);
  body.appendChild(picker.node);
  const error = document.createElement("p");
  error.className = "hidden mt-2 text-sm text-rose-600";
  body.appendChild(error);

  tmsOpenModal({
    title: "Add / remove runs",
    body,
    confirmLabel: "Save",
    size: "lg",
    onConfirm: async ({ close }) => {
      error.classList.add("hidden");
      const run_paths = picker.getSelected();
      if (run_paths.length > 10) {
        error.textContent = "A report may reference at most 10 runs.";
        error.classList.remove("hidden");
        return;
      }
      const updated = { ...report, run_paths };
      try {
        const r = await fetch(
          `/api/reports/${encodeURIComponent(project)}/${encodeURIComponent(fileName)}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updated),
          }
        );
        if (!r.ok) {
          const data = await r.json().catch(() => ({}));
          throw new Error(data?.error?.message || "HTTP " + r.status);
        }
      } catch (e) {
        error.textContent = e.message;
        error.classList.remove("hidden");
        return;
      }
      close();
      htmx.ajax("GET", `/ui/report/${project}/${fileName}`, {
        target: "#main-pane",
        swap: "innerHTML",
      });
    },
  });
}

/**
 * "Edit scope" on a tag_inventory report detail. Loads the current
 * report + the project's folder paths, opens a scope <select> pre-set to
 * the current scope, then PATCHes the full report doc. On success the
 * detail re-renders against the new scope.
 */
async function tmsEditReportScope(project, fileName) {
  let report, folders;
  try {
    const rr = await fetch(
      `/api/reports/${encodeURIComponent(project)}/${encodeURIComponent(fileName)}`,
      { headers: { Accept: "application/json" } }
    );
    if (!rr.ok) throw new Error("Could not load report (HTTP " + rr.status + ")");
    report = await rr.json();
    folders = await tmsFetchProjectFolderPaths(project);
    if (!folders.length) folders = [project];
  } catch (e) {
    alert(e.message);
    return;
  }

  const body = document.createElement("div");
  body.innerHTML =
    '<label class="block text-sm text-slate-600 mb-1" for="tms-es-scope">Scope</label>' +
    '<select id="tms-es-scope" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>' +
    '<p data-role="error" class="hidden mt-2 text-sm text-rose-600"></p>';
  const scopeSel = body.querySelector("#tms-es-scope");
  tmsFillSelect(scopeSel, folders);
  if (folders.includes(report.scope)) scopeSel.value = report.scope;
  const error = body.querySelector('[data-role="error"]');

  tmsOpenModal({
    title: "Edit scope",
    body,
    confirmLabel: "Save",
    onConfirm: async ({ close }) => {
      error.classList.add("hidden");
      const updated = { ...report, scope: scopeSel.value };
      try {
        const r = await fetch(
          `/api/reports/${encodeURIComponent(project)}/${encodeURIComponent(fileName)}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updated),
          }
        );
        if (!r.ok) {
          const data = await r.json().catch(() => ({}));
          throw new Error(data?.error?.message || "HTTP " + r.status);
        }
      } catch (e) {
        error.textContent = e.message;
        error.classList.remove("hidden");
        return;
      }
      close();
      htmx.ajax("GET", `/ui/report/${project}/${fileName}`, {
        target: "#main-pane",
        swap: "innerHTML",
      });
    },
  });
}

