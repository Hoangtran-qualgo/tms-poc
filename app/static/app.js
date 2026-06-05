// TMS client-side helpers.
//
// Populated across PLAN.md Do steps 12–14:
//   - Step 12: tree expand/collapse.
//   - Step 13 (this file): folder-view actions (new project / new module
//     / new test case), expand-state preservation across SSE refreshes.
//   - Step 14: file editor dirty tracking, beforeunload, search input
//     debounce, chip-input behaviour, grid keyboard nav.

// -----------------------------------------------------------------------
// Tree state
// -----------------------------------------------------------------------

/** Set of folder paths the user has expanded. Survives tree re-renders. */
const tmsExpandedFolders = new Set();

/**
 * Toggle the .tree-children sibling of a clicked .tree-folder row.
 * Updates the caret glyph in place and records the change in
 * `tmsExpandedFolders` so SSE refreshes can re-apply.
 */
function toggleTreeFolder(rowEl) {
  if (!rowEl) return;
  const children = rowEl.nextElementSibling;
  if (!children || !children.classList.contains("tree-children")) return;
  const isHidden = children.classList.toggle("hidden");
  const caret = rowEl.querySelector(".caret");
  if (caret) {
    caret.innerHTML = isHidden ? "&#9654;" /* ▶ */ : "&#9660;" /* ▼ */;
  }
  const path = rowEl.dataset.path;
  if (path) {
    if (isHidden) tmsExpandedFolders.delete(path);
    else tmsExpandedFolders.add(path);
  }
}

/** Re-apply the expand state to a freshly-rendered tree. */
function tmsRestoreTreeState() {
  document.querySelectorAll("#tree-pane .tree-folder").forEach((row) => {
    const path = row.dataset.path;
    if (!path || !tmsExpandedFolders.has(path)) return;
    const children = row.nextElementSibling;
    if (!children || !children.classList.contains("tree-children")) return;
    if (children.classList.contains("hidden")) {
      children.classList.remove("hidden");
      const caret = row.querySelector(".caret");
      if (caret) caret.innerHTML = "&#9660;" /* ▼ */;
    }
  });
}

// -----------------------------------------------------------------------
// Sidebar shell — Phase 2 (specs/features/10-feature-test-run-NEW.md)
//
// Two-tab vertical sidebar with:
//   - tab switching (Directory tree <-> Test run);
//   - lazy mount of the Test-run panel on first activation, then sticky
//     SSE refresh even while the panel is hidden;
//   - drag-to-resize the whole sidebar (bounds clamped, persisted in
//     localStorage, double-click resets to default);
//   - collapse the sidebar to just the tab strip (persisted).
//
// No expand-state persistence for the Test-run tree in v1 — see the
// "persist expand-state for the Test run sidebar tab" backlog item.
// -----------------------------------------------------------------------

const TMS_SIDEBAR_WIDTH_KEY = "tms.sidebar.width";
const TMS_SIDEBAR_COLLAPSED_KEY = "tms.sidebar.collapsed";

/** Switch the active sidebar tab. If the sidebar is collapsed, expand it. */
function tmsSwitchSidebarTab(target) {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;

  if (sidebar.dataset.collapsed === "1") {
    tmsSetSidebarCollapsed(false);
  }

  document.querySelectorAll("#sidebar-tabs .sidebar-tab").forEach((btn) => {
    const isActive = btn.dataset.sidebarTab === target;
    if (isActive) {
      btn.classList.add(
        "border-slate-800", "font-medium", "text-slate-800"
      );
      btn.classList.remove(
        "border-transparent", "text-slate-500", "hover:text-slate-700"
      );
    } else {
      btn.classList.remove(
        "border-slate-800", "font-medium", "text-slate-800"
      );
      btn.classList.add(
        "border-transparent", "text-slate-500", "hover:text-slate-700"
      );
    }
  });

  const treePane = document.getElementById("tree-pane");
  const runPane = document.getElementById("test-run-pane");
  if (treePane && runPane) {
    treePane.classList.toggle("hidden", target !== "tree");
    runPane.classList.toggle("hidden", target !== "test-run");
  }

  if (target === "test-run") tmsActivateTestRunPane();
}

