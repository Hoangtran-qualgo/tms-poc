"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table } from "@/components/ui/table";
import { ArrowLeft, LoaderCircle, Menu, Pencil, Plus, Trash2, Upload, X } from "lucide-react";
import type { FeaturePayload } from "@/src/lib/feature";

type Counts = { total: number; auto: number; non_auto: number };
type TreeNode = { type: "folder" | "feature" | "other"; name: string; path: string; children?: TreeNode[]; counts?: Counts };
type FeatureSummary = { file_name: string; description: string; scenario_name: string; tags: string[]; enums: Array<{ kind: string; key: string; label: string }> };
type Listing = { kind: string; folders?: string[]; features?: FeatureSummary[]; projects?: string[]; modules?: string[] };
type TestRunSummary = { path: string; project?: string; group: string; file_name: string; name: string; created_at: string; case_count: number; results_count_by_status: Record<string, number> };
type TestRun = { name: string; created_at: string; description: string; results: Array<{ file_path: string; result: string; remark: string; example?: { table: number; row: number } }> };
type ReportSummary = { project?: string; file_name: string; title: string; type: string; created_at: string; source: string };
type EnumVocabulary = Record<string, Record<string, string>>;
type Tab = "directory" | "runs" | "reports" | "enums";
type EditorBanner = { message: string; tone: "info" | "warning" | "error"; conflict: boolean; removed: boolean };
type FeatureEditRequest = { path: string; scenarioName: string; fileName: string };
type DialogRequest = { kind: "prompt"; title: string; label: string; initialValue?: string; confirmLabel: string; resolve: (value: string | null) => void } | { kind: "confirm"; title: string; description: string; confirmLabel: string; destructive?: boolean; resolve: (value: string | null) => void };
type DialogApi = { prompt: (request: Omit<Extract<DialogRequest, { kind: "prompt" }>, "kind" | "resolve">) => Promise<string | null>; confirm: (request: Omit<Extract<DialogRequest, { kind: "confirm" }>, "kind" | "resolve">) => Promise<boolean> };
const DialogContext = createContext<DialogApi | null>(null);
class TextApiError extends Error { constructor(message: string, readonly details?: { line?: number; column?: number }) { super(message); } }

function DialogHost({ request, onResolve }: { request: DialogRequest | null; onResolve: (value: string | null) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [value, setValue] = useState("");
  useEffect(() => { setValue(request?.kind === "prompt" ? request.initialValue ?? "" : ""); }, [request]);
  useEffect(() => {
    const node = dialog.current;
    if (!node || !request) return;
    if (!node.open) node.showModal();
    return () => { if (node.open) node.close(); };
  }, [request]);
  if (!request) return null;
  const prompt = request.kind === "prompt";
  return <dialog ref={dialog} className="app-dialog" aria-labelledby="dialog-title" aria-describedby={prompt ? undefined : "dialog-description"} onCancel={(event) => { event.preventDefault(); onResolve(null); }}><form className="dialog-form" onSubmit={(event) => { event.preventDefault(); onResolve(prompt ? value : "confirmed"); }}><div className="dialog-header"><h2 id="dialog-title">{request.title}</h2>{!prompt && <p id="dialog-description" className="muted">{request.description}</p>}</div>{prompt && <label className="editor-field"><span>{request.label}</span><Input autoFocus value={value} onChange={(event) => setValue(event.target.value)} /></label>}<div className="actions dialog-actions"><Button type="button" onClick={() => onResolve(null)}>Cancel</Button><Button variant={!prompt && request.destructive ? "danger" : "primary"} type="submit">{request.confirmLabel}</Button></div></form></dialog>;
}

function DialogProvider({ children }: { children: ReactNode }) {
  const [request, setRequest] = useState<DialogRequest | null>(null);
  const prompt = useCallback((next: Omit<Extract<DialogRequest, { kind: "prompt" }>, "kind" | "resolve">) => new Promise<string | null>((resolve) => setRequest({ ...next, kind: "prompt", resolve })), []);
  const confirm = useCallback((next: Omit<Extract<DialogRequest, { kind: "confirm" }>, "kind" | "resolve">) => new Promise<boolean>((resolve) => setRequest({ ...next, kind: "confirm", resolve: (value) => resolve(value === "confirmed") })), []);
  const resolve = useCallback((value: string | null) => { if (!request) return; request.resolve(value); setRequest(null); }, [request]);
  return <DialogContext.Provider value={{ prompt, confirm }}>{children}<DialogHost request={request} onResolve={resolve} /></DialogContext.Provider>;
}

function useDialog(): DialogApi {
  const dialog = useContext(DialogContext);
  if (!dialog) throw new Error("DialogProvider is required.");
  return dialog;
}

function LiveStatus({ message, assertive = false }: { message: string; assertive?: boolean }) {
  return <div className="sr-only" role={assertive ? "alert" : "status"} aria-live={assertive ? "assertive" : "polite"}>{message}</div>;
}

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.error?.message ?? `Request failed (${response.status})`);
  return payload as T;
}

async function textApi(url: string, init?: RequestInit): Promise<string> {
  const response = await fetch(url, init);
  const body = await response.text();
  if (!response.ok) {
    try { const error = (JSON.parse(body) as { error?: { message?: string; details?: { line?: number; column?: number } } }).error; throw new TextApiError(error?.message ?? `Request failed (${response.status})`, error?.details); }
    catch (error) { throw error instanceof Error ? error : new Error(`Request failed (${response.status})`); }
  }
  return body;
}

function pathUrl(base: string, path: string): string { return `${base}/${path.split("/").map(encodeURIComponent).join("/")}`; }

function generatedImportNames(folderPath: string, count: number, occupied: string[]): string[] {
  const stem = folderPath.split("/").at(-1) || "folder";
  const used = new Set(occupied.map((name) => name.toLowerCase()));
  const names: string[] = [];
  let number = 1;
  while (names.length < count) {
    const candidate = `${stem}_${number}.feature`;
    number += 1;
    if (used.has(candidate.toLowerCase())) continue;
    used.add(candidate.toLowerCase());
    names.push(candidate);
  }
  return names;
}

function FeatureImportPanel({ files, onFiles, onImport, onCancel }: { files: File[]; onFiles: (files: File[]) => void; onImport: () => void; onCancel: () => void }) {
  const [dragging, setDragging] = useState(false);
  return <section className="import-panel" aria-label="Import feature files"><div><strong>Import feature files</strong><p className="muted">Add up to 20 `.feature` files (3 MiB total).</p></div><label className={`dropzone ${dragging ? "dragging" : ""}`} onDragEnter={(event) => { event.preventDefault(); setDragging(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); onFiles(Array.from(event.dataTransfer.files)); }}><input className="dropzone-input" type="file" accept=".feature" multiple aria-label="Feature files to import" onChange={(event) => onFiles(Array.from(event.target.files ?? []))} /><span className="dropzone-title">Drop `.feature` files here</span><span className="muted">or click to browse</span></label>{files.length > 0 && <div className="import-selection" aria-live="polite">{files.length} file{files.length === 1 ? "" : "s"} selected</div>}<div className="actions"><Button variant="primary" disabled={!files.length} onClick={onImport}>Import {files.length || ""} files</Button><Button onClick={onCancel}>Cancel</Button></div></section>;
}

function FeatureImportDialog({ open, files, onFiles, onImport, onCancel }: { open: boolean; files: File[]; onFiles: (files: File[]) => void; onImport: () => void; onCancel: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { const node = dialog.current; if (!node) return; if (open && !node.open) node.showModal(); if (!open && node.open) node.close(); }, [open]);
  return <dialog ref={dialog} className="app-dialog import-dialog" aria-label="Import feature files" onCancel={(event) => { event.preventDefault(); onCancel(); }}><FeatureImportPanel files={files} onFiles={onFiles} onImport={onImport} onCancel={onCancel} /></dialog>;
}

function FeatureEditDialog({ request, onCancel, onSubmit }: { request: FeatureEditRequest | null; onCancel: () => void; onSubmit: (scenarioName: string, fileName: string) => Promise<boolean> }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [scenarioName, setScenarioName] = useState("");
  const [fileName, setFileName] = useState("");
  useEffect(() => { setScenarioName(request?.scenarioName ?? ""); setFileName(request?.fileName ?? ""); }, [request]);
  useEffect(() => { const node = dialog.current; if (!node || !request) return; if (!node.open) node.showModal(); return () => { if (node.open) node.close(); }; }, [request]);
  if (!request) return null;
  return <dialog ref={dialog} className="app-dialog" aria-labelledby="edit-feature-title" onCancel={(event) => { event.preventDefault(); onCancel(); }}><form className="dialog-form" onSubmit={(event) => { event.preventDefault(); void onSubmit(scenarioName.trim(), fileName.trim()).then((saved) => { if (saved) onCancel(); }); }}><div className="dialog-header"><h2 id="edit-feature-title">Edit test case</h2></div><label className="editor-field"><span>Scenario name</span><Input autoFocus value={scenarioName} onChange={(event) => setScenarioName(event.target.value)} /></label><label className="editor-field"><span>Feature file name</span><Input value={fileName} onChange={(event) => setFileName(event.target.value)} /></label><div className="actions dialog-actions"><Button type="button" onClick={onCancel}>Cancel</Button><Button variant="primary" type="submit">Save</Button></div></form></dialog>;
}

function FolderLinks({ names, parent, onOpen, emptyMessage }: { names: string[]; parent: string; onOpen: (path: string) => void | Promise<void>; emptyMessage?: string }) {
  if (!names.length) return emptyMessage ? <div className="muted">{emptyMessage}</div> : null;
  return <div className="folder-list" aria-label="Child folders">{names.map((name) => <button className="button folder-link" key={name} onClick={() => void onOpen(parent ? `${parent}/${name}` : name)}>{name}</button>)}</div>;
}

function InlinePills({ values, limit, prefix = "" }: { values: string[]; limit: number; prefix?: string }) {
  const hidden = values.slice(limit);
  return <span className="inline-pills">{values.slice(0, limit).map((value, index) => <span className="tag" key={`${value}-${index}`}>{prefix}{value}</span>)}{hidden.length > 0 && <span className="inline-more" title={hidden.map((value) => `${prefix}${value}`).join(", ")} aria-label={`${hidden.length} more items`}>...</span>}</span>;
}

function WorkspaceMenu({ tab, onChange }: { tab: Tab; onChange: (tab: Tab) => void | Promise<void> }) {
  const [open, setOpen] = useState(false);
  async function select(next: Tab) { await onChange(next); setOpen(false); }
  return <div className="screen-menu" onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); }}><button className="icon-button screen-menu-toggle" aria-label={`${open ? "Close" : "Open"} workspace menu`} aria-expanded={open} aria-controls="workspace-sections" onClick={() => setOpen((current) => !current)}><Menu size={18} aria-hidden="true" /></button>{open && <nav id="workspace-sections" className="screen-menu-popover" aria-label="Workspace sections">{(["directory", "runs", "reports", "enums"] as Tab[]).map((item) => <button key={item} className={`screen-menu-item ${tab === item ? "active" : ""}`} aria-current={tab === item ? "page" : undefined} onClick={() => void select(item)}>{item[0].toUpperCase() + item.slice(1)}</button>)}</nav>}</div>;
}

