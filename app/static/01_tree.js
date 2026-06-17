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

/** Re-apply an expand-state Set to the .tree-folder rows under `root`,
 *  un-hiding each matching folder's .tree-children sibling. Shared by the
 *  Directory tree and the typed sidebar trees (test-run / reports), which use
 *  the same row markup. */
function tmsApplyTreeExpansion(root, expandSet) {
  if (!root) return;
  root.querySelectorAll(".tree-folder").forEach((row) => {
    const path = row.dataset.path;
    if (!path || !expandSet.has(path)) return;
    const children = row.nextElementSibling;
    if (!children || !children.classList.contains("tree-children")) return;
    if (children.classList.contains("hidden")) {
      children.classList.remove("hidden");
      const caret = row.querySelector(".caret");
      if (caret) caret.innerHTML = "&#9660;" /* ▼ */;
    }
  });
}

/** Re-apply the Directory-tree expand state to a freshly-rendered tree. */
function tmsRestoreTreeState() {
  tmsApplyTreeExpansion(document.getElementById("tree-pane"), tmsExpandedFolders);
}

/** tech-10 (10b): folder data-paths to keep open in the active typed sidebar
 *  tree (test-run / reports) so a deep-linked run/report stays revealed across
 *  the pane's lazy mount + SSE refreshes. Seeded from window.TMS_EXPAND_PATHS
 *  at boot when the active tab is a typed tab (see 09_bootstrap.js). */
const tmsTypedExpand = new Set();

/** Re-apply tmsTypedExpand to a freshly-rendered typed sidebar pane. */
function tmsRestoreTypedTree(paneEl) {
  tmsApplyTreeExpansion(paneEl, tmsTypedExpand);
}