/**
 * Mount the Test-run panel on first activation: attach the htmx
 * attributes and trigger the initial fetch. After this runs once, the
 * panel re-renders on every `sse:change` even while it is hidden.
 */
function tmsActivateTestRunPane() {
  const pane = document.getElementById("test-run-pane");
  if (!pane || pane.dataset.mounted === "1") return;
  pane.dataset.mounted = "1";
  pane.setAttribute("hx-get", "/ui/test-run-tree");
  pane.setAttribute("hx-trigger", "sse:change");
  pane.setAttribute("hx-swap", "innerHTML");
  if (window.htmx) {
    htmx.process(pane);
    htmx.ajax("GET", "/ui/test-run-tree", { target: "#test-run-pane", swap: "innerHTML" });
  }
}

// ---- Sidebar resize ----------------------------------------------------

let tmsSidebarResize = null; // { startX, startWidth }

function tmsClampSidebarWidth(px) {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return px;
  const min = Number(sidebar.dataset.minWidth) || 240;
  const max = Number(sidebar.dataset.maxWidth) || 600;
  return Math.max(min, Math.min(max, px));
}

function tmsSetSidebarWidth(px, { persist } = { persist: true }) {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  const clamped = tmsClampSidebarWidth(px);
  sidebar.style.width = clamped + "px";
  if (persist) {
    try {
      localStorage.setItem(TMS_SIDEBAR_WIDTH_KEY, String(clamped));
    } catch (_) {}
  }
}

function tmsStartSidebarResize(event) {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar || sidebar.dataset.collapsed === "1") return;
  event.preventDefault();
  tmsSidebarResize = {
    startX: event.clientX,
    startWidth: sidebar.getBoundingClientRect().width,
  };
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";
  document.addEventListener("mousemove", tmsOnSidebarResizeMove);
  document.addEventListener("mouseup", tmsOnSidebarResizeEnd);
}

function tmsOnSidebarResizeMove(event) {
  if (!tmsSidebarResize) return;
  const dx = event.clientX - tmsSidebarResize.startX;
  tmsSetSidebarWidth(tmsSidebarResize.startWidth + dx, { persist: false });
}

function tmsOnSidebarResizeEnd() {
  if (!tmsSidebarResize) return;
  const sidebar = document.getElementById("sidebar");
  tmsSidebarResize = null;
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
  document.removeEventListener("mousemove", tmsOnSidebarResizeMove);
  document.removeEventListener("mouseup", tmsOnSidebarResizeEnd);
  if (sidebar) {
    try {
      localStorage.setItem(
        TMS_SIDEBAR_WIDTH_KEY,
        String(Math.round(sidebar.getBoundingClientRect().width))
      );
    } catch (_) {}
  }
}

function tmsResetSidebarWidth() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  const def = Number(sidebar.dataset.defaultWidth) || 316;
  tmsSetSidebarWidth(def);
}

// ---- Sidebar collapse --------------------------------------------------

function tmsSetSidebarCollapsed(collapsed) {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  const icon = document.getElementById("sidebar-collapse-icon");
  const handle = document.getElementById("sidebar-resize-handle");
  const panels = document.getElementById("sidebar-panels");
  if (collapsed) {
    sidebar.dataset.collapsed = "1";
    // Remember the expanded width so toggle-back restores it.
    sidebar.dataset.expandedWidth = String(
      Math.round(sidebar.getBoundingClientRect().width)
    );
    sidebar.style.width = "36px";
    if (panels) panels.classList.add("hidden");
    if (handle) handle.classList.add("hidden");
    if (icon) icon.innerHTML = "&raquo;";
  } else {
    sidebar.dataset.collapsed = "0";
    const restore =
      Number(sidebar.dataset.expandedWidth) ||
      Number(localStorage.getItem(TMS_SIDEBAR_WIDTH_KEY)) ||
      Number(sidebar.dataset.defaultWidth) ||
      316;
    sidebar.style.width = tmsClampSidebarWidth(restore) + "px";
    if (panels) panels.classList.remove("hidden");
    if (handle) handle.classList.remove("hidden");
    if (icon) icon.innerHTML = "&laquo;";
  }
  try {
    localStorage.setItem(TMS_SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
  } catch (_) {}
}

function tmsToggleSidebarCollapse() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  tmsSetSidebarCollapsed(sidebar.dataset.collapsed !== "1");
}

