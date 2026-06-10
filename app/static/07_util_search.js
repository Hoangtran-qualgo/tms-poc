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

