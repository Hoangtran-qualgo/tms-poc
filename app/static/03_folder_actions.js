// -----------------------------------------------------------------------
// Folder-view actions
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
  const url = "/ui/folder/" + (folderPath ? tmsEncodePath(folderPath) : "");
  htmx.ajax("GET", url, { target: "#main-pane", swap: "innerHTML" });
}

function tmsEncodePath(path) {
  return path.split("/").map((segment) => encodeURIComponent(segment)).join("/");
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
 * @param {"md"|"lg"|"xl"|"2xl"} [opts.size]  Modal max width. Default "md".
 *   md = max-w-md (small forms), lg = max-w-2xl (case picker),
 *   xl = max-w-4xl (large pickers), 2xl = max-w-6xl (import preview —
 *   wide enough to show 50 chars of a scenario name on one line).
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
    size === "2xl"
      ? "max-w-6xl"
      : size === "xl"
        ? "max-w-4xl"
        : size === "lg"
          ? "max-w-2xl"
          : "max-w-md";
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
    if (e.key === "Escape") {
      close();
    } else if (e.metaKey && e.key === "Enter") {
      e.preventDefault();
      triggerConfirm();
    }
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
  let confirmInFlight = false;
  const triggerConfirm = async () => {
    if (!hasConfirm || confirmBtn.disabled || confirmInFlight) return;
    confirmInFlight = true;
    try {
      await onConfirm?.({ close });
    } catch (_) {
      /* caller is expected to surface its own errors */
    } finally {
      confirmInFlight = false;
    }
  };
  if (hasConfirm) {
    confirmBtn.addEventListener("click", triggerConfirm);
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
 * Confirm and delete one module/branch folder. The templates expose this only
 * below project depth, so project typed data (runs, reports, enums) is never
 * reachable through this UI action.
 */
function tmsDeleteFolder(folderPath, parentPath) {
  const body = document.createElement("div");
  const warning = document.createElement("p");
  warning.className = "text-sm text-slate-700";
  warning.textContent =
    "Permanently delete " + folderPath +
    ", including all sub-folders and test cases? This cannot be undone.";
  const error = document.createElement("p");
  error.className = "hidden mt-2 text-sm text-red-600";
  body.appendChild(warning);
  body.appendChild(error);

  tmsOpenModal({
    title: "Delete folder",
    body,
    confirmLabel: "Delete folder",
    onConfirm: async ({ close }) => {
      error.classList.add("hidden");
      try {
        const encodedPath = folderPath
          .split("/")
          .map((segment) => encodeURIComponent(segment))
          .join("/");
        const response = await fetch("/api/folders/" + encodedPath, {
          method: "DELETE",
        });
        if (!response.ok) {
          let message = response.statusText;
          try {
            const data = await response.json();
            if (data?.error?.message) message = data.error.message;
          } catch (_) {}
          throw new Error(message);
        }
      } catch (e) {
        error.textContent = "Could not delete folder: " + e.message;
        error.classList.remove("hidden");
        return;
      }
      close();
      tmsRefreshFolder(parentPath);
      tmsRefreshTreePane("tree-pane");
    },
  });
}

/** Rename a project, module, or branch and refresh its renamed location. */
function tmsRenameFolder(folderPath) {
  const parts = folderPath.split("/");
  const currentName = parts.at(-1);
  const isProject = parts.length === 1;
  const body = document.createElement("div");
  body.innerHTML =
    '<label class="block text-sm text-slate-600 mb-1" for="tms-rf-name">Folder name</label>' +
    '<input id="tms-rf-name" type="text" autocomplete="off"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '<p class="text-xs text-slate-500 mt-2"></p>' +
    '<p data-role="error" class="hidden mt-2 text-sm text-red-600"></p>';
  const nameInput = body.querySelector("#tms-rf-name");
  const note = body.querySelector("p.text-xs");
  const error = body.querySelector('[data-role="error"]');
  nameInput.value = currentName;
  note.textContent = isProject
    ? "Linked test runs and reports update to the new project path."
    : "Linked test runs and reports update to the new folder path.";

  const modal = tmsOpenModal({
    title: isProject ? "Rename project" : "Rename folder",
    body,
    confirmLabel: "Rename",
    onConfirm: async ({ close }) => {
      const name = nameInput.value.trim();
      if (!name) return;
      error.classList.add("hidden");
      try {
        const response = await fetch("/api/folders/" + tmsEncodePath(folderPath), {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        });
        if (!response.ok) {
          const data = await response.json().catch(() => null);
          throw new Error(data?.error?.message || response.statusText);
        }
      } catch (e) {
        error.textContent = e.message;
        error.classList.remove("hidden");
        return;
      }

      const newPath = [...parts.slice(0, -1), name].join("/");
      close();
      if (isProject) {
        window.location.assign("/ui/folder/" + tmsEncodePath(newPath));
        return;
      }
      window.history.pushState({}, "", "/ui/folder/" + tmsEncodePath(newPath));
      tmsRefreshFolder(newPath);
      tmsRefreshTreePane("tree-pane");
    },
  });

  nameInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const button = body
      .closest('[role="dialog"]')
      ?.querySelector('[data-action="confirm"]');
    if (button && !button.disabled) button.click();
  });
  setTimeout(() => {
    nameInput.focus();
    nameInput.select();
  }, 0);
  return modal;
}

