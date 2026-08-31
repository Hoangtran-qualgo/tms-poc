import { parse as parseYaml, stringify as stringifyYaml } from "yaml";
import { RUN_RESULTS } from "./run";

export const RUN_SET_TYPES = ["enum_ranking", "tag_ranking", "case_trend"] as const;
export const REPORT_TYPES = [...RUN_SET_TYPES, "tag_inventory"] as const;
export type ReportType = (typeof REPORT_TYPES)[number];
export const FOLDER_TYPES = new Set(["tag_inventory"]);

export type Report = {
  type: string;
  title: string;
  created_at: string;
  run_paths: string[];
  scope: string;
  status: string;
  kind: string;
  case_path: string;
  tag: string;
};

export class ReportParseError extends Error {
  constructor(message: string, readonly line = 0, readonly column = 0) { super(message); }
}
export class ReportValidationError extends Error {
  constructor(readonly field: string, message: string) { super(message); }
}
export class ReportConflictError extends Error {}

export function emptyReport(): Report { return { type: "", title: "", created_at: "", run_paths: [], scope: "", status: "", kind: "", case_path: "", tag: "" }; }

export function parseReport(source: string): Report {
  let payload: unknown;
  try { payload = parseYaml(source); }
  catch (error) {
    const mark = (error as { linePos?: Array<{ line: number; col: number }> }).linePos?.[0];
    throw new ReportParseError((error as Error).message, mark?.line ?? 0, mark?.col ?? 0);
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new ReportParseError(`Report file root must be a YAML mapping; got ${Array.isArray(payload) ? "list" : typeof payload}.`);
  const record = payload as Record<string, unknown>;
  const paths = record.run_paths;
  if (paths !== undefined && !Array.isArray(paths)) throw new ReportParseError("Report field 'run_paths' must be a list.");
  return { type: typeof record.type === "string" ? record.type : String(record.type ?? ""), title: typeof record.title === "string" ? record.title : String(record.title ?? ""), created_at: typeof record.created_at === "string" ? record.created_at : String(record.created_at ?? ""), run_paths: (paths as unknown[] | undefined)?.map((value) => String(value)) ?? [], scope: typeof record.scope === "string" ? record.scope : String(record.scope ?? ""), status: typeof record.status === "string" ? record.status : String(record.status ?? ""), kind: typeof record.kind === "string" ? record.kind : String(record.kind ?? ""), case_path: typeof record.case_path === "string" ? record.case_path : String(record.case_path ?? ""), tag: typeof record.tag === "string" ? record.tag : String(record.tag ?? "") };
}

export function validateReport(report: Report): void {
  if (!(REPORT_TYPES as readonly string[]).includes(report.type)) throw new ReportValidationError("type", `Invalid report type: '${report.type}'.`);
  if (!report.title.trim()) throw new ReportValidationError("title", "Report title must not be empty.");
  if (/\r|\n/.test(report.title)) throw new ReportValidationError("title", "Report title must be single-line.");
  if (!report.created_at.trim()) throw new ReportValidationError("created_at", "created_at must not be empty.");
  if (/\r|\n/.test(report.created_at)) throw new ReportValidationError("created_at", "created_at must be single-line.");
  if (report.type === "enum_ranking") {
    if (!(RUN_RESULTS as readonly string[]).includes(report.status)) throw new ReportValidationError("status", `Invalid status: '${report.status}'.`);
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(report.kind)) throw new ReportValidationError("kind", "enum_ranking kind is invalid.");
  } else if (report.type === "tag_ranking") {
    if (!(RUN_RESULTS as readonly string[]).includes(report.status)) throw new ReportValidationError("status", `Invalid status: '${report.status}'.`);
  } else if (report.type === "case_trend") {
    if (!report.case_path.trim()) throw new ReportValidationError("case_path", "case_trend case_path must not be empty.");
  } else if (report.type === "tag_inventory") {
    if (!report.tag.trim()) throw new ReportValidationError("tag", "tag_inventory tag must not be empty.");
    if (!report.scope.trim()) throw new ReportValidationError("scope", "tag_inventory scope must not be empty.");
  }
  if (RUN_SET_TYPES.includes(report.type as (typeof RUN_SET_TYPES)[number])) {
    if (report.scope) throw new ReportValidationError("scope", "scope must be empty for run-set report types.");
    if (report.tag) throw new ReportValidationError("tag", "tag must be empty for run-set report types.");
    if (report.run_paths.length > 10) throw new ReportValidationError("run_paths", "A report may reference at most 10 runs.");
    const seen = new Set<string>();
    for (const [index, path] of report.run_paths.entries()) { if (!path) throw new ReportValidationError(`run_paths[${index}]`, "run path must not be empty."); if (seen.has(path)) throw new ReportValidationError(`run_paths[${index}]`, `Duplicate run path: '${path}'.`); seen.add(path); }
  } else if (report.run_paths.length) throw new ReportValidationError("run_paths", "run_paths must be empty for folder report types.");
}

export function reportToPersisted(report: Report): Record<string, unknown> {
  const out: Record<string, unknown> = { type: report.type, title: report.title, created_at: report.created_at };
  if (report.type === "enum_ranking") Object.assign(out, { status: report.status, kind: report.kind, run_paths: report.run_paths });
  else if (report.type === "tag_ranking") Object.assign(out, { status: report.status, run_paths: report.run_paths });
  else if (report.type === "case_trend") Object.assign(out, { case_path: report.case_path, run_paths: report.run_paths });
  else if (report.type === "tag_inventory") Object.assign(out, { tag: report.tag, scope: report.scope });
  return out;
}

export function serializeReport(report: Report): string { validateReport(report); return stringifyYaml(reportToPersisted(report), { sortMapEntries: false, lineWidth: 0 }); }
