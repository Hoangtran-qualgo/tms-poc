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