/** Apply persisted width + collapsed state on initial page load. */
function tmsInitSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  let stored = NaN;
  try {
    stored = Number(localStorage.getItem(TMS_SIDEBAR_WIDTH_KEY));
  } catch (_) {}
  if (Number.isFinite(stored) && stored > 0) {
    tmsSetSidebarWidth(stored, { persist: false });
  }
  let collapsed = false;
  try {
    collapsed = localStorage.getItem(TMS_SIDEBAR_COLLAPSED_KEY) === "1";
  } catch (_) {}
  if (collapsed) tmsSetSidebarCollapsed(true);
}

// -----------------------------------------------------------------------
// Folder-view actions (prompt-based for v1; modal polish in step 14)
// -----------------------------------------------------------------------

async function tmsApiPost(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = r.statusText;
    try {
      const j = await r.json();
      if (j && j.error && j.error.message) msg = j.error.message;
    } catch (_) {}
    throw new Error(msg);
  }
  return r;
}

function tmsRefreshFolder(folderPath) {
  const url = "/ui/folder/" + (folderPath || "");
  htmx.ajax("GET", url, { target: "#main-pane", swap: "innerHTML" });
}

/**
 * Open a small modal dialog. First in-app modal primitive (introduced for
 * the "Move test case to another folder" feature; see IN-PROGRESS.md).
 * Designed to be reused by future pickers — caller passes a generic body
 * Element so any form / list / picker can live inside.
 *
 * @param {object}  opts
 * @param {string}  opts.title          Heading text.
 * @param {string|Node} opts.body       Body content; string is text, Node is appended as-is.
 * @param {string} [opts.confirmLabel]  Confirm button label. Default "Confirm".
 * @param {boolean}[opts.confirmDisabled] Initial disabled state.
 * @param {"md"|"lg"|"xl"} [opts.size]  Modal max width. Default "md".
 *   md = max-w-md (small forms), lg = max-w-2xl (case picker),
 *   xl = max-w-4xl (large pickers / future).
 * @param {(ctx:{close:()=>void})=>any} [opts.onConfirm]
 *   Called when Confirm is clicked. The caller decides when to close (so a
 *   failed request can keep the modal open). Awaited if it returns a promise.
 *
 * @returns {{ close: ()=>void, setConfirmDisabled: (v:boolean)=>void }}
 */
function tmsOpenModal({
  title,
  body,
  confirmLabel = "Confirm",
  confirmDisabled = false,
  size = "md",
  onConfirm,
}) {
  const overlay = document.createElement("div");
  overlay.className =
    "fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");

  const sizeClass =
    size === "xl" ? "max-w-4xl" : size === "lg" ? "max-w-2xl" : "max-w-md";
  const card = document.createElement("div");
  card.className = `bg-white rounded shadow-lg w-full ${sizeClass} mx-4 p-4`;
  card.innerHTML =
    '<h3 class="text-lg font-semibold mb-3 text-slate-800"></h3>' +
    '<div class="mb-4" data-role="body"></div>' +
    '<div class="flex justify-end gap-2">' +
    '  <button type="button" data-action="cancel" class="px-3 py-1.5 text-sm border border-slate-300 rounded hover:bg-slate-50">Cancel</button>' +
    '  <button type="button" data-action="confirm" class="px-3 py-1.5 text-sm bg-slate-800 text-white rounded hover:bg-slate-700 disabled:bg-slate-400 disabled:cursor-not-allowed"></button>' +
    "</div>";
  card.querySelector("h3").textContent = title;
  const bodyHost = card.querySelector('[data-role="body"]');
  if (typeof body === "string") bodyHost.textContent = body;
  else if (body instanceof Node) bodyHost.appendChild(body);
  const confirmBtn = card.querySelector('[data-action="confirm"]');
  confirmBtn.textContent = confirmLabel;
  confirmBtn.disabled = !!confirmDisabled;
  overlay.appendChild(card);

  const close = () => {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
  };
  const onKey = (e) => {
    if (e.key === "Escape") close();
  };
  // Backdrop-only click closes; clicks inside the card do not bubble out.
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });
  card.querySelector('[data-action="cancel"]').addEventListener("click", close);
  confirmBtn.addEventListener("click", async () => {
    if (confirmBtn.disabled) return;
    try {
      await onConfirm?.({ close });
    } catch (_) {
      /* caller is expected to surface its own errors */
    }
  });

  document.addEventListener("keydown", onKey);
  document.body.appendChild(overlay);
  return {
    close,
    setConfirmDisabled: (v) => {
      confirmBtn.disabled = !!v;
    },
  };
}