function TreeBranch({ nodes, selected, expanded, onToggle, onFolder, onFeature }: { nodes: TreeNode[]; selected: string; expanded: ReadonlySet<string>; onToggle: (path: string) => void; onFolder: (node: TreeNode) => void; onFeature: (node: TreeNode) => void }) {
  return <ul className="tree-list">{nodes.map((node) => {
    if (node.type !== "folder") return <li key={node.path}><button className={`tree-item ${selected === node.path ? "active" : ""}`} aria-current={selected === node.path ? "page" : undefined} onClick={() => onFeature(node)}><span>◇</span><span className="tree-label">{node.name}</span></button></li>;
    const hasChildren = (node.children?.length ?? 0) > 0;
    const isExpanded = expanded.has(node.path);
    return <li key={node.path}>
      <button className={`tree-item ${selected === node.path ? "active" : ""}`} aria-current={selected === node.path ? "page" : undefined} aria-expanded={hasChildren ? isExpanded : undefined} onClick={() => { if (hasChildren) onToggle(node.path); if (!hasChildren || !isExpanded) onFolder(node); }}><span className="tree-label">{node.name || "Projects"}</span>{node.counts && <span className="count">{node.counts.total}-{node.counts.auto}-{node.counts.non_auto}</span>}</button>
      {hasChildren && isExpanded && <div className="tree-children"><TreeBranch nodes={node.children ?? []} selected={selected} expanded={expanded} onToggle={onToggle} onFolder={onFolder} onFeature={onFeature} /></div>}
    </li>;
  })}</ul>;
}

type RunImportGroup = { project: string; group: string };
type RunImportPreview = { report_name: string; created_at: string; scenarios: Array<{ no: number; name: string; result: string; match: string; file_path?: string }>; counts: Record<string, number>; errors: string[] };

async function importRequest<T>(url: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const reasons = Array.isArray(payload?.error?.details?.reasons) ? payload.error.details.reasons : [];
    throw new Error([payload?.error?.message ?? `Request failed (${response.status})`, ...reasons].join("\n"));
  }
  return payload as T;
}

function RunImportForm({ onCancel, onCreated }: { onCancel: () => void; onCreated: (project: string, group: string, fileName: string) => void | Promise<void> }) {
  const [groups, setGroups] = useState<RunImportGroup[]>([]);
  const [destination, setDestination] = useState("");
  const [runName, setRunName] = useState("");
  const [fileName, setFileName] = useState("");
  const [description, setDescription] = useState("");
  const [html, setHtml] = useState("");
  const [preview, setPreview] = useState<RunImportPreview | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  useEffect(() => { void api<{ groups: RunImportGroup[] }>("/api/run-groups").then((value) => { setGroups(value.groups); setDestination((current) => current || (value.groups[0] ? `${value.groups[0].project}\u0000${value.groups[0].group}` : "")); }).catch((cause) => setError((cause as Error).message)); }, []);
  const selectedDestination = groups.find((item) => `${item.project}\u0000${item.group}` === destination);
  async function previewReport(source: string, project: string) {
    if (!source || !project) return;
    try { setLoading(true); setError(""); setPreview(await importRequest<RunImportPreview>("/api/runs/import/preview", { project, html: source })); }
    catch (cause) { setPreview(null); setError((cause as Error).message); }
    finally { setLoading(false); }
  }
  async function chooseFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 30 * 1024 * 1024) { setHtml(""); setPreview(null); setError("Imported report exceeds the 30 MiB limit."); return; }
    try { const source = await file.text(); setHtml(source); setError(""); if (selectedDestination) await previewReport(source, selectedDestination.project); }
    catch (cause) { setHtml(""); setPreview(null); setError((cause as Error).message); }
  }
  async function chooseDestination(event: React.ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value; setDestination(value); setPreview(null); if (html) { const owner = groups.find((item) => `${item.project}\u0000${item.group}` === value)?.project; if (owner) await previewReport(html, owner); }
  }
  const previewErrors = preview?.errors ?? [];
  async function commit() {
    if (!selectedDestination || !preview || previewErrors.length || !runName.trim() || !fileName.trim()) return;
    try {
      setLoading(true); setError(""); await importRequest("/api/runs/import", { project: selectedDestination.project, group: selectedDestination.group, name: runName.trim(), file_name: fileName.trim(), description, html });
      const normalized = fileName.trim().toLowerCase().endsWith(".yaml") ? fileName.trim() : `${fileName.trim()}.yaml`;
      setHtml(""); setPreview(null); if (fileInput.current) fileInput.current.value = ""; await onCreated(selectedDestination.project, selectedDestination.group, normalized);
    } catch (cause) { setError((cause as Error).message); }
    finally { setLoading(false); }
  }
  return <Card><CardHeader><div><strong>Import test run</strong><div className="muted">Allure single-file report; source is not retained.</div></div><Button onClick={onCancel}>Cancel</Button></CardHeader><CardContent><div className="run-import-form">{!groups.length ? <div className="notice info">No run groups yet — create one first.</div> : <><label className="editor-field"><span>Where</span><select value={destination} onChange={(event) => void chooseDestination(event)}><option value="">Select a run group</option>{groups.map((item) => <option key={`${item.project}/${item.group}`} value={`${item.project}\u0000${item.group}`}>{item.project} / {item.group}</option>)}</select></label><label className="editor-field"><span>Report file</span><input ref={fileInput} type="file" accept=".html,.htm,text/html" onChange={(event) => void chooseFile(event)} /></label><label className="editor-field"><span>Run file name</span><Input value={fileName} onChange={(event) => setFileName(event.target.value)} placeholder="allure-import.yaml" /></label><label className="editor-field"><span>Run name</span><Input value={runName} onChange={(event) => setRunName(event.target.value)} placeholder="Imported run" /></label><label className="editor-field"><span>Description</span><textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>{loading && <p className="muted">Preparing preview…</p>}{preview && <><div className="muted">{preview.report_name} · {preview.created_at}</div><div className="table-wrap"><Table><thead><tr><th>#</th><th>Scenario</th><th>Result</th><th>Matched case</th></tr></thead><tbody>{preview.scenarios.map((row) => <tr key={row.no}><td>{row.no}</td><td>{row.name}</td><td>{row.result}</td><td>{row.file_path ?? row.match}</td></tr>)}</tbody></Table></div></>}{(error || previewErrors.length > 0) && <div className="notice">{error && <div>{error}</div>}{previewErrors.map((reason) => <div key={reason}>{reason}</div>)}</div>}<div className="actions"><Button variant="primary" disabled={!selectedDestination || !preview || previewErrors.length > 0 || !runName.trim() || !fileName.trim() || loading} onClick={() => void commit()}>Import run</Button><Button onClick={onCancel}>Cancel</Button></div></>}</div></CardContent></Card>;
}

function RunsPanel({ project, initialRun, onError }: { project: string; initialRun: string; onError: (message: string) => void }) {
  const { prompt, confirm } = useDialog();
  const [runs, setRuns] = useState<TestRunSummary[]>([]);
  const [projects, setProjects] = useState<string[]>([]);
  const [scopeProject, setScopeProject] = useState(project);
  const [selected, setSelected] = useState<TestRun | null>(null);
  const [selectedPath, setSelectedPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [runLoading, setRunLoading] = useState(false);
  const [scenarioNames, setScenarioNames] = useState<Record<string, string>>({});
  const [openRemarks, setOpenRemarks] = useState<ReadonlySet<string>>(new Set());
  const [runDirty, setRunDirty] = useState(false);
  const [runSaved, setRunSaved] = useState(false);
  const [runImporting, setRunImporting] = useState(false);
  const initialRunOpened = useRef("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const catalog = await api<{ projects: string[] }>("/api/run-groups");
      const targets = project ? [project] : catalog.projects;
      setProjects(targets);
      if (!project && scopeProject && !targets.includes(scopeProject)) setScopeProject(targets[0] ?? "");
      const responses = await Promise.all(targets.map(async (owner) => (await api<{ runs: TestRunSummary[] }>(`/api/runs/${encodeURIComponent(owner)}`)).runs.map((run) => ({ ...run, project: owner }))));
      setRuns(responses.flat()); onError("");
    }
    catch (cause) { onError((cause as Error).message); }
    finally { setLoading(false); }
  }, [project, scopeProject, onError]);

  useEffect(() => { if (project) setScopeProject(project); void load(); setSelected(null); setSelectedPath(""); setRunDirty(false); }, [load, project]);

  async function open(path: string, owner: string, group: string, fileName: string) {
    setRunLoading(true); setSelected(null); setScenarioNames({}); setOpenRemarks(new Set());
    try {
      const run = await api<TestRun>(`/api/runs/${[owner, group, fileName].map(encodeURIComponent).join("/")}`);
      const names = Object.fromEntries(await Promise.all(run.results.map(async ({ file_path }) => {
        try { return [file_path, (await api<FeaturePayload>(pathUrl("/api/files", file_path))).scenario.name || "Scenario unavailable"]; }
        catch { return [file_path, "Scenario unavailable"]; }
      })));
      setSelected(run); setScenarioNames(names); setOpenRemarks(new Set(run.results.filter((item) => item.remark).map((item) => item.file_path))); setSelectedPath(path); setRunDirty(false); setRunSaved(false); onError("");
    }
    catch (cause) { onError((cause as Error).message); }
    finally { setRunLoading(false); }
  }

  useEffect(() => {
    if (!initialRun || !runs.length || selected || initialRunOpened.current === initialRun) return;
    const separator = initialRun.indexOf("/");
    if (separator < 1) return;
    const group = initialRun.slice(0, separator);
    const fileName = initialRun.slice(separator + 1);
    const match = runs.find((run) => run.group === group && run.file_name === fileName && (!project || run.project === project));
    if (!match) return;
    initialRunOpened.current = initialRun;
    void open(match.path, match.project ?? project, match.group, match.file_name);
  }, [initialRun, project, runs, selected]);

  function updateResult(filePath: string, result: string) {
    setSelected((current) => current ? { ...current, results: current.results.map((item) => item.file_path === filePath ? { ...item, result } : item) } : current);
    setRunDirty(true); setRunSaved(false);
  }

  function updateRemark(filePath: string, remark: string) {
    setSelected((current) => current ? { ...current, results: current.results.map((item) => item.file_path === filePath ? { ...item, remark } : item) } : current);
    setRunDirty(true); setRunSaved(false);
  }

  function toggleRemark(filePath: string) {
    setOpenRemarks((current) => {
      const next = new Set(current);
      if (next.has(filePath)) next.delete(filePath); else next.add(filePath);
      return next;
    });
  }

  async function addCase() {
    if (!selected) return;
    const filePath = await prompt({ title: "Add test case", label: "Feature path", confirmLabel: "Add" });
    if (!filePath?.trim()) return;
    if (selected.results.some((item) => item.file_path === filePath.trim())) { onError(`Case '${filePath.trim()}' is already in this run.`); return; }
    setSelected({ ...selected, results: [...selected.results, { file_path: filePath.trim(), result: "PENDING", remark: "" }] });
    setRunDirty(true); setRunSaved(false); onError("");
  }

  function removeCase(filePath: string) {
    if (!selected) return;
    setSelected({ ...selected, results: selected.results.filter((item) => item.file_path !== filePath) });
    setRunDirty(true); setRunSaved(false);
  }

  async function saveRun() {
    if (!selected || !selectedPath) return;
    const [owner, , group, fileName] = selectedPath.split("/");
    try {
      await api(`/api/runs/${[owner, group, fileName].map(encodeURIComponent).join("/")}`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(selected) });
      setRunDirty(false); setRunSaved(true); window.setTimeout(() => setRunSaved(false), 1500); await load();
      onError("");
    } catch (cause) { onError((cause as Error).message); }
  }

  async function reloadRun(discard = false) {
    if (!selected || !selectedPath) return;
    if (runDirty && !discard && !(await confirm({ title: "Reload test run?", description: "Reload from disk? Your unsaved changes will be discarded.", confirmLabel: "Reload" }))) return;
    const [owner, , group, fileName] = selectedPath.split("/");
    await open(selectedPath, owner, group, fileName);
  }

  async function createGroup() {
    const owner = project || scopeProject || await prompt({ title: "Create run group", label: "Project name", confirmLabel: "Continue" }) || "";
    if (!owner) { onError("Select a project before creating a run group."); return; }
    const group = await prompt({ title: "Create run group", label: "Run group name", confirmLabel: "Create" });
    if (!group) return;
    try { await api(`/api/runs/${encodeURIComponent(owner)}/groups`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name: group }) }); await load(); }
    catch (cause) { onError((cause as Error).message); }
  }

  async function createRun() {
    const owner = project || scopeProject || await prompt({ title: "Create test run", label: "Project name", confirmLabel: "Continue" }) || "";
    if (!owner) { onError("Select a project before creating a run."); return; }
    const group = await prompt({ title: "Create test run", label: "Existing run group", confirmLabel: "Continue" });
    const fileName = await prompt({ title: "Create test run", label: "Run file name", confirmLabel: "Continue" });
    const name = await prompt({ title: "Create test run", label: "Run display name", confirmLabel: "Create" });
    if (!group || !fileName || !name) return;
    try {
      await api("/api/runs", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ project: owner, group, file_name: fileName, name, case_paths: [] }) });
      await load();
    } catch (cause) { onError((cause as Error).message); }
  }

  return <div className="split-view">{runImporting && <RunImportForm onCancel={() => setRunImporting(false)} onCreated={async (owner, group, fileName) => { setRunImporting(false); await load(); await open(`${owner}/test-run/${group}/${fileName}`, owner, group, fileName); }} />}<Card><CardHeader><div><strong>Test runs</strong><div className="muted">{project || "All projects"}</div></div><div className="actions">{!project && <select aria-label="Run project scope" value={scopeProject} onChange={(event) => setScopeProject(event.target.value)}><option value="">All projects</option>{projects.map((owner) => <option key={owner}>{owner}</option>)}</select>}<button className="button" onClick={() => setRunImporting(true)}>Import Allure</button><button className="button" onClick={() => void createGroup()}>New group</button><button className="button primary" onClick={() => void createRun()}>New run</button><Button onClick={() => void load()}>{loading ? "Loading…" : "Refresh"}</Button></div></CardHeader><CardContent><div className="table-wrap"><Table className="run-table"><thead><tr><th>Run</th><th>Project</th><th>Group</th><th>Cases</th><th>Created</th></tr></thead><tbody>{runs.filter((run) => !scopeProject || run.project === scopeProject || project).map((run) => <tr className="clickable-row" key={run.path} tabIndex={0} aria-label={`Open ${run.name || run.file_name}`} onClick={() => void open(run.path, run.project ?? project, run.group, run.file_name)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); void open(run.path, run.project ?? project, run.group, run.file_name); } }}><td>{run.name || run.file_name}</td><td>{run.project ?? project}</td><td>{run.group}</td><td>{run.case_count}</td><td>{run.created_at || <span className="muted">Malformed</span>}</td></tr>)}</tbody></Table></div>{!runs.length && <p className="muted">No runs found.</p>}</CardContent></Card>
    {runLoading && <Card><CardContent><div className="loading-state" role="status"><LoaderCircle className="loading-icon" size={18} aria-hidden="true" /><span>Loading test run…</span></div></CardContent></Card>}
    {selected && <Card><CardHeader><div><strong>{selected.name}</strong>{runDirty && <span className="dirty-indicator">Unsaved</span>}{runSaved && !runDirty && <span className="saved-indicator">Saved</span>}</div><div className="actions"><Button onClick={() => void reloadRun()}>Reload</Button><Button variant="primary" disabled={!runDirty} onClick={() => void saveRun()}>Save</Button></div></CardHeader><CardContent><label className="editor-field"><span>Description</span><textarea value={selected.description} onChange={(event) => { setSelected({ ...selected, description: event.target.value }); setRunDirty(true); setRunSaved(false); }} /></label><div className="editor-section-heading" style={{ marginTop: ".9rem" }}><strong>Cases</strong><Button onClick={addCase}>Add test case</Button></div><div className="run-cases">{selected.results.map((item) => <div className="run-case" key={`${item.file_path}:${item.example?.table ?? ""}:${item.example?.row ?? ""}`}><div><span title={item.file_path}>{scenarioNames[item.file_path] ?? "Scenario unavailable"}</span>{openRemarks.has(item.file_path) && <textarea className="run-remark" rows={2} value={item.remark} onChange={(event) => updateRemark(item.file_path, event.target.value)} placeholder="Remark" />}</div><div className="actions"><select className={`case-status status-${item.result.toLowerCase()}`} value={item.result} onChange={(event) => updateResult(item.file_path, event.target.value)}><option>PENDING</option><option>EXECUTING</option><option>PASSED</option><option>FAILED</option><option>SKIPPED</option></select><button className="icon-button" aria-label={`${openRemarks.has(item.file_path) ? "Hide" : "Add"} remark for ${scenarioNames[item.file_path] ?? "scenario"}`} title={openRemarks.has(item.file_path) ? "Hide remark" : "Add remark"} onClick={() => toggleRemark(item.file_path)}><Plus size={16} aria-hidden="true" /></button><button className="icon-button danger-icon" aria-label={`Remove ${item.file_path}`} title="Remove test case" onClick={() => removeCase(item.file_path)}><Trash2 size={16} aria-hidden="true" /></button></div></div>)}</div>{!selected.results.length && <p className="muted">This run has no cases.</p>}</CardContent></Card>}
  </div>;
}