/** Rename one test-case file from its folder listing. */
function tmsRenameFile(filePath, currentName) {
  const body = document.createElement("div");
  body.innerHTML =
    '<label class="block text-sm text-slate-600 mb-1" for="tms-rfile-name">File name</label>' +
    '<input id="tms-rfile-name" type="text" autocomplete="off"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '<p class="text-xs text-slate-500 mt-1">.feature is added automatically.</p>' +
    '<p data-role="error" class="hidden mt-2 text-sm text-red-600"></p>';
  const nameInput = body.querySelector("#tms-rfile-name");
  const error = body.querySelector('[data-role="error"]');
  nameInput.value = currentName;

  const modal = tmsOpenModal({
    title: "Rename test case",
    body,
    confirmLabel: "Rename",
    onConfirm: async ({ close }) => {
      const fileName = nameInput.value.trim();
      if (!fileName) return;
      error.classList.add("hidden");
      try {
        const response = await fetch(
          "/api/files/" + tmsEncodePath(filePath) + "/rename",
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_name: fileName }),
          }
        );
        if (!response.ok) {
          const data = await response.json().catch(() => null);
          throw new Error(data?.error?.message || response.statusText);
        }
      } catch (e) {
        error.textContent = e.message;
        error.classList.remove("hidden");
        return;
      }

      close();
      tmsRefreshFolder(filePath.split("/").slice(0, -1).join("/"));
      tmsRefreshTreePane("tree-pane");
    },
  });

  nameInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const button = body
      .closest('[role="dialog"]')
      ?.querySelector('[data-action="confirm"]');
    if (button && !button.disabled) button.click();
  });
  setTimeout(() => {
    nameInput.focus();
    nameInput.select();
  }, 0);
  return modal;
}

/**
 * Open the single-form create-test-case modal (tech-04 D2/D3). Three
 * fields, top-down: File name (required), Feature description (optional),
 * Scenario name (required). Confirm is gated on File name + Scenario name
 * being non-empty after trim; the description is optional. All other
 * validation (regex, name conflicts, etc.) is delegated to the server
 * response so the client never drifts from `_validate_segment` /
 * `NameConflictError`.
 */