async function tmsCreateProject() {
  const name = (window.prompt("New project name:") || "").trim();
  if (!name) return;
  try {
    await tmsApiPost("/api/folders", { parent: "", name });
    tmsRefreshFolder("");
  } catch (e) {
    alert("Could not create project: " + e.message);
  }
}

async function tmsCreateModule(project) {
  const name = (window.prompt("New module name:") || "").trim();
  if (!name) return;
  try {
    await tmsApiPost("/api/folders", { parent: project, name });
    tmsRefreshFolder(project);
  } catch (e) {
    alert("Could not create module: " + e.message);
  }
}

async function tmsCreateSubfolder(parent) {
  // Used by the "+ Sub-folder" button in folder_module.html and
  // folder_subfolder.html. `parent` is already a non-empty depth >= 2
  // path because the button only renders inside a module or deeper
  // sub-folder view. The server enforces the depth cap.
  const name = (window.prompt("New sub-folder name:") || "").trim();
  if (!name) return;
  try {
    await tmsApiPost("/api/folders", { parent, name });
    tmsRefreshFolder(parent);
  } catch (e) {
    alert("Could not create sub-folder: " + e.message);
  }
}

/**
 * Open the single-form create-test-case modal. Replaces the previous
 * two-prompt flow (see IN-PROGRESS.md "Single-form create-test-case flow").
 * Both fields are required client-side as a "non-empty after trim" check;
 * all other validation (regex, name conflicts, etc.) is delegated to the
 * server response so the client never drifts from `_validate_segment` /
 * `NameConflictError`.
 */
function tmsCreateFile(parent) {
  const body = document.createElement("div");
  body.innerHTML =
    '<label class="block text-sm text-slate-600 mb-1" for="tms-cf-name">File name</label>' +
    '<input id="tms-cf-name" type="text" autocomplete="off"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '<p class="text-xs text-slate-400 mt-1">.feature is added automatically.</p>' +
    '<label class="block text-sm text-slate-600 mt-3 mb-1" for="tms-cf-desc">Description</label>' +
    '<textarea id="tms-cf-desc" rows="2"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white resize-y"></textarea>' +
    '<p data-role="error" class="hidden mt-2 text-sm text-red-600"></p>';
  const nameInput = body.querySelector("#tms-cf-name");
  const descInput = body.querySelector("#tms-cf-desc");
  const error = body.querySelector('[data-role="error"]');

  const trimmed = () => [nameInput.value.trim(), descInput.value.trim()];

  const modal = tmsOpenModal({
    title: "Create test case in " + parent,
    body,
    confirmLabel: "Create",
    confirmDisabled: true,
    onConfirm: async ({ close }) => {
      const [fileName, description] = trimmed();
      if (!fileName || !description) return;
      error.classList.add("hidden");
      try {
        await tmsApiPost("/api/files", {
          parent,
          file_name: fileName,
          description,
        });
        close();
        tmsRefreshFolder(parent);
      } catch (e) {
        error.textContent = e.message;
        error.classList.remove("hidden");
      }
    },
  });

  // Gate Confirm on both fields being non-empty after trim.
  const refreshGate = () => {
    const [n, d] = trimmed();
    modal.setConfirmDisabled(!(n && d));
  };
  nameInput.addEventListener("input", refreshGate);
  descInput.addEventListener("input", refreshGate);

  // Keyboard ergonomics: Enter inside the single-line name input acts
  // like Tab to the description; Ctrl/Cmd+Enter inside either field
  // submits (calling the same path as the Confirm button click).
  const submit = () => {
    const btn = body
      .closest('[role="dialog"]')
      ?.querySelector('[data-action="confirm"]');
    if (btn && !btn.disabled) btn.click();
  };
  nameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      descInput.focus();
    } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      submit();
    }
  });
  descInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      submit();
    }
  });

  // Defer focus to after the overlay is in the DOM.
  setTimeout(() => nameInput.focus(), 0);
}

