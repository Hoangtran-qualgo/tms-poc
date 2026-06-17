// -----------------------------------------------------------------------
// Wiring
// -----------------------------------------------------------------------

document.body.addEventListener("htmx:afterSwap", (e) => {
  if (e.target && e.target.id === "tree-pane") {
    tmsRestoreTreeState();
  }
  // tech-10 (10b): keep the active typed sidebar tree (test-run / reports)
  // expanded to the deep-linked item across its lazy mount + SSE refreshes.
  if (
    e.target &&
    (e.target.id === "test-run-pane" ||
      e.target.id === "reports-pane" ||
      e.target.id === "enums-pane")
  ) {
    tmsRestoreTypedTree(e.target);
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

// tech-10 (10c): a deep-linked / pasted URL can point at a missing item (the
// route 404s) or any failing main-pane fetch. htmx does NOT swap error
// responses by default, which would leave #main-pane stuck on its "Loading…"
// placeholder inside the shell. Inject the server's `_ui_error_html` snippet so
// the user sees a clean message in the main pane. Scoped to #main-pane so it
// never alters error handling for the sidebar panes or other requests.
document.body.addEventListener("htmx:responseError", (e) => {
  const d = e.detail;
  if (d && d.target && d.target.id === "main-pane" && d.xhr) {
    d.target.innerHTML = d.xhr.responseText;
    // The editor DOM (if any) was just replaced by the error snippet; drop the
    // stale editor state so SSE / the dirty guards stop tracking a gone item.
    if (!document.getElementById("file-editor")) tmsEditor.state = null;
    if (!document.getElementById("run-editor")) tmsRunEditor.state = null;
  }
});

// SSE-driven external-change detection. PLAN.md §9.5 covers the file
// editor; Phase 3.G of 10-feature-test-run-NEW.md extends it to the
// run editor with the same state machine.
document.body.addEventListener("sse:change", () => {
  if (tmsEditor.state) tmsEditor.onExternalChange();
  if (tmsRunEditor.state) tmsRunEditor.onExternalChange();
});

// tech-10 (10a): make Back/Forward a full reload rather than a snapshot
// restore. A reload re-renders the shell from the server (the item URL hits
// the non-HX shell branch) so all scripts run once in a fresh document and the
// #main-pane load-trigger re-fetches the item. This sidesteps htmx's history
// snapshot, which would neither re-run the editors' tail <script> nor be safe
// to innerHTML-swap over the page's top-level `const` script tags.
if (window.htmx) {
  htmx.config.historyCacheSize = 0;
  htmx.config.refreshOnHistoryMiss = true;
}

/** The /ui/... URL of the editor currently mounted in the main pane, or null.
 *  Reconstructed from editor state (mirrors each editor's own reload URL) so
 *  the popstate guard can re-push it without tracking history separately. */
function tmsCurrentEditorUrl() {
  if (tmsRunEditor && tmsRunEditor.state) {
    const s = tmsRunEditor.state;
    return encodeURI(`/ui/run/${s.project}/${s.group}/${s.file_name}`);
  }
  if (tmsEditor && tmsEditor.state) {
    return encodeURI(`/ui/file/${tmsEditor.state.path}`);
  }
  return null;
}

// tech-10 (10c): guard in-app Back/Forward against silently discarding a dirty
// editor. Under D2, htmx's popstate handler turns Back/Forward into a full
// reload; on a dirty editor that reload would fire the beforeunload prompt, but
// the popstate has ALREADY moved the address bar — so a "Stay" leaves the URL
// desynced from the still-shown editor. We wrap htmx's handler: confirm first,
// and on cancel re-push the editor's URL so the bar matches the content; on
// confirm, clear the dirty flag so the ensuing reload's beforeunload is silent
// (no double prompt).
if (window.htmx) {
  const tmsHtmxOnPopstate = window.onpopstate;
  window.onpopstate = function (event) {
    const editorUrl = tmsCurrentEditorUrl();
    const dirty =
      (tmsEditor.state && tmsEditor.state.dirty) ||
      (tmsRunEditor.state && tmsRunEditor.state.dirty);
    if (editorUrl && dirty) {
      const leave = window.confirm(
        "Discard your unsaved changes and leave this view?"
      );
      if (!leave) {
        history.pushState({ htmx: true }, "", editorUrl);
        return;
      }
      if (tmsEditor.state) tmsEditor.state.dirty = false;
      if (tmsRunEditor.state) tmsRunEditor.state.dirty = false;
    }
    if (typeof tmsHtmxOnPopstate === "function") {
      tmsHtmxOnPopstate.call(this, event);
    }
  };
}

// Wire the persistent top-bar search input + sidebar shell once the DOM
// is ready. Both live in base.html so they're available immediately on
// first paint.
function tmsBootShell() {
  tmsWireSearch();
  tmsInitSidebar();
  // tech-10: rehydrate the open item's context on cold load. Route the
  // server-computed expand paths to the active tab's tree.
  const tab = window.TMS_ACTIVE_TAB;
  const expand = Array.isArray(window.TMS_EXPAND_PATHS)
    ? window.TMS_EXPAND_PATHS
    : [];
  if (tab && tab !== "tree") {
    // 10b: seed the typed tree, then activate the tab. The lazy mount's
    // htmx:afterSwap (and every SSE refresh) re-applies tmsTypedExpand.
    expand.forEach((p) => tmsTypedExpand.add(p));
    tmsSwitchSidebarTab(tab);
  } else {
    // 10a: seed the Directory tree.
    expand.forEach((p) => tmsExpandedFolders.add(p));
  }
  // The directory tree is server-included in base.html (not an htmx swap), so
  // its htmx:afterSwap restore never fires at boot — apply it explicitly.
  tmsRestoreTreeState();
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
