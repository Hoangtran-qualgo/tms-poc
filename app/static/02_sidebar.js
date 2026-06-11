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
  const reportsPane = document.getElementById("reports-pane");
  const enumsPane = document.getElementById("enums-pane");
  if (treePane) treePane.classList.toggle("hidden", target !== "tree");
  if (runPane) runPane.classList.toggle("hidden", target !== "test-run");
  if (reportsPane) reportsPane.classList.toggle("hidden", target !== "reports");
  if (enumsPane) enumsPane.classList.toggle("hidden", target !== "enums");

  if (target === "test-run") tmsActivateTestRunPane();
  if (target === "reports") tmsActivateReportsPane();
  if (target === "enums") tmsActivateEnumsPane();
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

/**
 * Mount the Reports panel on first activation. Mirrors
 * tmsActivateTestRunPane: lazy hx-get + sse:change refresh.
 */
function tmsActivateReportsPane() {
  const pane = document.getElementById("reports-pane");
  if (!pane || pane.dataset.mounted === "1") return;
  pane.dataset.mounted = "1";
  pane.setAttribute("hx-get", "/ui/reports-tree");
  pane.setAttribute("hx-trigger", "sse:change");
  pane.setAttribute("hx-swap", "innerHTML");
  if (window.htmx) {
    htmx.process(pane);
    htmx.ajax("GET", "/ui/reports-tree", { target: "#reports-pane", swap: "innerHTML" });
  }
}

/**
 * Mount the Enums panel on first activation. Mirrors
 * tmsActivateReportsPane: lazy hx-get + sse:change refresh. The pane lists
 * projects; clicking one loads its manager into #main-pane.
 */
function tmsActivateEnumsPane() {
  const pane = document.getElementById("enums-pane");
  if (!pane || pane.dataset.mounted === "1") return;
  pane.dataset.mounted = "1";
  pane.setAttribute("hx-get", "/ui/enums-tree");
  pane.setAttribute("hx-trigger", "sse:change");
  pane.setAttribute("hx-swap", "innerHTML");
  if (window.htmx) {
    htmx.process(pane);
    htmx.ajax("GET", "/ui/enums-tree", { target: "#enums-pane", swap: "innerHTML" });
  }
}

/**
 * E5 (specs/tech/02): refresh a sidebar tree pane after a successful in-app
 * create. The watcher deliberately suppresses `sse:change` for paths the app
 * itself just wrote, so a newly-created artifact would otherwise not appear in
 * its tree until an external change or a manual Refresh. We re-GET the pane so
 * it reflects current on-disk state (the new artifact shows up as on disk).
 *
 * Only mounted panes are refreshed: `#tree-pane` is mounted at page load
 * (its hx-get lives in base.html); the lazy run/report panes gain an hx-get
 * only after first activation. An unmounted pane needs nothing — it loads
 * fresh on first open. Triggering `sse:change` (rather than relaxing the
 * watcher suppression) keeps the editor's external-change banner quiet during
 * self-saves.
 */
function tmsRefreshTreePane(paneId) {
  const pane = document.getElementById(paneId);
  if (!pane || !window.htmx) return;
  const url = pane.getAttribute("hx-get");
  if (!url) return; // not mounted yet → loads fresh on first open
  htmx.ajax("GET", url, { target: "#" + paneId, swap: "innerHTML" });
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