// -----------------------------------------------------------------------
// Test-run create flow — Phase 3.B of `10-feature-test-run-NEW.md`.
//
// `tmsCreateRun(project, group)` opens a single modal containing:
//   - run name (text)
//   - description (textarea, optional)
//   - case picker: flat checkbox table of every .feature file under the
//     given project, sorted by folder path then file name, with a search
//     filter on top.
//
// On confirm the run's file_name is derived from the name via a small
// slugifier; POST hits /api/runs and on success the main pane is
// navigated to /ui/run/<project>/<group>/<file_name>.yaml (the route
// itself lands in Phase 3.C — clicks before then 404 with a clean
// envelope, the modal closes either way).
//
// The case-picker helper is factored out so Phase 3.E's "+ Add test
// case" modal in the run editor reuses it verbatim with the editor's
// current case_paths excluded.
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
 * of {path, file_name, folder_path} for every .feature file under the
 * given project, sorted by folder_path ASC then file_name ASC.
 */
async function tmsFetchProjectFeaturePaths(project) {
  const r = await fetch("/api/tree", { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error("Could not load tree: " + r.statusText);
  const tree = await r.json();
  const projectNode = (tree.children || []).find(
    (c) => c.type === "folder" && c.name === project
  );
  if (!projectNode) return [];
  const out = [];
  const walk = (node) => {
    if (!node) return;
    if (node.type === "feature") {
      const path = node.path;
      const slash = path.lastIndexOf("/");
      out.push({
        path,
        file_name: slash === -1 ? path : path.slice(slash + 1),
        folder_path: slash === -1 ? "" : path.slice(0, slash),
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
    '    <th class="text-left px-2 py-1.5 font-medium w-8"></th>' +
    '    <th class="text-left px-2 py-1.5 font-medium">Folder</th>' +
    '    <th class="text-left px-2 py-1.5 font-medium">File</th>' +
    "  </tr>" +
    "</thead>";
  const tbody = document.createElement("tbody");
  table.appendChild(tbody);
  scroll.appendChild(table);

  // Empty-state row when nothing is available (project has no features,
  // or all features are already in the run).
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
      tr.dataset.path = f.path;
      tr.dataset.folder = (f.folder_path || "").toLowerCase();
      tr.dataset.file = f.file_name.toLowerCase();
      tr.innerHTML =
        '<td class="px-2 py-1.5 align-top">' +
        '  <input type="checkbox" class="rounded border-slate-300" />' +
        "</td>" +
        '<td class="px-2 py-1.5 text-slate-500"></td>' +
        '<td class="px-2 py-1.5 text-slate-800"></td>';
      tr.children[1].textContent = f.folder_path;
      tr.children[2].textContent = f.file_name;
      tbody.appendChild(tr);
    }
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
  updateCount();

  tbody.addEventListener("change", (e) => {
    if (e.target.matches('input[type="checkbox"]')) {
      updateCount();
      opts.onChange?.();
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
  });

  return {
    node: wrap,
    getSelected: () =>
      Array.from(tbody.querySelectorAll('input[type="checkbox"]:checked'))
        .map((box) => box.closest("tr").dataset.path),
    countVisible: () => visible.length,
  };
}

/**
 * Open the "+ New run" modal for the given (project, group).
 *
 * Called by folder_test_run_group.html's toolbar button and empty-state
 * CTA. Field-level validation is purely "non-empty after trim" on the
 * client; server-side errors (name conflict, depth violation, etc.)
 * propagate from /api/runs and are surfaced inline in the modal so the
 * user can correct and retry without losing their selection.
 */
async function tmsCreateRun(project, group) {
  let features;
  try {
    features = await tmsFetchProjectFeaturePaths(project);
  } catch (e) {
    alert("Could not load test cases: " + e.message);
    return;
  }

  const body = document.createElement("div");
  body.innerHTML =
    '<label class="block text-sm text-slate-600 mb-1" for="tms-cr-name">Run name</label>' +
    '<input id="tms-cr-name" type="text" autocomplete="off"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '<label class="block text-sm text-slate-600 mt-3 mb-1" for="tms-cr-desc">Description <span class="text-slate-400 font-normal">(optional)</span></label>' +
    '<textarea id="tms-cr-desc" rows="2"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white resize-y"></textarea>' +
    '<label class="block text-sm text-slate-600 mt-3 mb-1">Test cases</label>' +
    '<div data-role="picker-host"></div>' +
    '<p data-role="error" class="hidden mt-2 text-sm text-red-600"></p>';
  const nameInput = body.querySelector("#tms-cr-name");
  const descInput = body.querySelector("#tms-cr-desc");
  const pickerHost = body.querySelector('[data-role="picker-host"]');
  const error = body.querySelector('[data-role="error"]');

  let modalRef = null;
  const refreshGate = () => {
    if (!modalRef) return;
    const ok =
      nameInput.value.trim().length > 0 && picker.getSelected().length > 0;
    modalRef.setConfirmDisabled(!ok);
  };
  const picker = tmsBuildCasePicker(features, { onChange: refreshGate });
  pickerHost.appendChild(picker.node);

  modalRef = tmsOpenModal({
    title: `Create run in ${project} / ${group}`,
    body,
    size: "lg",
    confirmLabel: "Create run",
    confirmDisabled: true,
    onConfirm: async ({ close }) => {
      const name = nameInput.value.trim();
      const description = descInput.value.trim();
      const case_paths = picker.getSelected();
      if (!name || case_paths.length === 0) return;
      const file_name = tmsSlugifyForFilename(name);
      if (!file_name) {
        error.textContent =
          "Run name produces an empty file name; use letters or digits.";
        error.classList.remove("hidden");
        return;
      }
      error.classList.add("hidden");
      try {
        await tmsApiPost("/api/runs", {
          project,
          group,
          name,
          file_name,
          description,
          case_paths,
        });
        close();
        // Navigate the main pane to the new run editor. The route lands
        // in Phase 3.C; until then this swap will 404 cleanly via the
        // blueprint's error handler.
        htmx.ajax(
          "GET",
          `/ui/run/${project}/${group}/${file_name}.yaml`,
          { target: "#main-pane", swap: "innerHTML" }
        );
      } catch (e) {
        error.textContent = e.message;
        error.classList.remove("hidden");
      }
    },
  });

  nameInput.addEventListener("input", refreshGate);
  setTimeout(() => nameInput.focus(), 0);
}

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
    this.state.baselineJson = JSON.stringify(this._readCurrent());
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

  /** Snapshot the live DOM into the shape patch_run expects. */
  _readCurrent() {
    const nameEl = document.getElementById("run-name");
    const descEl = document.getElementById("run-description");
    const rows = document.querySelectorAll("#run-results tbody tr");
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
        if (e.target.matches(".run-result-select")) onChange();
      });
      tbody.addEventListener("click", (e) => {
        if (e.target.matches(".run-row-remove")) {
          e.target.closest("tr").remove();
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
    link.textContent = file_path;
    link.setAttribute("hx-get", `/ui/file/${file_path}`);
    // Result defaults to PENDING (spec: "newly-checked row is appended
    // as a fresh PENDING row with empty remark").
    tr.querySelector(".run-result-select").value = "PENDING";
    tr.querySelector(".run-remark").value = "";
    return tr;
  },

  /** Toggle table / empty-state visibility + refresh dirty. */
  _afterRowsChanged() {
    const tbody = document.querySelector("#run-results tbody");
    const hasRows = !!(tbody && tbody.children.length > 0);
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
      .querySelectorAll("#run-results tbody tr")
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
          tbody.appendChild(this._createResultRow(p));
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
    const liveJson = JSON.stringify(this._readCurrent());
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
      this.state.baselineJson = JSON.stringify(current);
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
        diskJson = JSON.stringify({
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

// -----------------------------------------------------------------------
// Top-bar search wiring (PLAN.md §9.1, R5)
// -----------------------------------------------------------------------

/**
 * Wire the top-bar search input to /ui/search via htmx.ajax.
 *
 * Replaces an earlier HTMX-trigger-based wiring that relied on bare-name
 * filter expressions (e.g. `keyup[key=='Enter']`). Under HTMX 2.x, the
 * filter eval scope does not expose bare event properties, so the filter
 * silently throws and neither trigger fires. Wiring this in JS is
 * explicit, debuggable, and gives us:
 *   - immediate fire on Enter
 *   - 300 ms idle debounce on every other keyup
 *   - re-fire when scope/match/case change
 *   - skip the request entirely when q is empty (server handles empty
 *     anyway, but skipping avoids stale-flash of empty-state HTML)
 */
function tmsWireSearch() {
  const q = document.getElementById("search-q");
  const scope = document.getElementById("search-scope");
  const match = document.getElementById("search-match");
  const caseChk = document.getElementById("search-case");
  if (!q) return;  // base.html not yet in DOM; bail.

  let debounceTimer = null;

  function fire() {
    const params = new URLSearchParams({
      q: q.value,
      scope: scope.value,
      match: match.value,
      case: caseChk.checked ? "true" : "false",
    });
    htmx.ajax("GET", "/ui/search?" + params.toString(), {
      target: "#main-pane",
      swap: "innerHTML",
    });
  }

  function scheduleFire(delay) {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fire, delay);
  }

  q.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (debounceTimer) {
        clearTimeout(debounceTimer);
        debounceTimer = null;
      }
      fire();
    }
  });
  q.addEventListener("input", () => scheduleFire(300));
  // Scope/match/case changes re-fire immediately if there's a query.
  for (const el of [scope, match, caseChk]) {
    el.addEventListener("change", () => {
      if (q.value.trim()) fire();
    });
  }
}

// -----------------------------------------------------------------------
// Misc helpers
// -----------------------------------------------------------------------

function tmsEscape(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

/** Tag character rule mirror of `models._is_valid_tag` (PLAN.md §4). */
function tmsIsValidTag(t) {
  if (!t) return false;
  for (const ch of t) {
    const cp = ch.charCodeAt(0);
    if (cp < 0x21 || cp > 0x7e) return false;
    if (ch === "@" || ch === ",") return false;
  }
  return true;
}

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
    };
    this.renderStructured();
    this.renderRaw();
    this.wireHeaderButtons();
    this.wireStructuredInputs();
    this.wireRawInputs();
    this.wireTabButtons();
    this.updateSaveButton();
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
   * branches of both `save` (structured) and `saveRaw` (raw tab); see
   * IN-PROGRESS.md "Save success indicator" entry.
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
  // share three requirements (IN-PROGRESS.md "Inline data table & Examples
  // table sizing"):
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
   * See IN-PROGRESS.md "Manual refresh button for the test-case editor".
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

// -----------------------------------------------------------------------
// Wiring
// -----------------------------------------------------------------------

document.body.addEventListener("htmx:afterSwap", (e) => {
  if (e.target && e.target.id === "tree-pane") {
    tmsRestoreTreeState();
  }
  // If the main pane was just swapped to something OTHER than the file
  // editor, clear the editor state so SSE events stop polling for it.
  if (e.target && e.target.id === "main-pane") {
    if (!document.getElementById("file-editor")) {
      tmsEditor.state = null;
    }
    // Same housekeeping for the run editor: when the main pane no
    // longer hosts it, drop the in-memory state so SSE / beforeunload
    // stop guarding a run that is no longer on screen.
    if (!document.getElementById("run-editor")) {
      tmsRunEditor.state = null;
    }
  }
});

// SSE-driven external-change detection. PLAN.md §9.5 covers the file
// editor; Phase 3.G of 10-feature-test-run-NEW.md extends it to the
// run editor with the same state machine.
document.body.addEventListener("sse:change", () => {
  if (tmsEditor.state) tmsEditor.onExternalChange();
  if (tmsRunEditor.state) tmsRunEditor.onExternalChange();
});

// Wire the persistent top-bar search input + sidebar shell once the DOM
// is ready. Both live in base.html so they're available immediately on
// first paint.
function tmsBootShell() {
  tmsWireSearch();
  tmsInitSidebar();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", tmsBootShell);
} else {
  tmsBootShell();
}

// Guard against losing unsaved editor state on tab close / refresh.
// Either the file editor or the run editor can hold a dirty buffer.
window.addEventListener("beforeunload", (e) => {
  const dirty =
    (tmsEditor.state && tmsEditor.state.dirty) ||
    (tmsRunEditor.state && tmsRunEditor.state.dirty);
  if (dirty) {
    e.preventDefault();
    e.returnValue = "";
    return "";
  }
});
