import { mkdir, readdir, stat, unlink } from "node:fs/promises";
import { resolve } from "node:path";
import { atomicCreateUtf8, atomicWriteUtf8 } from "./atomic-write";
import { resolveDataRoot } from "./data-root";
import { validateLogicalSegments } from "./path";
import { readProjectEnums } from "./enums";
import { parseReport, ReportConflictError, ReportValidationError, serializeReport, validateReport, type Report } from "./report";
import { readUtf8File } from "./utf8";
import { markWrite } from "./events";

const REPORT_AREA = "report";
const RUN_AREA = "test-run";
const TEMP_FILE_RE = /.+\.tmp\.\d+\.[0-9a-f]+$/i;

function reportPath(project: string, fileName: string): { path: string; name: string } {
  const name = fileName.toLowerCase().endsWith(".yaml") ? fileName : fileName.includes(".") ? (() => { throw new ReportValidationError("file_name", `Report file name must end with '.yaml'; got '${fileName}'.`); })() : `${fileName}.yaml`;
  validateLogicalSegments([project, name]);
  return { path: resolve(resolveDataRoot(), project, REPORT_AREA, name), name };
}

function projectRelative(project: string, raw: string, field: string): string[] {
  const parts = raw.split("/").filter(Boolean);
  validateLogicalSegments(parts);
  if (parts[0] !== project) throw new ReportValidationError(field, `${field} must be inside project '${project}': '${raw}'.`);
  return parts;
}

async function crossCheck(project: string, report: Report): Promise<void> {
  const root = resolveDataRoot();
  if (report.type === "enum_ranking") {
    let vocabulary;
    try { vocabulary = await readProjectEnums(resolve(root, project, "enums.yaml")); }
    catch { throw new ReportValidationError("kind", `Cannot rank enum kind '${report.kind}': project '${project}' has no enums.yaml.`); }
    if (!(report.kind in vocabulary)) throw new ReportValidationError("kind", `Unknown enum kind '${report.kind}'.`);
  }
  if (report.type === "enum_ranking" || report.type === "tag_ranking" || report.type === "case_trend") {
    for (const [index, raw] of report.run_paths.entries()) {
      const parts = raw.split("/");
      if (parts.length !== 4 || parts[0] !== project || parts[1] !== RUN_AREA) throw new ReportValidationError(`run_paths[${index}]`, `Run path must be ${project}/${RUN_AREA}/<group>/<file>: '${raw}'.`);
      validateLogicalSegments(parts);
      try { if (!(await stat(resolve(root, ...parts))).isFile()) throw new Error(); }
      catch { throw new ReportValidationError(`run_paths[${index}]`, `Run not found: '${raw}'.`); }
    }
  }
  if (report.type === "case_trend") {
    const parts = projectRelative(project, report.case_path, "case_path");
    try { if (!(await stat(resolve(root, ...parts))).isFile()) throw new Error(); }
    catch { throw new ReportValidationError("case_path", `Case not found: '${report.case_path}'.`); }
  }
  if (report.type === "tag_inventory") {
    const parts = projectRelative(project, report.scope, "scope");
    try { if (!(await stat(resolve(root, ...parts))).isDirectory()) throw new Error(); }
    catch { throw new ReportValidationError("scope", `Scope folder not found: '${report.scope}'.`); }
  }
}

export async function createReport(project: string, fileName: string, input: Report): Promise<void> {
  const { path, name } = reportPath(project, fileName);
  if (!(await stat(resolve(resolveDataRoot(), project)).catch(() => null))?.isDirectory()) throw new Error(`Project folder does not exist: '${project}'.`);
  // Python's UTC ISO serializer emits an explicit +00:00 offset (rather than
  // the equivalent trailing Z); preserve that persisted shape for parity.
  const report = { ...input, created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00") };
  if (await stat(/*turbopackIgnore: true*/ path).then(() => true).catch(() => false)) throw new ReportConflictError(`A report named '${name}' already exists.`);
  validateReportForStorage(report);
  await crossCheck(project, report);
  const area = resolve(resolveDataRoot(), project, REPORT_AREA);
  await mkdir(area, { recursive: false }).then(() => markWrite(area)).catch((error: unknown) => { if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error; });
  try { await atomicCreateUtf8(path, serializeReport(report)); }
  catch (error) { if ((error as NodeJS.ErrnoException).code === "EEXIST") throw new ReportConflictError(`A report named '${name}' already exists.`); throw error; }
}

function validateReportForStorage(report: Report): void { validateReport(report); }

export async function readReport(project: string, fileName: string): Promise<Report> { const { path } = reportPath(project, fileName); return parseReport(await readUtf8File(path)); }

export async function writeReport(project: string, fileName: string, report: Report): Promise<void> {
  const { path } = reportPath(project, fileName);
  await stat(/*turbopackIgnore: true*/ path);
  validateReportForStorage(report);
  await crossCheck(project, report);
  await atomicWriteUtf8(path, serializeReport(report));
}

export async function deleteReport(project: string, fileName: string): Promise<void> { const { path } = reportPath(project, fileName); await unlink(path).then(() => markWrite(path)).catch((error: unknown) => { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }); }

export async function listReports(project: string): Promise<Array<Record<string, unknown>>> {
  const area = resolve(resolveDataRoot(), project, REPORT_AREA);
  const entries = await readdir(area, { withFileTypes: true }).catch((error: unknown) => { if ((error as NodeJS.ErrnoException).code === "ENOENT") return []; throw error; });
  const reports: Array<Record<string, unknown>> = [];
  for (const entry of entries) {
    if (!entry.isFile() || TEMP_FILE_RE.test(entry.name) || !entry.name.toLowerCase().endsWith(".yaml")) continue;
    try {
      const report = await readReport(project, entry.name);
      reports.push({ file_name: entry.name, title: report.title, type: report.type, created_at: report.created_at, source: report.type === "tag_inventory" ? report.scope : `${report.run_paths.length} run(s)` });
    } catch { reports.push({ file_name: entry.name, title: "", type: "", created_at: "", source: "" }); }
  }
  return reports;
}

export { crossCheck };
