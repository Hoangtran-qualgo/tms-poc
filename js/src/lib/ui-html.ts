import { stat } from "node:fs/promises";
import { resolve } from "node:path";

import { parseFeature } from "./feature";
import { listFolder, type FolderListing } from "./folder";
import { readProjectEnums } from "./enums";
import { computeReport } from "./reporting";
import { readReport, listReports } from "./report-storage";
import { listProjects, listRunGroups, listRuns, readRun } from "./run-storage";
import { searchFeatures } from "./search";
import { listTree, type TreeNode } from "./tree";
import { resolveDataRoot } from "./data-root";
import { readUtf8File } from "./utf8";
import { validateLogicalSegments, PathValidationError } from "./path";

export { PathValidationError };

export const UI_HTML_HEADERS = { "content-type": "text/html; charset=utf-8" };

export function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function pathUrl(prefix: string, path: string): string {
  return `${prefix}/${path.split("/").filter(Boolean).map(encodeURIComponent).join("/")}`;
}

function fragment(title: string, body: string): string {
  return `<section data-ui-fragment="true" data-ui-title="${escapeHtml(title)}"><h2>${escapeHtml(title)}</h2>${body}</section>`;
}

function renderTreeNodes(nodes: TreeNode[]): string {
  if (!nodes.length) return `<p class="muted">No projects or test cases.</p>`;
  return `<ul>${nodes.map((node) => {
    const link = node.type === "folder" ? pathUrl("/ui/folder", node.path) : pathUrl("/ui/file", node.path);
    const count = node.type === "folder" ? ` <span class="count">${node.counts.total}-${node.counts.auto}-${node.counts.non_auto}</span>` : "";
    return `<li data-path="${escapeHtml(node.path)}"><a href="${escapeHtml(link)}">${escapeHtml(node.name || "Projects")}</a>${count}${node.type === "folder" ? renderTreeNodes(node.children) : ""}</li>`;
  }).join("")}</ul>`;
}

function renderFolderListing(path: string, listing: FolderListing): string {
  if (listing.kind === "root") return fragment("Projects", listing.projects.map((project) => `<a href="${escapeHtml(pathUrl("/ui/folder", project))}">${escapeHtml(project)}</a>`).join(" ") || `<p class="muted">No projects.</p>`);
  if (listing.kind === "project") return fragment(path || "Project", listing.modules.map((module) => `<a href="${escapeHtml(pathUrl("/ui/folder", `${path}/${module}`))}">${escapeHtml(module)}</a>`).join(" ") || `<p class="muted">No modules.</p>`);
  const folders = listing.folders.map((folder) => `<tr><td><a href="${escapeHtml(pathUrl("/ui/folder", `${path}/${folder}`))}">${escapeHtml(folder)}</a></td></tr>`).join("");
  const features = listing.features.map((feature) => `<tr><td><a href="${escapeHtml(pathUrl("/ui/file", `${path}/${feature.file_name}`))}">${escapeHtml(feature.file_name)}</a></td><td>${escapeHtml(feature.scenario_name || "Malformed")}</td><td>${feature.tags.map((tag) => `@${escapeHtml(tag)}`).join(" ")}</td></tr>`).join("");
  return fragment(path, `<table><thead><tr><th>File name</th><th>Scenario</th><th>Tags</th></tr></thead><tbody>${folders}${features || `<tr><td colspan="3">No test cases.</td></tr>`}</tbody></table>`);
}

async function renderFolder(path: string[]): Promise<string> {
  const root = resolveDataRoot();
  if (path[1] === "test-run") {
    const project = path[0];
    if (!project) throw new PathValidationError("A project is required.");
    const groups = await listRunGroups(project);
    if (path.length === 2) return fragment(`${project}/test-run`, groups.map((group) => `<a href="${escapeHtml(pathUrl("/ui/folder", `${project}/test-run/${group}`))}">${escapeHtml(group)}</a>`).join(" ") || `<p class="muted">No run groups.</p>`);
    if (path.length === 3) {
      const group = path[2];
      const runs = await listRuns(project, group);
      return fragment(`${project}/test-run/${group}`, runs.map((run) => `<a href="${escapeHtml(pathUrl("/ui/run", `${project}/${group}/${String(run.file_name)}`))}">${escapeHtml(String(run.name || run.file_name))}</a>`).join(" ") || `<p class="muted">No runs.</p>`);
    }
    throw new Error(`Folder not found: ${path.join("/")}`);
  }
  if (path[1] === "report") {
    const project = path[0];
    if (!project || path.length > 2) throw new Error(`Folder not found: ${path.join("/")}`);
    const reports = await listReports(project);
    return fragment(`${project}/report`, reports.map((report) => `<a href="${escapeHtml(pathUrl("/ui/report", `${project}/${String(report.file_name)}`))}">${escapeHtml(String(report.title || report.file_name))}</a>`).join(" ") || `<p class="muted">No reports.</p>`);
  }
  return renderFolderListing(path.join("/"), await listFolder(root, path));
}

async function renderFile(path: string[]): Promise<string> {
  validateLogicalSegments(path);
  const logicalPath = path.join("/");
  if (!logicalPath.toLowerCase().endsWith(".feature")) return fragment(logicalPath, `<p>Unsupported file type: ${escapeHtml(logicalPath)}</p>`);
  const source = await readUtf8File(resolve(resolveDataRoot(), ...path));
  const feature = parseFeature(source);
  return fragment(logicalPath, `<pre data-feature-json="true">${escapeHtml(JSON.stringify(feature, null, 2))}</pre><pre data-feature-raw="true">${escapeHtml(source)}</pre>`);
}

