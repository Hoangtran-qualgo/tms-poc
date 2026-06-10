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
 * the "Move test case to another folder" feature; see DONE.md § Must have).
 * Designed to be reused by future pickers — caller passes a generic body
 * Element so any form / list / picker can live inside.
 *
 * @param {object}  opts
 * @param {string}  opts.title          Heading text.
 * @param {string|Node} opts.body       Body content; string is text, Node is appended as-is.
 * @param {string|null} [opts.confirmLabel]  Confirm button label. Default
 *   "Confirm". Pass `null` to render no Confirm button at all (used by
 *   information-only modals such as the zero-projects branch of
 *   `tmsCreateRun`, which has nothing actionable to confirm).
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
  if (confirmLabel === null) {
    // Information-only modal: drop the Confirm button entirely so the
    // footer only shows Cancel. Caller's `onConfirm` is never invoked.
    confirmBtn.remove();
  } else {
    confirmBtn.textContent = confirmLabel;
    confirmBtn.disabled = !!confirmDisabled;
  }
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
  // The confirm button may have been removed for information-only modals;
  // attach listeners and expose setConfirmDisabled only when it still lives
  // in the card. `parentNode` flips to null after `.remove()`; `isConnected`
  // is unreliable here because the card itself isn't in the document yet.
  const hasConfirm = confirmBtn.parentNode !== null;
  if (hasConfirm) {
    confirmBtn.addEventListener("click", async () => {
      if (confirmBtn.disabled) return;
      try {
        await onConfirm?.({ close });
      } catch (_) {
        /* caller is expected to surface its own errors */
      }
    });
  }

  document.addEventListener("keydown", onKey);
  document.body.appendChild(overlay);
  return {
    close,
    setConfirmDisabled: (v) => {
      if (hasConfirm) confirmBtn.disabled = !!v;
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
 * two-prompt flow. Both fields are required client-side as a "non-empty
 * after trim" check;
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
        tmsRefreshTreePane("tree-pane"); // E5: show the new case in the tree
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