const REPORT_TYPES = ["enum_ranking", "tag_ranking", "case_trend", "tag_inventory"] as const;
const REPORT_STATUSES = ["PENDING", "EXECUTING", "PASSED", "FAILED", "SKIPPED"];

function reportFileStem(title: string): string { return title.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "report"; }

function ReportCreateForm({ project, onCancel, onCreated, onError }: { project: string; onCancel: () => void; onCreated: () => void | Promise<void>; onError: (message: string) => void }) {
  const [title, setTitle] = useState("");
  const [fileName, setFileName] = useState("");
  const [type, setType] = useState<(typeof REPORT_TYPES)[number]>("enum_ranking");
  const [status, setStatus] = useState("PASSED");
  const [kind, setKind] = useState("");
  const [casePath, setCasePath] = useState("");
  const [tag, setTag] = useState("");
  const [scope, setScope] = useState(project);
  const [kinds, setKinds] = useState<string[]>([]);
  const [formError, setFormError] = useState("");
  useEffect(() => { void api<Record<string, Record<string, string>>>(`/api/enums/${encodeURIComponent(project)}`).then((vocabulary) => { const next = Object.keys(vocabulary); setKinds(next); setKind((current) => current || next[0] || ""); }).catch(() => setKinds([])); }, [project]);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!title.trim()) { setFormError("Report title is required."); return; }
    if (type === "enum_ranking" && !kind) { setFormError("Select an enum kind."); return; }
    if (type === "case_trend" && !casePath.trim()) { setFormError("Case path is required."); return; }
    if (type === "tag_inventory" && (!scope.trim() || !tag.trim())) { setFormError("Scope and tag are required."); return; }
    const body = { file_name: `${(fileName.trim() || reportFileStem(title)).replace(/\.yaml$/i, "")}.yaml`, title: title.trim(), type, created_at: "", run_paths: [], status: type === "enum_ranking" || type === "tag_ranking" ? status : "", kind: type === "enum_ranking" ? kind : "", case_path: type === "case_trend" ? casePath.trim() : "", tag: type === "tag_inventory" ? tag.trim() : "", scope: type === "tag_inventory" ? scope.trim() : "" };
    try { setFormError(""); await api(`/api/reports/${encodeURIComponent(project)}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }); onError(""); await onCreated(); }
    catch (cause) { setFormError((cause as Error).message); onError(""); }
  }
  return <Card><CardHeader><strong>New report</strong><Button onClick={onCancel}>Cancel</Button></CardHeader><CardContent><form className="report-form" onSubmit={(event) => void submit(event)}><label className="editor-field"><span>Title</span><Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Report title" /></label><label className="editor-field"><span>File name</span><Input value={fileName} onChange={(event) => setFileName(event.target.value)} placeholder={`${reportFileStem(title) || "report"}.yaml`} /></label><label className="editor-field"><span>Type</span><select value={type} onChange={(event) => setType(event.target.value as (typeof REPORT_TYPES)[number])}>{REPORT_TYPES.map((item) => <option key={item}>{item}</option>)}</select></label>{(type === "enum_ranking" || type === "tag_ranking") && <label className="editor-field"><span>Status</span><select value={status} onChange={(event) => setStatus(event.target.value)}>{REPORT_STATUSES.map((item) => <option key={item}>{item}</option>)}</select></label>}{type === "enum_ranking" && <label className="editor-field"><span>Enum kind</span><select value={kind} onChange={(event) => setKind(event.target.value)}><option value="">Select a kind</option>{kinds.map((item) => <option key={item}>{item}</option>)}</select></label>}{type === "case_trend" && <label className="editor-field"><span>Case path</span><Input value={casePath} onChange={(event) => setCasePath(event.target.value)} placeholder={`${project}/API/example.feature`} /></label>}{type === "tag_inventory" && <><label className="editor-field"><span>Scope folder</span><Input value={scope} onChange={(event) => setScope(event.target.value)} placeholder={project} /></label><label className="editor-field"><span>Tag</span><Input value={tag} onChange={(event) => setTag(event.target.value)} placeholder="release" /></label></>}{formError && <div className="notice">{formError}</div>}<div className="actions"><Button variant="primary" type="submit">Create report</Button><Button type="button" onClick={onCancel}>Cancel</Button></div></form></CardContent></Card>;
}

function percent(value: unknown): string { return typeof value === "number" ? `${Math.round(value * 100)}%` : "—"; }

function reportRunUrl(path: string): string {
  const [project, area, group, fileName, ...extra] = path.split("/");
  if (!project || area !== "test-run" || !group || !fileName || extra.length) return "";
  return `/?${new URLSearchParams({ tab: "runs", project, run: `${group}/${fileName}` }).toString()}`;
}

function openReportRun(path: string) {
  const url = reportRunUrl(path);
  if (url) window.location.assign(url);
}

function ReportCases({ cases }: { cases: unknown[] }) {
  const grouped = new Map<string, Array<{ path: string; name: string }>>();
  for (const item of cases) {
    if (!item || typeof item !== "object") continue;
    const row = item as { file_path?: unknown; scenario_name?: unknown };
    const path = typeof row.file_path === "string" ? row.file_path : "(unknown)";
    const folder = path.split("/").slice(0, -1).join("/") || "Project root";
    const entries = grouped.get(folder) ?? [];
    entries.push({ path, name: typeof row.scenario_name === "string" ? row.scenario_name : "" });
    grouped.set(folder, entries);
  }
  if (!grouped.size) return <span className="muted">No matching cases.</span>;
  return <div className="report-case-groups">{[...grouped.entries()].map(([folder, entries]) => <div key={folder}><strong>{folder}</strong><ul>{entries.map((entry) => <li key={`${entry.path}:${entry.name}`}><code>{entry.path}</code>{entry.name && <span className="muted"> — {entry.name}</span>}</li>)}</ul></div>)}</div>;
}

function ReportComputedView({ view }: { view: Record<string, unknown> }) {
  const warnings = Array.isArray(view.warnings) ? view.warnings.filter((item): item is string => typeof item === "string") : [];
  const type = typeof view.type === "string" ? view.type : "";
  const trend = Array.isArray(view.trend) ? view.trend.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object")) : [];
  const buckets = Array.isArray(view.buckets) ? view.buckets.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object")) : [];
  return <div className="report-view">{warnings.length > 0 && <div className="notice warning"><strong>Warnings</strong><ul>{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}{type === "case_trend" ? <>{view.tombstoned && <div className="notice warning">The selected case is missing from the current directory.</div>}{trend.length ? <div className="table-wrap"><table className="report-table"><thead><tr><th>Run</th><th>Created</th><th>Result</th></tr></thead><tbody>{trend.map((item, index) => {
    const result = typeof item.result === "string" ? item.result : "—";
    const path = typeof item.run_path === "string" ? item.run_path : "";
    const interactive = Boolean(reportRunUrl(path));
    return <tr className={interactive ? "clickable-row" : undefined} key={`${String(item.run_path ?? index)}`} tabIndex={interactive ? 0 : undefined} onClick={interactive ? () => openReportRun(path) : undefined} onKeyDown={interactive ? (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openReportRun(path); } } : undefined}><td>{String(item.run_name ?? item.run ?? "")}</td><td>{String(item.created_at ?? "")}</td><td><span className={`status status-${result.toLowerCase()}`}>{result}</span></td></tr>;
  })}</tbody></table></div> : <p className="muted">No runs selected.</p>}</> : buckets.length ? <div className="report-buckets">{buckets.map((bucket) => { const value = String(bucket.value ?? ""); const label = String(bucket.label ?? value); const cases = Array.isArray(bucket.cases) ? bucket.cases : []; return <details key={value}><summary><span>{label}</span><span className="muted">{String(bucket.count ?? cases.length)} ({percent(bucket.pct)})</span></summary><ReportCases cases={cases} /></details>; })}</div> : <p className="muted">No matching data.</p>}</div>;
}

function ReportsPanel({ project, initialReport, onError }: { project: string; initialReport: string; onError: (message: string) => void }) {
  const { confirm } = useDialog();
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [projects, setProjects] = useState<string[]>([]);
  const [scopeProject, setScopeProject] = useState(project);
  const [selected, setSelected] = useState<{ summary: ReportSummary; definition: Record<string, unknown>; view: Record<string, unknown> } | null>(null);
  const [reportDraft, setReportDraft] = useState<Record<string, unknown> | null>(null);
  const [availableRuns, setAvailableRuns] = useState<Array<{ path: string; name: string; group: string; created_at: string }>>([]);
  const [runToAdd, setRunToAdd] = useState("");
  const [reportDirty, setReportDirty] = useState(false);
  const [reportSaved, setReportSaved] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const initialReportOpened = useRef("");
  const load = useCallback(async () => {
    try {
      const tree = await api<{ children: TreeNode[] }>("/api/tree");
      const targets = project ? [project] : tree.children.filter((node) => node.type === "folder" && node.path.split("/").filter(Boolean).length === 1).map((node) => node.name);
      setProjects(targets);
      const responses = await Promise.all(targets.map(async (owner) => (await api<{ reports: ReportSummary[] }>(`/api/reports/${encodeURIComponent(owner)}`)).reports.map((report) => ({ ...report, project: owner }))));
      setReports(responses.flat());
      onError("");
    } catch (cause) { onError((cause as Error).message); }
  }, [project, onError]);
  useEffect(() => { if (project) setScopeProject(project); void load(); setSelected(null); setReportDraft(null); setReportDirty(false); setReportSaved(false); }, [load, project]);
  async function open(summary: ReportSummary) {
    setReportLoading(true); setSelected(null); setReportDraft(null);
    try {
      const owner = summary.project ?? project ?? scopeProject;
      if (!owner) return;
      const base = `/api/reports/${[owner, summary.file_name].map(encodeURIComponent).join("/")}`;
      const [definition, view] = await Promise.all([api<Record<string, unknown>>(base), api<Record<string, unknown>>(`${base}/view`)]);
      setSelected({ summary, definition, view });
      setReportDraft(definition);
      setReportDirty(false);
      setReportSaved(false);
      setRunToAdd("");
      if (["enum_ranking", "tag_ranking", "case_trend"].includes(summary.type)) {
        setAvailableRuns((await api<{ runs: Array<{ path: string; name: string; group: string; created_at: string }> }>(`/api/runs/${encodeURIComponent(owner)}`)).runs);
      } else setAvailableRuns([]);
      onError("");
    } catch (cause) { onError((cause as Error).message); }
    finally { setReportLoading(false); }
  }
  useEffect(() => {
    if (!initialReport || !reports.length || selected || initialReportOpened.current === initialReport) return;
    const match = reports.find((report) => report.file_name === initialReport && (!project || report.project === project));
    if (!match) return;
    initialReportOpened.current = initialReport;
    void open(match);
  }, [initialReport, project, reports, selected]);
  function updateDraft(patch: Record<string, unknown>) { setReportDraft((current) => current ? { ...current, ...patch } : current); setReportDirty(true); setReportSaved(false); }
  function runPaths(): string[] { return Array.isArray(reportDraft?.run_paths) ? reportDraft.run_paths.filter((value): value is string => typeof value === "string") : []; }
  function addRun() { if (!runToAdd || runPaths().includes(runToAdd)) return; if (runPaths().length >= 10) { onError("A report may reference at most 10 runs."); return; } updateDraft({ run_paths: [...runPaths(), runToAdd] }); setRunToAdd(""); onError(""); }
  async function saveReport() {
    if (!selected || !reportDraft) return;
    try {
      const body = { ...reportDraft, type: selected.definition.type, created_at: selected.definition.created_at };
      const owner = selected.summary.project ?? project ?? scopeProject;
      if (!owner) return;
      const base = `/api/reports/${[owner, selected.summary.file_name].map(encodeURIComponent).join("/")}`;
      await api(base, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      await open(selected.summary);
      await load();
      setReportSaved(true);
      window.setTimeout(() => setReportSaved(false), 1500);
    } catch (cause) { onError((cause as Error).message); }
  }
  async function reloadReport(discard = false) {
    if (!selected) return;
    if (reportDirty && !discard && !(await confirm({ title: "Reload report?", description: "Reload from disk? Your unsaved changes will be discarded.", confirmLabel: "Reload" }))) return;
    await open(selected.summary);
  }
  function beginCreate() {
    if (project || scopeProject) setCreating(true);
    else onError("Select a project before creating a report.");
  }
  const runSet = reportDraft && ["enum_ranking", "tag_ranking", "case_trend"].includes(String(reportDraft.type));
  const visibleReports = reports.filter((report) => Boolean(project) || !scopeProject || report.project === scopeProject);
  return <div className="split-view">
    {creating && <ReportCreateForm project={project || scopeProject} onCancel={() => setCreating(false)} onCreated={async () => { setCreating(false); await load(); }} onError={onError} />}
    <Card><CardHeader><div><strong>Reports</strong><div className="muted">{project || "All projects"}</div></div><div className="actions">{!project && <select aria-label="Report project scope" value={scopeProject} onChange={(event) => setScopeProject(event.target.value)}><option value="">All projects</option>{projects.map((owner) => <option key={owner}>{owner}</option>)}</select>}<Button variant="primary" onClick={beginCreate}>New report</Button><button className="button" onClick={() => void load()}>Refresh</button></div></CardHeader><CardContent><div className="table-wrap"><Table><thead><tr><th>Report</th><th>Project</th><th>Type</th><th>Source</th><th>Created</th></tr></thead><tbody>{visibleReports.map((report) => <tr className="clickable-row" key={`${report.project ?? ""}/${report.file_name}`} tabIndex={0} aria-label={`Open ${report.title || report.file_name}`} onClick={() => void open(report)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); void open(report); } }}><td>{report.title || report.file_name}</td><td>{report.project ?? project}</td><td>{report.type || <span className="muted">Malformed</span>}</td><td>{report.source}</td><td>{report.created_at}</td></tr>)}</tbody></Table></div>{!visibleReports.length && <p className="muted">No reports found.</p>}</CardContent></Card>
    {reportLoading && <Card><CardContent><div className="loading-state" role="status"><LoaderCircle className="loading-icon" size={18} aria-hidden="true" /><span>Loading report…</span></div></CardContent></Card>}
    {selected && reportDraft && <Card><CardHeader><div><strong>{selected.summary.title || selected.summary.file_name}<span className="report-type"> {selected.summary.type}</span></strong>{reportDirty && <span className="dirty-indicator">Unsaved</span>}{reportSaved && !reportDirty && <span className="saved-indicator">Saved</span>}</div><div className="actions"><Button onClick={() => void reloadReport()}>Reload</Button><Button variant="primary" disabled={!reportDirty} onClick={() => void saveReport()}>Save</Button></div></CardHeader><CardContent><section className="editor-section report-source-editor"><div className="editor-section-heading"><strong>Data source</strong><span className="muted">{runSet ? `${runPaths().length}/10 runs` : "Folder scope"}</span></div>{runSet ? <><div className="inline-form"><select aria-label="Run to add" value={runToAdd} onChange={(event) => setRunToAdd(event.target.value)}><option value="">Select a run</option>{availableRuns.filter((run) => !runPaths().includes(run.path)).map((run) => <option key={run.path} value={run.path}>{run.group} / {run.name || run.path} ({run.created_at})</option>)}</select><Button onClick={addRun} disabled={!runToAdd || runPaths().length >= 10}>Add run</Button></div><div className="report-source-list">{runPaths().map((path) => {
      const interactive = Boolean(reportRunUrl(path));
      return <div className={`report-source-row ${interactive ? "clickable-row" : ""}`} key={path} role={interactive ? "link" : undefined} tabIndex={interactive ? 0 : undefined} onClick={interactive ? () => openReportRun(path) : undefined} onKeyDown={interactive ? (event) => { if (event.target !== event.currentTarget || (event.key !== "Enter" && event.key !== " ")) return; event.preventDefault(); openReportRun(path); } : undefined}><code>{path}</code><button className="link-button danger-text" onClick={(event) => { event.stopPropagation(); updateDraft({ run_paths: runPaths().filter((current) => current !== path) }); }}>remove</button></div>;
    })}{!runPaths().length && <span className="muted">No runs selected. Add a run to populate this report.</span>}</div></> : <label className="editor-field"><span>Scope folder</span><Input value={typeof reportDraft.scope === "string" ? reportDraft.scope : ""} onChange={(event) => updateDraft({ scope: event.target.value })} /></label>}</section><h3>Definition</h3><pre className="json-view">{JSON.stringify(reportDraft, null, 2)}</pre><h3>Computed view</h3><ReportComputedView view={selected.view} /></CardContent></Card>}
  </div>;
}

function ProjectEnumsPanel({ project, onError }: { project: string; onError: (message: string) => void }) {
  const [vocabulary, setVocabulary] = useState<EnumVocabulary>({});
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [missing, setMissing] = useState(false);
  const [newKind, setNewKind] = useState("");
  const [newEntry, setNewEntry] = useState<Record<string, { key: string; label: string }>>({});
  const load = useCallback(async () => { if (!project) return; try { const next = await api<EnumVocabulary>(`/api/enums/${encodeURIComponent(project)}`); setVocabulary(next); setLabels(Object.fromEntries(Object.keys(next).map((kind) => [kind, kind]))); setMissing(false); onError(""); } catch (cause) { setMissing(/not found/i.test((cause as Error).message)); onError((cause as Error).message); } }, [project, onError]);
  useEffect(() => { void load(); }, [load]);
  async function saveVocabulary(next: EnumVocabulary) { try { await api(`/api/enums/${encodeURIComponent(project)}`, { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify(next) }); setVocabulary(next); onError(""); } catch (cause) { onError((cause as Error).message); } }
  async function addKind() { const kind = newKind.trim(); if (!kind || vocabulary[kind]) return; await saveVocabulary({ ...vocabulary, [kind]: {} }); setLabels((current) => ({ ...current, [kind]: kind })); setNewKind(""); }
  async function addEntry(kind: string) { const entry = newEntry[kind]; if (!entry?.key.trim()) return; if (vocabulary[kind]?.[entry.key]) { onError(`Enum key '${entry.key}' already exists.`); return; } await saveVocabulary({ ...vocabulary, [kind]: { ...vocabulary[kind], [entry.key]: entry.label || entry.key } }); setNewEntry((current) => ({ ...current, [kind]: { key: "", label: "" } })); }
  async function saveLabels() { try { await api(`/api/enums/${encodeURIComponent(project)}/kind-labels`, { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify(labels) }); onError(""); } catch (cause) { onError((cause as Error).message); } }
  async function initialize() { try { const next = await api<EnumVocabulary>(`/api/enums/${encodeURIComponent(project)}`, { method: "POST" }); setVocabulary(next); setLabels({}); setMissing(false); onError(""); } catch (cause) { onError((cause as Error).message); } }
  async function removeEntry(kind: string, key: string) { const next = { ...vocabulary, [kind]: Object.fromEntries(Object.entries(vocabulary[kind]).filter(([entry]) => entry !== key)) }; await saveVocabulary(next); }
  return <Card><CardHeader><div><strong>Project enums</strong><div className="muted">IDs remain stable; labels are display metadata.</div></div><div className="actions">{missing && <button className="button primary" onClick={() => void initialize()}>Initialize enums</button>}<button className="button" onClick={() => void load()}>Refresh</button><Button variant="primary" disabled={missing} onClick={() => void saveLabels()}>Save kind labels</Button></div></CardHeader><CardContent><div className="inline-form"><Input value={newKind} onChange={(event) => setNewKind(event.target.value)} placeholder="New kind ID" /><Button disabled={missing} onClick={() => void addKind()}>Add kind</Button></div><div className="enum-grid">{Object.entries(vocabulary).map(([kind, entries]) => <section className="enum-section" key={kind}><div className="enum-heading"><Input value={labels[kind] ?? kind} onChange={(event) => setLabels((current) => ({ ...current, [kind]: event.target.value }))} aria-label={`${kind} display label`} /><code>{kind}</code></div><div className="enum-entries">{Object.entries(entries).map(([key, label]) => <div className="enum-entry" key={key}><code>{key}</code><span>{label}</span><button className="link-button danger-text" onClick={() => void removeEntry(kind, key)}>remove</button></div>)}</div><div className="inline-form"><Input value={newEntry[kind]?.key ?? ""} onChange={(event) => setNewEntry((current) => ({ ...current, [kind]: { key: event.target.value, label: current[kind]?.label ?? "" } }))} placeholder="Entry key" /><Input value={newEntry[kind]?.label ?? ""} onChange={(event) => setNewEntry((current) => ({ ...current, [kind]: { key: current[kind]?.key ?? "", label: event.target.value } }))} placeholder="Display label" /><Button onClick={() => void addEntry(kind)}>Add entry</Button></div></section>)}</div>{!Object.keys(vocabulary).length && <p className="muted">{missing ? "Initialize enums to create the project vocabulary." : "No enum kinds. Add one above."}</p>}</CardContent></Card>;
}

function EnumsPanel({ project, onError }: { project: string; onError: (message: string) => void }) {
  const [projects, setProjects] = useState<string[]>([]);
  const [chosen, setChosen] = useState("");
  const loadProjects = useCallback(async () => {
    try { const tree = await api<{ children: TreeNode[] }>("/api/tree"); setProjects(tree.children.filter((node) => node.type === "folder" && node.path.split("/").filter(Boolean).length === 1).map((node) => node.name)); }
    catch (cause) { onError((cause as Error).message); }
  }, [onError]);
  useEffect(() => { setChosen(project); }, [project]);
  useEffect(() => { void loadProjects(); }, [loadProjects]);
  if (chosen) return <div className="stack"><div className="enum-project-picker"><label><span>Project</span><select aria-label="Enum project" value={chosen} onChange={(event) => setChosen(event.target.value)}><option value="">Select a project</option>{projects.map((name) => <option key={name}>{name}</option>)}</select></label></div><ProjectEnumsPanel key={chosen} project={chosen} onError={onError} /></div>;
  return <Card><CardHeader><strong>Project enums</strong><Button onClick={() => void loadProjects()}>Refresh</Button></CardHeader><CardContent><label className="editor-field"><span>Select a project</span><select aria-label="Enum project" value={chosen} onChange={(event) => setChosen(event.target.value)}><option value="">Choose…</option>{projects.map((name) => <option key={name}>{name}</option>)}</select></label>{!projects.length && <p className="muted">No projects found.</p>}</CardContent></Card>;
}

type StepPayload = FeaturePayload["scenario"]["steps"][number];
type ExamplePayload = FeaturePayload["scenario"]["examples"][number];

function TagEditor({ tags, onChange, label, placeholder }: { tags: string[]; onChange: (tags: string[]) => void; label: string; placeholder: string }) {
  const [input, setInput] = useState("");
  const isComposing = useRef(false);
  const addTag = () => {
    const tag = input.trim().replace(/^@+/, "");
    if (!tag || /[\s@,]/.test(tag)) return;
    onChange([...tags, tag]);
    setInput("");
  };
  return <div className="tag-editor"><div className="tag-chips">{tags.map((tag, index) => <span className="tag tag-chip" key={`${tag}-${index}`}>@{tag}<button type="button" aria-label={`Remove tag @${tag}`} title={`Remove @${tag}`} onClick={() => onChange(tags.filter((_, tagIndex) => tagIndex !== index))}><X size={13} aria-hidden="true" /></button></span>)}</div><input aria-label={label} placeholder={placeholder} value={input} onChange={(event) => setInput(event.target.value)} onCompositionStart={() => { isComposing.current = true; }} onCompositionEnd={() => { isComposing.current = false; }} onKeyDown={(event) => { if (event.key === "Enter" && !isComposing.current && !event.nativeEvent.isComposing) { event.preventDefault(); addTag(); } }} /></div>;
}

function tableText(table: string[][] | null): string {
  return table?.map((row) => row.join(" | ")).join("\n") ?? "";
}

function parseTable(value: string): string[][] | null {
  if (!value.trim()) return null;
  return value.split("\n").map((row) => row.split("|").map((cell) => cell.trim()));
}

function StepEditor({ step, index, onChange, onRemove }: { step: StepPayload; index: number; onChange: (step: StepPayload) => void; onRemove: () => void }) {
  const dataTableHint = "Add data table, 1 row per line, split by |";
  const resizeDataTable = (element: HTMLTextAreaElement | null) => { if (element) { element.style.height = "auto"; element.style.height = `${element.scrollHeight + element.offsetHeight - element.clientHeight}px`; } };
  return <div className="step-editor"><div className="step-fields"><select aria-label={`Step ${index + 1} keyword`} value={step.keyword} onChange={(event) => onChange({ ...step, keyword: event.target.value })}>{["Given", "When", "Then", "And", "But"].map((keyword) => <option key={keyword}>{keyword}</option>)}</select><input aria-label={`Step ${index + 1} text`} value={step.text} onChange={(event) => onChange({ ...step, text: event.target.value })} placeholder="Step text" />{!step.data_table && <button className="icon-button data-table-add" aria-label={dataTableHint} title={dataTableHint} onClick={() => onChange({ ...step, data_table: [[""]] })}><Plus size={16} aria-hidden="true" /></button>}<button className="icon-button danger-icon" aria-label={`Remove step ${index + 1}`} title="Remove step" onClick={onRemove}><Trash2 size={16} aria-hidden="true" /></button></div>{step.data_table && <textarea className="data-table-editor" ref={resizeDataTable} aria-label={`Step ${index + 1} data table`} value={tableText(step.data_table)} onChange={(event) => onChange({ ...step, data_table: parseTable(event.target.value) })} placeholder="Data table, 1 row per line, split by |" />}</div>;
}

function StructuredFeatureEditor({ draft, onChange }: { draft: string; onChange: (next: string) => void }) {
  let value: FeaturePayload;
  try { value = JSON.parse(draft) as FeaturePayload; } catch { return <div className="notice">Structured draft is not valid JSON.</div>; }
  const write = (next: FeaturePayload) => onChange(JSON.stringify(next, null, 2));
  const updateScenario = (next: Partial<FeaturePayload["scenario"]>) => write({ ...value, scenario: { ...value.scenario, ...next } });
  const updateSteps = (section: "background" | "scenario", steps: StepPayload[]) => section === "background" ? write({ ...value, background: { steps } }) : updateScenario({ steps });
  const editStep = (section: "background" | "scenario", index: number, step: StepPayload) => {
    const steps = section === "background" ? value.background.steps : value.scenario.steps;
    updateSteps(section, steps.map((current, stepIndex) => stepIndex === index ? step : current));
  };
  const removeStep = (section: "background" | "scenario", index: number) => {
    const steps = section === "background" ? value.background.steps : value.scenario.steps;
    updateSteps(section, steps.filter((_, stepIndex) => stepIndex !== index));
  };
  const addStep = (section: "background" | "scenario") => {
    const steps = section === "background" ? value.background.steps : value.scenario.steps;
    updateSteps(section, [...steps, { keyword: "Given", text: "", data_table: null }]);
  };
  const updateExample = (index: number, example: ExamplePayload) => updateScenario({ examples: value.scenario.examples.map((current, exampleIndex) => exampleIndex === index ? example : current) });
  return <div className="structured-editor"><div className="editor-field"><textarea className="feature-description" rows={2} aria-label="Feature description" placeholder="Description" value={value.description} onChange={(event) => write({ ...value, description: event.target.value })} /></div><div className="editor-field"><TagEditor tags={value.tags} onChange={(tags) => write({ ...value, tags })} label="Feature tags" placeholder="Add feature tag" /></div><section className="editor-section"><div className="editor-section-heading"><strong>Background</strong><button className="button" onClick={() => addStep("background")}>Add step</button></div>{value.background.steps.map((step, index) => <StepEditor key={`background-${index}`} step={step} index={index} onChange={(next) => editStep("background", index, next)} onRemove={() => removeStep("background", index)} />)}{!value.background.steps.length && <span className="muted">No background steps.</span>}</section><section className="editor-section"><div className="editor-section-heading"><button className="scenario-kind-toggle" type="button" aria-pressed={value.scenario.kind === "outline"} title={`Change to ${value.scenario.kind === "scenario" ? "Scenario Outline" : "Scenario"}`} onClick={() => updateScenario({ kind: value.scenario.kind === "scenario" ? "outline" : "scenario", examples: value.scenario.kind === "scenario" ? value.scenario.examples : [] })}>{value.scenario.kind === "outline" ? "Scenario Outline" : "Scenario"}</button></div><div className="editor-field"><input aria-label="Scenario name" placeholder="Scenario name" value={value.scenario.name} onChange={(event) => updateScenario({ name: event.target.value })} /></div><div className="editor-field"><TagEditor tags={value.scenario.tags} onChange={(tags) => updateScenario({ tags })} label="Scenario tags" placeholder="Add scenario tag" /></div>{value.scenario.steps.map((step, index) => <StepEditor key={`scenario-${index}`} step={step} index={index} onChange={(next) => editStep("scenario", index, next)} onRemove={() => removeStep("scenario", index)} />)}<button className="new-step" type="button" onClick={() => addStep("scenario")}><Plus size={16} aria-hidden="true" />New step</button></section>{value.scenario.kind === "outline" && <section className="editor-section"><div className="editor-section-heading"><strong>Examples</strong><button className="button" onClick={() => updateScenario({ examples: [...value.scenario.examples, { tags: [], name: "", header: ["value"], rows: [[""]] }] })}>Add examples</button></div>{value.scenario.examples.map((example, index) => <div className="example-editor" key={`example-${index}`}><div className="step-fields"><input value={example.name} onChange={(event) => updateExample(index, { ...example, name: event.target.value })} placeholder="Examples name" /><button className="link-button danger-text" onClick={() => updateScenario({ examples: value.scenario.examples.filter((_, exampleIndex) => exampleIndex !== index) })}>remove</button></div><TagEditor tags={example.tags} onChange={(tags) => updateExample(index, { ...example, tags })} label={`Example ${index + 1} tags`} placeholder="Add example tag" /><textarea value={example.header.join(" | ")} onChange={(event) => updateExample(index, { ...example, header: parseTable(event.target.value)?.[0] ?? [] })} placeholder="Header cells separated by |" /><textarea value={example.rows.map((row) => row.join(" | ")).join("\n")} onChange={(event) => updateExample(index, { ...example, rows: parseTable(event.target.value) ?? [] })} placeholder="One example row per line; cells separated by |" /></div>)}{!value.scenario.examples.length && <span className="muted">An outline needs at least one examples block before saving.</span>}</section>}</div>;
}

function cleanDataTable(table: string[][] | null): string[][] | null {
  if (!table?.length) return null;
  const isEmpty = (row: string[]) => row.every((cell) => !cell.trim());
  if (table.every(isEmpty)) return null;
  const [header, ...rows] = table;
  return [header, ...rows.filter((row) => !isEmpty(row))];
}

function cleanFeatureForSave(feature: FeaturePayload): FeaturePayload {
  const cleanSteps = (steps: StepPayload[]) => steps.filter((step) => step.text.trim()).map((step) => ({ ...step, data_table: cleanDataTable(step.data_table) }));
  const examples = feature.scenario.examples.map((example) => ({ ...example, rows: example.rows.filter((row) => !row.every((cell) => !cell.trim())) }));
  if (feature.scenario.kind === "outline" && examples.length === 0) throw new Error("outline_examples");
  return { ...feature, background: { steps: cleanSteps(feature.background.steps) }, scenario: { ...feature.scenario, steps: cleanSteps(feature.scenario.steps), examples } };
}

function readViewFromUrl(): { tab: Tab; path: string; project: string } {
  if (typeof window === "undefined") return { tab: "directory", path: "", project: "" };
  const params = new URLSearchParams(window.location.search);
  const candidate = params.get("tab");
  const tab: Tab = candidate === "runs" || candidate === "reports" || candidate === "enums" || candidate === "directory" ? candidate : "directory";
  const path = params.get("path") ?? "";
  return { tab, path, project: params.get("project") ?? path.split("/")[0] ?? "" };
}

function Workspace() {
  const { prompt, confirm } = useDialog();
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(() => new Set());
  const [selectedPath, setSelectedPath] = useState("");
  const [selectedProject, setSelectedProject] = useState("");
  const [listing, setListing] = useState<Listing | null>(null);
  const [feature, setFeature] = useState<Record<string, unknown> | null>(null);
  const [featureRaw, setFeatureRaw] = useState("");
  const [featureSnapshotRaw, setFeatureSnapshotRaw] = useState("");
  const [featureDraft, setFeatureDraft] = useState("");
  const [editorMode, setEditorMode] = useState<"structured" | "raw">("structured");
  const [moveTarget, setMoveTarget] = useState("");
  const [editorBanner, setEditorBanner] = useState<EditorBanner | null>(null);
  const [rawError, setRawError] = useState("");
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [query, setQuery] = useState("");
  const [searchScope, setSearchScope] = useState("all");
  const [searchMatch, setSearchMatch] = useState<"text" | "tag">("text");
  const [searchCase, setSearchCase] = useState(false);
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState<"file_name" | "scenario_name">("file_name");
  const [pageSize, setPageSize] = useState<20 | 50 | 100>(20);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [importOpen, setImportOpen] = useState(false);
  const [featureEdit, setFeatureEdit] = useState<FeatureEditRequest | null>(null);
  const [tab, setTab] = useState<Tab>("directory");
  const [deepLinkRun, setDeepLinkRun] = useState("");
  const [deepLinkReport, setDeepLinkReport] = useState("");
  const editorRef = useRef<{ path: string; feature: Record<string, unknown> | null; raw: string; dirty: boolean }>({ path: "", feature: null, raw: "", dirty: false });
  const searchTimer = useRef<number | null>(null);
  const hydratedUrl = useRef(false);
  const skipUrlSync = useRef(true);

  const reportError = useCallback((message: string) => setError(message), []);
  const refreshTree = useCallback(async () => { try { setTree((await api<{ children: TreeNode[] }>("/api/tree")).children); setError(""); } catch (cause) { setError((cause as Error).message); } }, []);
  const expandFolderPath = useCallback((path: string) => {
    const parts = path.split("/").filter(Boolean);
    if (!parts.length) return;
    setExpandedFolders((current) => {
      const next = new Set(current);
      for (let index = 1; index <= parts.length; index += 1) next.add(parts.slice(0, index).join("/"));
      return next;
    });
  }, []);
  const toggleFolder = useCallback((path: string) => {
    setExpandedFolders((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);
  const folderUrl = (path: string) => `/api/folders/${path ? `${path.split("/").map(encodeURIComponent).join("/")}/` : ""}contents`;
  const openFolder = useCallback(async (path: string) => { expandFolderPath(path); setSelectedPath(path); setSelectedProject(path.split("/")[0] ?? ""); setFeature(null); setPage(1); try { setListing(await api<Listing>(folderUrl(path))); setError(""); } catch (cause) { setError((cause as Error).message); } }, [expandFolderPath]);
  const openFeature = useCallback(async (node: TreeNode | string) => {
    const candidate = typeof node === "string" ? node : node.path;
    const path = candidate;
    expandFolderPath(path.split("/").slice(0, -1).join("/"));
    setSelectedPath(path); setSelectedProject(path.split("/")[0] ?? ""); setListing(null);
    try { const [structured, raw] = await Promise.all([api<Record<string, unknown>>(pathUrl("/api/files", path)), textApi(pathUrl("/api/files", `${path}/raw`))]); setFeature(structured); setFeatureDraft(JSON.stringify(structured, null, 2)); setFeatureRaw(raw); setFeatureSnapshotRaw(raw); setDirty(false); setSaved(false); setEditorBanner(null); setMoveTarget(""); setRawError(""); setError(""); }
    catch (cause) { setError((cause as Error).message); }
  }, [expandFolderPath]);

  useEffect(() => { editorRef.current = { path: selectedPath, feature, raw: featureRaw, dirty }; }, [selectedPath, feature, featureRaw, dirty]);
  const inspectExternalFeature = useCallback(async () => {
    const current = editorRef.current;
    if (!current.path || !current.feature) return;
    try {
      const [next, nextRaw] = await Promise.all([api<Record<string, unknown>>(pathUrl("/api/files", current.path)), textApi(pathUrl("/api/files", `${current.path}/raw`))]);
      const changed = JSON.stringify(next) !== JSON.stringify(current.feature) || nextRaw !== current.raw;
      if (!changed) return;
      if (current.dirty) { setEditorBanner({ message: "File changed externally while you have unsaved changes.", tone: "warning", conflict: true, removed: false }); return; }
      setFeature(next); setFeatureDraft(JSON.stringify(next, null, 2)); setFeatureRaw(nextRaw); setFeatureSnapshotRaw(nextRaw); setSaved(false); setEditorBanner({ message: "File was updated externally; the editor reloaded.", tone: "info", conflict: false, removed: false }); setError("");
    } catch (cause) {
      if (/enoent|not found|request failed \(404\)/i.test((cause as Error).message ?? "")) { setEditorBanner({ message: "This file was removed on disk.", tone: "error", conflict: false, removed: true }); return; }
      setError((cause as Error).message);
    }
  }, []);
  useEffect(() => {
    const view = readViewFromUrl();
    const urlParams = typeof window === "undefined" ? new URLSearchParams() : new URLSearchParams(window.location.search);
    const initialQuery = urlParams.get("q") ?? "";
    const initialScope = urlParams.get("scope") ?? "all";
    const initialMatch = urlParams.get("match") === "tag" ? "tag" : "text";
    const initialCase = ["true", "1", "yes"].includes((urlParams.get("case") ?? "false").toLowerCase());
    setTab(view.tab);
    setDeepLinkRun(urlParams.get("run") ?? "");
    setDeepLinkReport(urlParams.get("report") ?? "");
    if (view.project) setSelectedProject(view.project);
    if (initialQuery.trim() && view.tab === "directory") {
      setQuery(initialQuery);
      setSearchScope(initialScope);
      setSearchMatch(initialMatch);
      setSearchCase(initialCase);
      void runSearch(initialQuery, { scope: initialScope, match: initialMatch, caseSensitive: initialCase });
    } else if (view.path && view.tab === "directory") {
      if (!view.project) setSelectedProject(view.path.split("/")[0] ?? "");
      if (view.path.toLowerCase().endsWith(".feature")) void openFeature(view.path);
      else void openFolder(view.path);
    } else if (view.tab === "directory") {
      void openFolder("");
    }
    void refreshTree();
    hydratedUrl.current = true;
    const source = typeof window !== "undefined" ? new EventSource("/api/events") : null;
    const onChange = () => { void refreshTree(); void inspectExternalFeature(); };
    source?.addEventListener("change", onChange);
    return () => { source?.removeEventListener("change", onChange); source?.close(); };
  }, [refreshTree, openFolder, openFeature, inspectExternalFeature]);
  useEffect(() => {
    if (!hydratedUrl.current || typeof window === "undefined") return;
    if (skipUrlSync.current) {
      skipUrlSync.current = false;
      return;
    }
    const params = new URLSearchParams(window.location.search);
    params.set("tab", tab);
    if (tab === "directory" && selectedPath) params.set("path", selectedPath);
    else params.delete("path");
    if (selectedProject) params.set("project", selectedProject);
    else params.delete("project");
    if (tab !== "runs") params.delete("run");
    if (tab !== "reports") params.delete("report");
    const query = params.toString();
    window.history.replaceState(null, "", query ? `/?${query}` : "/");
  }, [tab, selectedPath, selectedProject]);
  useEffect(() => { const handler = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } }; window.addEventListener("beforeunload", handler); return () => window.removeEventListener("beforeunload", handler); }, [dirty]);
  useEffect(() => () => { if (searchTimer.current !== null) window.clearTimeout(searchTimer.current); }, []);

  const filteredFeatures = useMemo(() => { const rows = (listing?.features ?? []).filter((item) => !filter || item.scenario_name.toLowerCase().includes(filter.toLowerCase())); return [...rows].sort((a, b) => a[sort].localeCompare(b[sort], undefined, { sensitivity: "base" })); }, [listing, filter, sort]);
  const totalPages = Math.max(1, Math.ceil(filteredFeatures.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const paginatedFeatures = listing?.kind === "search" ? filteredFeatures : filteredFeatures.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const moveDestinations = useMemo(() => {
    const folders: string[] = [];
    const visit = (nodes: TreeNode[]) => nodes.forEach((node) => { if (node.type !== "folder") return; const depth = node.path.split("/").filter(Boolean).length; if (depth >= 2 && depth <= 10) folders.push(node.path); if (node.children) visit(node.children); });
    visit(tree);
    const currentParent = selectedPath.split("/").slice(0, -1).join("/");
    return folders.filter((path) => path !== currentParent).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
  }, [tree, selectedPath]);
  const searchScopes = useMemo(() => {
    const scopes: Array<{ value: string; label: string }> = [{ value: "all", label: "All projects" }];
    const visit = (nodes: TreeNode[]) => nodes.forEach((node) => {
      if (node.type !== "folder") return;
      const depth = node.path.split("/").filter(Boolean).length;
      if (depth === 1) scopes.push({ value: `project:${node.name}`, label: node.name });
      if (depth === 2) scopes.push({ value: `module:${node.path}`, label: node.path });
      if (node.children) visit(node.children);
    });
    visit(tree);
    return scopes;
  }, [tree]);
  const structuredDescription = useMemo(() => { try { const parsed = JSON.parse(featureDraft) as { description?: unknown }; return typeof parsed.description === "string" ? parsed.description : ""; } catch { return ""; } }, [featureDraft]);
  async function switchEditorMode(next: "structured" | "raw") {
    if (next === editorMode) return;
    if (dirty && !(await confirm({ title: "Switch editor mode?", description: "You have unsaved changes in the current tab. Switching tabs will discard them.", confirmLabel: "Switch" }))) return;
    if (dirty && feature) { setFeatureDraft(JSON.stringify(feature, null, 2)); setFeatureRaw(featureSnapshotRaw); setDirty(false); }
    setEditorMode(next);
  }
  function clearSearchTimer() { if (searchTimer.current !== null) { window.clearTimeout(searchTimer.current); searchTimer.current = null; } }
  async function runSearch(value = query, overrides: Partial<{ scope: string; match: "text" | "tag"; caseSensitive: boolean }> = {}) {
    const text = value.trim();
    if (!text) return;
    const scope = overrides.scope ?? searchScope;
    const match = overrides.match ?? searchMatch;
    const caseSensitive = overrides.caseSensitive ?? searchCase;
    try {
      const params = new URLSearchParams({ q: text, scope, match, case: caseSensitive ? "true" : "false" });
      const result = await api<{ hits: Array<{ file_path: string; scenario_name?: string; description?: string; matched_field?: string; match_value?: string }> }>(`/api/search?${params.toString()}`);
      if (result.hits.length === 1) { await openFeature(result.hits[0].file_path); return; }
      setFeature(null); setSelectedPath(""); setSelectedProject("");
      setListing({ kind: "search", features: result.hits.map((hit) => ({ file_name: hit.file_path, scenario_name: hit.scenario_name ?? "", description: hit.description ?? "", tags: hit.matched_field === "tag" && hit.match_value ? [hit.match_value] : [], enums: [] })) });
      setError("");
    } catch (cause) { setError((cause as Error).message); }
  }
  function scheduleSearch(value: string) { clearSearchTimer(); if (!value.trim()) return; searchTimer.current = window.setTimeout(() => { searchTimer.current = null; void runSearch(value); }, 300); }
  async function search(event: React.FormEvent) { event.preventDefault(); clearSearchTimer(); await runSearch(); }
  async function createFolder(parent: string, label: string) {
    const name = await prompt({ title: label, label: "Name", confirmLabel: "Create" });
    if (!name?.trim()) return;
    try {
      await api("/api/folders", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ parent, name: name.trim() }) });
      await refreshTree();
      await openFolder(parent);
    } catch (cause) { setError((cause as Error).message); }
  }
  async function createFeature(parent: string) {
    const fileName = await prompt({ title: "Create test case", label: "Feature file name", confirmLabel: "Continue" });
    if (!fileName?.trim()) return;
    const scenarioName = await prompt({ title: "Create test case", label: "Scenario name", confirmLabel: "Continue" });
    if (!scenarioName?.trim()) return;
    const description = await prompt({ title: "Create test case", label: "Feature description (optional)", confirmLabel: "Create" }) ?? "";
    try {
      await api("/api/files", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ parent, file_name: fileName.trim(), scenario_name: scenarioName.trim(), description }) });
      await refreshTree();
      await openFolder(parent);
    } catch (cause) { setError((cause as Error).message); }
  }
  async function moveSelectedFeature() {
    if (!selectedPath || !moveTarget) return;
    if (dirty && !(await confirm({ title: "Move test case?", description: "Discard unsaved changes and move the file?", confirmLabel: "Move" }))) return;
    try {
      await api(pathUrl("/api/files", `${selectedPath}/move`), { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ parent: moveTarget }) });
      setMoveTarget("");
      setFeature(null);
      await refreshTree();
      await openFolder(moveTarget);
    } catch (cause) { setError((cause as Error).message); }
  }
  async function reloadSelectedFeature(discard = false) {
    if (!selectedPath) return;
    if (dirty && !discard && !(await confirm({ title: "Reload test case?", description: "Discard unsaved changes and reload from disk?", confirmLabel: "Reload" }))) return;
    setEditorBanner(null);
    await openFeature(selectedPath);
  }
  async function discardRemovedFeature() {
    const parent = selectedPath.split("/").slice(0, -1).join("/");
    setFeature(null);
    setEditorBanner(null);
    await openFolder(parent);
  }
  async function renameSelected() { const name = await prompt({ title: "Rename folder", label: "Folder name", initialValue: selectedPath.split("/").at(-1), confirmLabel: "Rename" }); if (!name || !selectedPath) return; try { await api(pathUrl("/api/folders", selectedPath), { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ name }) }); await refreshTree(); await openFolder(selectedPath.split("/").slice(0, -1).concat(name).join("/")); } catch (cause) { setError((cause as Error).message); } }
  async function deleteSelected() { if (!selectedPath || !(await confirm({ title: "Delete folder?", description: `Delete ${selectedPath} and its contents?`, confirmLabel: "Delete", destructive: true }))) return; try { await api(pathUrl("/api/folders", selectedPath), { method: "DELETE" }); setSelectedPath(""); setListing(null); await refreshTree(); await openFolder(""); } catch (cause) { setError((cause as Error).message); } }
  async function importBatch() {
    if (!files.length || !selectedPath) return;
    try {
      const sources = await Promise.all(files.map(async (file) => ({ name: file.name, source: await file.text() })));
      const preview = await api<{ scenarios: unknown[] }>("/api/files/import/preview", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ sources }) });
      const occupied = [...(listing?.folders ?? []), ...(listing?.features ?? []).map((item) => item.file_name)];
      const names = generatedImportNames(selectedPath, preview.scenarios.length, occupied);
      await api(`/api/files/import`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ parent: selectedPath, sources, names }) });
      setFiles([]); setImportOpen(false); await refreshTree(); await openFolder(selectedPath);
    } catch (cause) { setError((cause as Error).message); }
  }
  async function saveFeature() {
    if (!feature || !selectedPath) return;
    try {
      if (editorMode === "raw") {
        setRawError("");
        await textApi(pathUrl("/api/files", `${selectedPath}/raw`), { method: "PUT", headers: { "content-type": "text/plain; charset=utf-8" }, body: featureRaw });
      } else {
        const payload = cleanFeatureForSave(JSON.parse(featureDraft) as FeaturePayload);
        setFeatureDraft(JSON.stringify(payload, null, 2));
        await api(pathUrl("/api/files", selectedPath), { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
      }
      setDirty(false);
      await openFeature(selectedPath);
      await refreshTree();
      setSaved(true);
      window.setTimeout(() => setSaved(false), 1500);
    } catch (cause) {
      if ((cause as Error).message === "outline_examples") {
        setEditorBanner({ message: "Cannot save: An outline must have at least one Examples block.", tone: "error", conflict: false, removed: false });
        return;
      }
      if (editorMode === "raw") {
        const textError = cause instanceof TextApiError ? cause : undefined;
        const message = textError?.details?.line ? `Line ${textError.details.line}, col ${textError.details.column ?? 0}: ${textError.message}` : (cause as Error).message;
        setRawError(message);
        return;
      }
      setError((cause as Error).message);
    }
  }
  function renameFeature(featurePath = selectedPath, scenarioName = "") { if (!featurePath) return; setFeatureEdit({ path: featurePath, scenarioName, fileName: featurePath.split("/").at(-1) ?? "" }); }
  async function saveFeatureEdit(scenarioName: string, fileName: string): Promise<boolean> {
    if (!featureEdit) return false;
    if (!scenarioName || !fileName) { setError("Scenario name and feature file name are required."); return false; }
    try {
      if (scenarioName !== featureEdit.scenarioName) {
        const current = await api<FeaturePayload>(pathUrl("/api/files", featureEdit.path));
        await api(pathUrl("/api/files", featureEdit.path), { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ ...current, scenario: { ...current.scenario, name: scenarioName } }) });
      }
      if (fileName !== featureEdit.fileName) await api(pathUrl("/api/files", `${featureEdit.path}/rename`), { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ file_name: fileName }) });
      await refreshTree();
      await openFolder(featureEdit.path.split("/").slice(0, -1).join("/"));
      setFeature(null);
      return true;
    } catch (cause) { setError((cause as Error).message); return false; }
  }
  async function deleteFeature(featurePath = selectedPath) { if (!featurePath || !(await confirm({ title: "Delete test case?", description: `Delete ${featurePath}?`, confirmLabel: "Delete", destructive: true }))) return; try { await api(pathUrl("/api/files", featurePath), { method: "DELETE" }); await refreshTree(); await openFolder(featurePath.split("/").slice(0, -1).join("/")); } catch (cause) { setError((cause as Error).message); } }
  async function changeTab(next: Tab) { if (dirty && !(await confirm({ title: "Discard changes?", description: "Discard unsaved feature changes?", confirmLabel: "Discard" }))) return; setDirty(false); setDeepLinkRun(""); setDeepLinkReport(""); setTab(next); }

  return <><LiveStatus message={error} assertive /><LiveStatus message={editorBanner?.message ?? ""} /><main className="shell">
    <header className="topbar"><span className="brand">TMS</span><WorkspaceMenu tab={tab} onChange={changeTab} /><form onSubmit={search} className="search"><input aria-label="Search" value={query} onChange={(event) => { setQuery(event.target.value); scheduleSearch(event.target.value); }} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); clearSearchTimer(); void runSearch(event.currentTarget.value); } }} placeholder="Search test cases…" style={{ border: 0, outline: 0, width: "100%" }} /></form><div className="search-options"><select aria-label="Search scope" value={searchScope} onChange={(event) => { const value = event.target.value; setSearchScope(value); if (query.trim()) { clearSearchTimer(); void runSearch(query, { scope: value }); } }}>{searchScopes.map((scope) => <option key={scope.value} value={scope.value}>{scope.label}</option>)}</select><select aria-label="Search match" value={searchMatch} onChange={(event) => { const value = event.target.value as "text" | "tag"; setSearchMatch(value); if (query.trim()) { clearSearchTimer(); void runSearch(query, { match: value }); } }}><option value="text">Description</option><option value="tag">Tag</option></select><label><input type="checkbox" checked={searchCase} onChange={(event) => { const value = event.target.checked; setSearchCase(value); if (query.trim()) { clearSearchTimer(); void runSearch(query, { caseSensitive: value }); } }} /> Case-sensitive</label></div><span className="muted">{selectedProject || "Filesystem workspace"}</span></header>
    
    {tab === "directory" ? <div className="layout"><aside className="sidebar"><div className="card-header" style={{ padding: "0 0 .75rem" }}><strong>Directory</strong><button className="button" onClick={() => void refreshTree()}>Refresh</button></div><TreeBranch nodes={tree} selected={selectedPath} expanded={expandedFolders} onToggle={toggleFolder} onFolder={(node) => void openFolder(node.path)} onFeature={(node) => void openFeature(node)} /></aside>
      <section className="content"><div className="stack">{error && <div className="notice">{error}</div>}{listing && <div className="card"><div className="card-header"><div className="breadcrumb-heading">{selectedPath && listing.kind !== "search" && selectedPath.split("/").length >= 2 && <button className="icon-button" aria-label="Back to parent folder" title="Back" onClick={() => void openFolder(selectedPath.split("/").slice(0, -1).join("/"))}><ArrowLeft size={16} aria-hidden="true" /></button>}<div><strong>{listing.kind === "search" ? "Search results" : selectedPath || "Projects"}</strong><div className="muted">{listing.features?.length ?? listing.projects?.length ?? listing.modules?.length ?? 0} items</div></div></div><div className="actions">{listing.kind === "root" && <button className="button primary" onClick={() => void createFolder("", "New project name")}>New project</button>}{selectedPath && listing.kind !== "search" && <>{selectedPath.split("/").length === 1 ? <button className="button primary" onClick={() => void createFolder(selectedPath, "New module name")}>New module</button> : <button className="button primary" onClick={() => void createFolder(selectedPath, "New subfolder name")}>+ Sub-folder</button>}{selectedPath.split("/").length >= 2 && <button className="button primary" onClick={() => void createFeature(selectedPath)}>+ Scenario</button>}<button className="icon-button" aria-label="Rename folder" title="Rename folder" onClick={renameSelected}><Pencil size={16} aria-hidden="true" /></button><button className="icon-button danger-icon" aria-label="Delete folder" title="Delete folder" onClick={deleteSelected}><Trash2 size={16} aria-hidden="true" /></button></>} {selectedPath && listing.kind !== "search" && <button className="icon-button" aria-label="Import files" title="Import files" onClick={() => setImportOpen(true)}><Upload size={16} aria-hidden="true" /></button>}</div></div><div className="card-body">{listing.features ? <><FolderLinks names={listing.folders ?? []} parent={selectedPath} onOpen={openFolder} /><div className="actions" style={{ marginBottom: ".75rem" }}><input className="search" style={{ maxWidth: "none" }} placeholder="Filter scenario name…" value={filter} onChange={(event) => { setFilter(event.target.value); setPage(1); }} /><button className="button" onClick={() => { setSort("file_name"); setPage(1); }}>Sort file</button><button className="button" onClick={() => { setSort("scenario_name"); setPage(1); }}>Sort scenario</button></div><div className="table-wrap"><table className="feature-table"><thead><tr><th>Scenario</th><th>Tags</th><th>Enums</th><th>Actions</th></tr></thead><tbody>{paginatedFeatures.map((item) => <tr className="clickable-row" key={item.file_name} tabIndex={0} title="Open scenario detail" onClick={() => void openFeature(selectedPath ? `${selectedPath}/${item.file_name}` : item.file_name)} onKeyDown={(event) => { if (event.target !== event.currentTarget || (event.key !== "Enter" && event.key !== " ")) return; event.preventDefault(); void openFeature(selectedPath ? `${selectedPath}/${item.file_name}` : item.file_name); }}><td>{item.scenario_name || <span className="muted">Malformed</span>}</td><td><InlinePills values={item.tags} limit={2} prefix="@" /></td><td><InlinePills values={item.enums.map((entry) => entry.label || entry.key)} limit={1} /></td><td><span className="row-actions"><button className="icon-button" aria-label={`Edit ${item.file_name}`} title="Edit file name" onClick={(event) => { event.stopPropagation(); void renameFeature(selectedPath ? `${selectedPath}/${item.file_name}` : item.file_name, item.scenario_name); }}><Pencil size={16} aria-hidden="true" /></button><button className="icon-button danger-icon" aria-label={`Remove ${item.file_name}`} title="Remove file" onClick={(event) => { event.stopPropagation(); void deleteFeature(selectedPath ? `${selectedPath}/${item.file_name}` : item.file_name); }}><Trash2 size={16} aria-hidden="true" /></button></span></td></tr>)}</tbody></table></div>{listing.kind !== "search" && filteredFeatures.length > 0 && <div className="table-pagination"><span>{(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, filteredFeatures.length)} of {filteredFeatures.length}</span><label className="page-size"><span>Rows</span><select aria-label="Scenarios per page" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value) as 20 | 50 | 100); setPage(1); }}><option value={20}>20</option><option value={50}>50</option><option value={100}>100</option></select></label><div className="actions"><button className="button" disabled={currentPage === 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Previous</button><span>Page {currentPage} of {totalPages}</span><button className="button" disabled={currentPage === totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>Next</button></div></div>}{!filteredFeatures.length && <p className="muted">{listing.kind === "search" ? `No matches for ${query}` : "No test cases."}</p>}</> : <FolderLinks names={listing.projects ?? listing.modules ?? listing.folders ?? []} parent={selectedPath} onOpen={openFolder} emptyMessage="No items" />}</div></div>}{editorBanner && <div className={`notice ${editorBanner.tone}`}>{editorBanner.message}{editorBanner.conflict && <span className="actions"><button className="button" onClick={() => void reloadSelectedFeature(true)}>Reload (discard mine)</button><button className="button" onClick={() => setEditorBanner(null)}>Keep editing</button></span>}{editorBanner.removed && <button className="button" onClick={() => void discardRemovedFeature()}>Discard</button>}</div>}{feature && <div className="card"><div className="card-header"><div className="breadcrumb-heading"><button className="icon-button" aria-label="Back to parent folder" title="Back" onClick={() => void openFolder(selectedPath.split("/").slice(0, -1).join("/"))}><ArrowLeft size={16} aria-hidden="true" /></button><div><strong>{selectedPath}</strong>{dirty && <span className="dirty-indicator">Unsaved</span>}{saved && !dirty && <span className="saved-indicator">Saved</span>}</div></div><div className="actions"><button className={`button ${editorMode === "structured" ? "primary" : ""}`} onClick={() => switchEditorMode("structured")}>Structured</button><button className={`button ${editorMode === "raw" ? "primary" : ""}`} onClick={() => switchEditorMode("raw")}>Raw</button><button className="button primary" disabled={!dirty || (editorMode === "structured" && !structuredDescription.trim())} onClick={() => void saveFeature()}>Save</button><button className="button" onClick={() => void reloadSelectedFeature()}>Reload</button>{moveDestinations.length > 0 && <><select aria-label="Move feature destination" value={moveTarget} onChange={(event) => setMoveTarget(event.target.value)}><option value="">Move…</option>{moveDestinations.map((path) => <option key={path} value={path}>{path}</option>)}</select><button className="button" disabled={!moveTarget} onClick={() => void moveSelectedFeature()}>Move</button></>}</div></div><div className="card-body">{editorMode === "raw" ? <div><textarea className="editor" value={featureRaw} onChange={(event) => { setFeatureRaw(event.target.value); setRawError(""); setSaved(false); setDirty(true); }} />{rawError && <div className="raw-error">{rawError}</div>}</div> : <StructuredFeatureEditor draft={featureDraft} onChange={(next) => { setFeatureDraft(next); setSaved(false); setDirty(true); }} />}</div></div>}{!listing && !feature && <div className="card empty"><p className="muted">Select a project, folder, or feature from the directory.</p></div>}</div></section></div> : <section className="content"><div className="stack">{error && <div className="notice">{error}</div>}{tab === "runs" && <RunsPanel project={selectedProject} initialRun={deepLinkRun} onError={reportError} />}{tab === "reports" && <ReportsPanel project={selectedProject} initialReport={deepLinkReport} onError={reportError} />}{tab === "enums" && <EnumsPanel project={selectedProject} onError={reportError} />}</div></section>}
  </main><FeatureImportDialog open={importOpen} files={files} onFiles={setFiles} onImport={() => void importBatch()} onCancel={() => { setFiles([]); setImportOpen(false); }} /><FeatureEditDialog request={featureEdit} onCancel={() => setFeatureEdit(null)} onSubmit={saveFeatureEdit} /></>;
}

export default function Home() {
  return <DialogProvider><Workspace /></DialogProvider>;
}