async function renderRun(path: string[]): Promise<string> {
  if (path.length !== 3) throw new Error(`Run not found: ${path.join("/")}`);
  const [project, group, fileName] = path;
  const run = await readRun(project, group, fileName);
  const rows = run.results.map((result) => `<tr><td><a href="${escapeHtml(pathUrl("/ui/file", result.file_path))}">${escapeHtml(result.file_path)}</a></td><td>${escapeHtml(result.result)}</td><td>${escapeHtml(result.remark)}</td></tr>`).join("");
  return fragment(`${project}/${group}/${fileName}`, `<dl><dt>Name</dt><dd>${escapeHtml(run.name)}</dd><dt>Created</dt><dd>${escapeHtml(run.created_at)}</dd></dl><table><thead><tr><th>Case</th><th>Result</th><th>Remark</th></tr></thead><tbody>${rows}</tbody></table>`);
}

async function renderReport(path: string[]): Promise<string> {
  if (path.length !== 2) throw new Error(`Report not found: ${path.join("/")}`);
  const [project, fileName] = path;
  const report = await readReport(project, fileName);
  const view = await computeReport(project, report);
  return fragment(`${project}/${fileName}`, `<pre data-report-json="true">${escapeHtml(JSON.stringify(view, null, 2))}</pre>`);
}

async function renderSearch(query: URLSearchParams): Promise<string> {
  const value = (query.get("q") ?? "").trim();
  if (!value) return fragment("Search", `<p>Type a query to search test cases.</p>`);
  const hits = await searchFeatures(resolveDataRoot(), value, query.get("scope") ?? "all", query.get("match") ?? "text", ["true", "1", "yes"].includes((query.get("case") ?? "false").toLowerCase()));
  if (!hits.length) return fragment("Search", `<p>No matches for ${escapeHtml(value)}.</p>`);
  return fragment("Search", `<ul>${hits.map((hit) => `<li><a href="${escapeHtml(pathUrl("/ui/file", hit.file_path))}">${escapeHtml(hit.file_path)}</a> — ${escapeHtml(hit.scenario_name)}</li>`).join("")}</ul>`);
}

export async function renderUiFragment(parts: string[], query: URLSearchParams): Promise<string> {
  const [route, ...rest] = parts;
  switch (route) {
    case "tree": return fragment("Directory", renderTreeNodes((await listTree(resolveDataRoot())).children));
    case "test-run-tree": {
      const projects = await listProjects();
      const links: string[] = [];
      for (const project of projects) for (const group of await listRunGroups(project)) links.push(`<a href="${escapeHtml(pathUrl("/ui/folder", `${project}/test-run/${group}`))}">${escapeHtml(project)}/${escapeHtml(group)}</a>`);
      return fragment("Test runs", links.join(" ") || `<p class="muted">No test runs.</p>`);
    }
    case "reports-tree": {
      const links: string[] = [];
      for (const project of await listProjects()) for (const report of await listReports(project)) links.push(`<a href="${escapeHtml(pathUrl("/ui/report", `${project}/${String(report.file_name)}`))}">${escapeHtml(project)}/${escapeHtml(String(report.title || report.file_name))}</a>`);
      return fragment("Reports", links.join(" ") || `<p class="muted">No reports.</p>`);
    }
    case "enums-tree": {
      const links: string[] = [];
      for (const project of await listProjects()) { const missing = await stat(resolve(resolveDataRoot(), project, "enums.yaml")).then(() => false).catch(() => true); links.push(`<a href="${escapeHtml(pathUrl("/ui/enums", project))}">${escapeHtml(project)}${missing ? " (initialize)" : ""}</a>`); }
      return fragment("Enums", links.join(" ") || `<p class="muted">No projects.</p>`);
    }
    case "folder": return renderFolder(rest);
    case "file": return renderFile(rest);
    case "run": return renderRun(rest);
    case "report": return renderReport(rest);
    case "enums": {
      if (rest.length !== 1) throw new Error(`Enum project not found: ${rest.join("/")}`);
      const project = rest[0];
      const vocabulary = await readProjectEnums(resolve(resolveDataRoot(), project, "enums.yaml")).catch(() => null);
      return fragment(`Enums: ${project}`, vocabulary ? `<pre>${escapeHtml(JSON.stringify(vocabulary, null, 2))}</pre>` : `<p>Project has no enums.yaml; initialize it from the workspace.</p>`);
    }
    case "search": return renderSearch(query);
    default: throw new Error(`UI route not found: ${parts.join("/")}`);
  }
}

export function uiErrorHtml(error: unknown): { status: number; body: string } {
  const code = (error as NodeJS.ErrnoException).code;
  const message = error instanceof Error ? error.message : String(error);
  const status = code === "ENOENT" || /^Folder not found|^Run not found|^Report not found|^Enum project not found/.test(message) ? 404 : error instanceof PathValidationError ? 400 : 500;
  const safe = status === 500 && !(error instanceof PathValidationError) ? "An unexpected error occurred." : message;
  return { status, body: `<div class="p-4 text-red-700 bg-red-50 border border-red-200 rounded">${escapeHtml(safe)}</div>` };
}
