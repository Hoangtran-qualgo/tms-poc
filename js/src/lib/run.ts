import { parse as parseYaml, stringify as stringifyYaml } from "yaml";

export const RUN_RESULTS = ["PENDING", "EXECUTING", "PASSED", "FAILED", "SKIPPED"] as const;
export type RunResultValue = (typeof RUN_RESULTS)[number];

export type RunResult = {
  file_path: string;
  result: string;
  remark: string;
  example?: { table: number; row: number };
};

export type TestRun = {
  name: string;
  created_at: string;
  description: string;
  results: RunResult[];
};

export class RunParseError extends Error {
  constructor(message: string, readonly line = 0, readonly column = 0) { super(message); }
}
export class RunValidationError extends Error {
  constructor(readonly field: string, message: string) { super(message); }
}
export class RunConflictError extends Error {}
/** Shape failures in nested persisted/request payloads intentionally remain
 * generic internal errors, matching the Python model's permissive conversion
 * followed by an uncaught nested-attribute failure. */
export class RunShapeError extends Error {}

export function normalizeRunFilename(name: string): string {
  if (!name) throw new RunValidationError("file_name", "Run file name must not be empty.");
  if (name.toLowerCase().endsWith(".yaml")) return name;
  if (name.includes(".")) throw new RunValidationError("file_name", `Run file name must end with '.yaml' (case-insensitive); got '${name}'.`);
  return `${name}.yaml`;
}

function stringValue(value: unknown): string { return typeof value === "string" ? value : String(value ?? ""); }

export function parseRun(source: string): TestRun {
  let payload: unknown;
  try { payload = parseYaml(source); }
  catch (error) {
    const mark = (error as { linePos?: Array<{ line: number; col: number }> }).linePos?.[0];
    throw new RunParseError((error as Error).message, mark?.line ?? 0, mark?.col ?? 0);
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new RunParseError(`Run file root must be a YAML mapping; got ${Array.isArray(payload) ? "list" : typeof payload}.`);
  const record = payload as Record<string, unknown>;
  const rawResults = record.results;
  const results: RunResult[] = [];
  if (rawResults !== undefined) {
    if (!Array.isArray(rawResults)) throw new RunShapeError("Run field 'results' has an invalid nested shape.");
    for (const raw of rawResults) {
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new RunShapeError("Run result has an invalid nested shape.");
      const item = raw as Record<string, unknown>;
      const result: RunResult = { file_path: stringValue(item.file_path), result: stringValue(item.result ?? "PENDING"), remark: stringValue(item.remark ?? "") };
      if (item.example && typeof item.example === "object" && !Array.isArray(item.example)) {
        const example = item.example as Record<string, unknown>;
        const table = Number(example.table), row = Number(example.row);
        if (Number.isInteger(table) && Number.isInteger(row)) result.example = { table, row };
      }
      results.push(result);
    }
  }
  return { name: stringValue(record.name), created_at: stringValue(record.created_at), description: stringValue(record.description), results };
}

export function validateRun(run: TestRun): void {
  if (!run.name.trim()) throw new RunValidationError("name", "Run name must not be empty.");
  if (/\r|\n/.test(run.name)) throw new RunValidationError("name", "Run name must be single-line.");
  if (!run.created_at.trim()) throw new RunValidationError("created_at", "created_at must not be empty.");
  if (/\r|\n/.test(run.created_at)) throw new RunValidationError("created_at", "created_at must be single-line.");
  if (!Array.isArray(run.results)) throw new RunValidationError("results", "Results must be a list.");
  const seen = new Set<string>();
  for (const [index, item] of run.results.entries()) {
    if (!item.file_path) throw new RunValidationError(`results[${index}].file_path`, "file_path must not be empty.");
    const exampleKey = item.example ? `${item.example.table}:${item.example.row}` : "-";
    const key = `${item.file_path}\u0000${exampleKey}`;
    if (seen.has(key)) throw new RunValidationError(`results[${index}].file_path`, `Duplicate run result: '${item.file_path}'.`);
    seen.add(key);
    if (!RUN_RESULTS.includes(item.result as RunResultValue)) throw new RunValidationError(`results[${index}].result`, `Invalid result value: '${item.result}'.`);
  }
}

export function serializeRun(run: TestRun): string {
  validateRun(run);
  return stringifyYaml(run, { sortMapEntries: false, lineWidth: 0 });
}