function tmsCreateFile(parent) {
  const body = document.createElement("div");
  body.innerHTML =
    '<label class="block text-sm text-slate-600 mb-1" for="tms-cf-name">File name</label>' +
    '<input id="tms-cf-name" type="text" autocomplete="off"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '<p class="text-xs text-slate-400 mt-1">.feature is added automatically.</p>' +
    '<label class="block text-sm text-slate-600 mt-3 mb-1" for="tms-cf-desc">Feature description <span class="text-slate-400">(optional)</span></label>' +
    '<textarea id="tms-cf-desc" rows="2"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white resize-y"></textarea>' +
    '<label class="block text-sm text-slate-600 mt-3 mb-1" for="tms-cf-scenario">Scenario name</label>' +
    '<input id="tms-cf-scenario" type="text" autocomplete="off"' +
    ' class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />' +
    '<p data-role="error" class="hidden mt-2 text-sm text-red-600"></p>';
  const nameInput = body.querySelector("#tms-cf-name");
  const descInput = body.querySelector("#tms-cf-desc");
  const scenarioInput = body.querySelector("#tms-cf-scenario");
  const error = body.querySelector('[data-role="error"]');

  const trimmed = () => [
    nameInput.value.trim(),
    descInput.value.trim(),
    scenarioInput.value.trim(),
  ];

  const modal = tmsOpenModal({
    title: "Create test case in " + parent,
    body,
    confirmLabel: "Create",
    confirmDisabled: true,
    onConfirm: async ({ close }) => {
      const [fileName, description, scenarioName] = trimmed();
      if (!fileName || !scenarioName) return;
      error.classList.add("hidden");
      try {
        await tmsApiPost("/api/files", {
          parent,
          file_name: fileName,
          scenario_name: scenarioName,
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

  // Gate Confirm on File name + Scenario name being non-empty after trim
  // (the description is optional).
  const refreshGate = () => {
    const [n, , sc] = trimmed();
    modal.setConfirmDisabled(!(n && sc));
  };
  nameInput.addEventListener("input", refreshGate);
  scenarioInput.addEventListener("input", refreshGate);

  // Keyboard ergonomics: Enter in a single-line input advances focus down
  // the field chain; Ctrl/Cmd+Enter in any field submits (same path as the
  // Confirm button click). The description is a textarea, so plain Enter
  // there inserts a newline.
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
  scenarioInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  });

  // Defer focus to after the overlay is in the DOM.
  setTimeout(() => nameInput.focus(), 0);
}


/**
 * Return the first ``count`` free feature leaves for one destination folder.
 * Existing leaf names are compared case-insensitively, matching storage.
 */
function tmsSuggestImportFilenames(folderName, occupiedNames, count) {
  const occupied = new Set(
    Array.from(occupiedNames, (name) => String(name).toLowerCase())
  );
  const suggestions = [];
  let number = 1;
  while (suggestions.length < count) {
    const name = `${folderName}_${number}.feature`;
    number += 1;
    if (occupied.has(name.toLowerCase())) continue;
    occupied.add(name.toLowerCase());
    suggestions.push(name);
  }
  return suggestions;
}

/**
 * Open the "Import test cases" modal (feature-14). Launched from the global
 * top-bar button. Upload up to 20 `.feature` files (3 MB total), preview the
 * split scenarios, name each output file, then commit. The destination is
 * chosen via a project selector + a destination-folder selector that lists
 * folders **relative to the chosen project** (module level and below). Enum
 * directives are dropped on import; one acknowledgement covers every source
 * containing them. All blocking validation (duplicate file / scenario names,
 * content rules) is delegated to the server, whose errors are rendered as a
 * list.
 */
async function tmsImportFile() {
  let tree;
  try {
    const r = await fetch("/api/tree", { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    tree = await r.json();
  } catch (e) {
    alert("Could not load folders: " + e.message);
    return;
  }

  // project name -> [destination folder paths] (depth >= 1 = modules and
  // deeper; reserved areas are already hidden from /api/tree).
  const foldersByProject = new Map();
  const folderNodesByPath = new Map();
  for (const projNode of tree.children || []) {
    if (projNode.type !== "folder") continue;
    const list = [];
    const walk = (node) => {
      for (const child of node.children || []) {
        if (child.type === "folder") {
          list.push(child.path);
          folderNodesByPath.set(child.path, child);
          walk(child);
        }
      }
    };
    walk(projNode);
    foldersByProject.set(projNode.name, list);
  }

  const projects = Array.from(foldersByProject.keys());
  if (projects.length === 0) {
    const info = document.createElement("div");
    info.innerHTML =
      '<p class="text-sm text-slate-700">No projects yet — create one first.</p>';
    tmsOpenModal({ title: "Import test cases", body: info, confirmLabel: null });
    return;
  }

  const body = document.createElement("div");
  body.innerHTML =
    '<div class="grid grid-cols-2 gap-3">' +
    '  <div>' +
    '    <label class="block text-sm text-slate-600 mb-1" for="tms-im-project">Project</label>' +
    '    <select id="tms-im-project" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>' +
    "  </div>" +
    '  <div>' +
    '    <label class="block text-sm text-slate-600 mb-1" for="tms-im-folder">Destination folder</label>' +
    '    <select id="tms-im-folder" class="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"></select>' +
    "  </div>" +
    "</div>" +
    '<label class="block text-sm text-slate-600 mt-3 mb-1" for="tms-im-file">.feature files</label>' +
    '<input id="tms-im-file" type="file" accept=".feature" multiple' +
    ' class="w-full text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-4 file:rounded file:border-2 file:border-slate-400 file:bg-slate-100 file:text-slate-700 file:text-sm file:font-semibold hover:file:bg-slate-200 hover:file:border-slate-500 file:cursor-pointer" />' +
    '<p class="text-xs text-slate-400 mt-1">Up to 20 files, 3 MB total. Enum directives are dropped on import.</p>' +
    '<div data-role="enum-warn" class="hidden mt-3 p-2 border border-amber-300 bg-amber-50 rounded text-sm text-amber-800">' +
    '  <label class="flex items-start gap-2">' +
    '    <input type="checkbox" data-role="enum-ack" class="mt-0.5" />' +
    '    <span data-role="enum-message">Enum directives will be <strong>dropped</strong> on import. Check to acknowledge.</span>' +
    "  </label>" +
    "</div>" +
    '<div data-role="scenarios" class="mt-3"></div>' +
    '<p data-role="error" class="hidden mt-2 text-sm text-red-600"></p>';

  const projectSel = body.querySelector("#tms-im-project");
  const folderSel = body.querySelector("#tms-im-folder");
  const fileInput = body.querySelector("#tms-im-file");
  const enumWarn = body.querySelector('[data-role="enum-warn"]');
  const enumAck = body.querySelector('[data-role="enum-ack"]');
  const enumMessage = body.querySelector('[data-role="enum-message"]');
  const scenBox = body.querySelector('[data-role="scenarios"]');
  const error = body.querySelector('[data-role="error"]');

  // Preview state captured for the commit step.
  let sourceItems = [];
  let scenarios = [];
  let previewErrors = [];
  let enumSources = [];
  let enumsPresent = false;
  let modalRef = null;

  for (const p of projects) {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    projectSel.appendChild(opt);
  }
  projectSel.value = projects[0];

  const populateFolders = () => {
    folderSel.innerHTML = "";
    const proj = projectSel.value;
    const list = foldersByProject.get(proj) || [];
    if (list.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "(no folders — create a module first)";
      folderSel.appendChild(opt);
      folderSel.disabled = true;
    } else {
      folderSel.disabled = false;
      // Project is chosen separately, so display each folder path relative
      // to the project (module level and below); the full path stays the
      // option value for the commit call.
      const prefix = proj + "/";
      for (const f of list) {
        const opt = document.createElement("option");
        opt.value = f;
        opt.textContent = f.startsWith(prefix) ? f.slice(prefix.length) : f;
        folderSel.appendChild(opt);
      }
    }
  };
  populateFolders();

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

  const getNames = () =>
    Array.from(scenBox.querySelectorAll('input[data-role="filename"]')).map((i) =>
      i.value.trim()
    );

  const refreshGeneratedNames = () => {
    const folder = folderNodesByPath.get(folderSel.value);
    if (!folder) return;
    const inputs = Array.from(
      scenBox.querySelectorAll('input[data-role="filename"]')
    );
    const generatedInputs = inputs.filter(
      (input) => input.dataset.generated !== "0"
    );
    const occupied = (folder.children || []).map((child) => child.name);
    for (const input of inputs) {
      if (input.dataset.generated === "0" && input.value) {
        const name = input.value.toLowerCase().endsWith(".feature")
          ? input.value
          : input.value + ".feature";
        occupied.push(name);
      }
    }
    const suggestions = tmsSuggestImportFilenames(
      folder.name,
      occupied,
      generatedInputs.length
    );
    generatedInputs.forEach((input, index) => {
      input.value = suggestions[index];
      input.dataset.generatedName = suggestions[index];
      input.dataset.generated = "1";
    });
  };

  const refreshGate = () => {
    if (!modalRef) return;
    const names = getNames();
    const allNamed =
      scenarios.length > 0 &&
      names.length === scenarios.length &&
      names.every((n) => n.length > 0);
    const folderOk = !!folderSel.value;
    const enumOk = !enumsPresent || enumAck.checked;
    modalRef.setConfirmDisabled(
      !(folderOk && allNamed && enumOk && previewErrors.length === 0)
    );
  };

  // Format a tag list as "@a @b +N more" (top 2, @-prefixed); em-dash when
  // empty.
  const fmtTags = (tags) => {
    const t = tags || [];
    if (!t.length) return "—";
    const shown = t.slice(0, 2).map((x) => "@" + x).join(" ");
    const more = t.length - 2;
    return more > 0 ? shown + " +" + more + " more" : shown;
  };

  const renderScenarios = () => {
    scenBox.innerHTML = "";
    if (!scenarios.length) return;
    const header = document.createElement("p");
    header.className = "text-sm text-slate-600 mb-2";
    header.textContent =
      scenarios.length + " scenario(s) found — name each file:";
    scenBox.appendChild(header);

    const scroll = document.createElement("div");
    scroll.className = "border border-slate-200 rounded max-h-72 overflow-auto";
    const table = document.createElement("table");
    table.className = "w-full text-sm";
    table.innerHTML =
      '<thead class="bg-slate-50 text-slate-600 sticky top-0">' +
      "  <tr>" +
      '    <th class="text-left px-2 py-1.5 font-medium">Source file</th>' +
      '    <th class="text-left px-2 py-1.5 font-medium">Scenario name</th>' +
      '    <th class="text-left px-2 py-1.5 font-medium">Feature tag</th>' +
      '    <th class="text-left px-2 py-1.5 font-medium">Scenario tag</th>' +
      '    <th class="text-left px-2 py-1.5 font-medium">File name</th>' +
      "  </tr>" +
      "</thead>";
    const tbody = document.createElement("tbody");
    table.appendChild(tbody);

    scenarios.forEach((sc) => {
      const tr = document.createElement("tr");
      tr.className = "border-t border-slate-100";

      const sourceTd = document.createElement("td");
      sourceTd.className = "px-2 py-1.5 text-slate-500 whitespace-nowrap";
      sourceTd.textContent = sc.source_name;
      sourceTd.title = sc.source_name;

      const nameTd = document.createElement("td");
      nameTd.className = "px-2 py-1.5 text-slate-800 whitespace-nowrap";
      const full = sc.scenario_name || "(unnamed scenario)";
      nameTd.textContent = full.length > 50 ? full.slice(0, 50) + "…" : full;
      nameTd.title = full;

      const featTd = document.createElement("td");
      featTd.className = "px-2 py-1.5 text-slate-500 whitespace-nowrap";
      featTd.textContent = fmtTags(sc.feature_tags);

      const scenTd = document.createElement("td");
      scenTd.className = "px-2 py-1.5 text-slate-500 whitespace-nowrap";
      scenTd.textContent = fmtTags(sc.scenario_tags);

      const fileTd = document.createElement("td");
      fileTd.className = "px-2 py-1.5";
      const input = document.createElement("input");
      input.type = "text";
      input.autocomplete = "off";
      input.dataset.role = "filename";
      input.placeholder = "file name";
      input.dataset.generated = "1";
      input.className =
        "w-44 border border-slate-300 rounded px-2 py-1 text-sm bg-white";
      input.addEventListener("input", () => {
        input.dataset.generated =
          input.value === input.dataset.generatedName ? "1" : "0";
        refreshGate();
      });
      fileTd.appendChild(input);

      tr.appendChild(sourceTd);
      tr.appendChild(nameTd);
      tr.appendChild(featTd);
      tr.appendChild(scenTd);
      tr.appendChild(fileTd);
      tbody.appendChild(tr);
    });

    scroll.appendChild(table);
    scenBox.appendChild(scroll);
    refreshGeneratedNames();
  };

  const resetPreview = () => {
    sourceItems = [];
    scenarios = [];
    previewErrors = [];
    enumSources = [];
    enumsPresent = false;
    scenBox.innerHTML = "";
    enumWarn.classList.add("hidden");
    enumAck.checked = false;
    error.classList.add("hidden");
    refreshGate();
  };

  fileInput.addEventListener("change", async () => {
    resetPreview();
    const files = Array.from(fileInput.files || []);
    if (!files.length) return;
    if (files.length > 20) {
      showError("Import batch exceeds the 20-file limit.");
      return;
    }
    const wrongTypes = files.filter((file) => !file.name.toLowerCase().endsWith(".feature"));
    if (wrongTypes.length) {
      showError(
        "Every selected file must end with .feature.",
        wrongTypes.map((file) => file.name)
      );
      return;
    }
    const totalBytes = files.reduce((total, file) => total + file.size, 0);
    if (totalBytes > 3 * 1024 * 1024) {
      showError("Import batch exceeds the 3 MB total limit.");
      return;
    }
    let results;
    try {
      results = await Promise.allSettled(files.map((file) => file.text()));
    } catch (_) {
      showError("Could not read the selected files.");
      return;
    }
    const readErrors = [];
    sourceItems = [];
    results.forEach((result, index) => {
      if (result.status === "fulfilled") {
        sourceItems.push({ name: files[index].name, source: result.value });
      } else {
        readErrors.push(files[index].name + ": could not read file.");
      }
    });
    if (readErrors.length) {
      sourceItems = [];
      showError("Could not read every selected file.", readErrors);
      return;
    }
    let data;
    try {
      const r = await fetch("/api/files/import/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sources: sourceItems }),
      });
      data = await r.json();
      if (!r.ok) {
        showError((data.error && data.error.message) || r.statusText);
        return;
      }
    } catch (e) {
      showError(e.message);
      return;
    }
    scenarios = data.scenarios || [];
    previewErrors = data.errors || [];
    enumSources = data.enum_sources || [];
    enumsPresent = !!data.enums_present;
    if (!scenarios.length && !previewErrors.length) {
      showError("No scenarios found to import.");
      return;
    }
    enumWarn.classList.toggle("hidden", !enumsPresent);
    if (enumsPresent) {
      const names = enumSources.map((source) => source.source_name).join(", ");
      enumMessage.textContent =
        names + " contain enum directives. They will be dropped on import. Check to acknowledge.";
    }
    renderScenarios();
    if (previewErrors.length) {
      showError(
        "Fix every source before importing:",
        previewErrors.map((item) => item.source_name + ": " + item.message)
      );
    }
    refreshGate();
  });

  projectSel.addEventListener("change", () => {
    populateFolders();
    refreshGeneratedNames();
    refreshGate();
  });
  folderSel.addEventListener("change", () => {
    refreshGeneratedNames();
    refreshGate();
  });
  enumAck.addEventListener("change", refreshGate);

  modalRef = tmsOpenModal({
    title: "Import test cases",
    body,
    confirmLabel: "Import",
    confirmDisabled: true,
    size: "2xl",
    onConfirm: async ({ close }) => {
      error.classList.add("hidden");
      const parentPath = folderSel.value;
      const names = getNames();
      if (
        !parentPath ||
        !scenarios.length ||
        previewErrors.length ||
        names.some((n) => !n)
      ) return;
      let data;
      try {
        const r = await fetch("/api/files/import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project: projectSel.value,
            parent: parentPath,
            sources: sourceItems,
            names,
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
      close();
      tmsRefreshFolder(parentPath);
      tmsRefreshTreePane("tree-pane");
    },
  });
}
