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

