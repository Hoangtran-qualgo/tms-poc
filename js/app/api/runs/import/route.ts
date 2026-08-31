import { readdir } from "node:fs/promises";
import { relative, resolve } from "node:path";
import { NextResponse } from "next/server";
import { parseAllureReport, splitExampleSuffix, AllureParseError, type ParsedReport } from "../../../../src/lib/allure";
import { resolveDataRoot } from "../../../../src/lib/data-root";
import { parseFeature } from "../../../../src/lib/feature";
import { jsonObject, requiredString, runError } from "../../../../src/lib/run-http";
import { createImportedRun } from "../../../../src/lib/run-storage";
import type { RunResult } from "../../../../src/lib/run";
import { readUtf8File } from "../../../../src/lib/utf8";
import { defaultMethodNotAllowed } from "../../../../src/lib/http-errors";

const MAX_HTML_BYTES = 30 * 1024 * 1024;

async function featureFiles(directory: string): Promise<string[]> {
  const found: string[] = [];
  const entries = await readdir(directory, { withFileTypes: true }).catch((error: unknown) => {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw error;
  });
  for (const entry of entries) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) found.push(...await featureFiles(path));
    else if (entry.isFile() && entry.name.toLowerCase().endsWith(".feature")) found.push(path);
  }
  return found;
}

async function resolveScenarios(project: string, names: string[]): Promise<{ matched: Map<string, string>; ambiguous: Set<string> }> {
  const root = resolveDataRoot();
  const index = new Map<string, string[]>();
  for (const path of await featureFiles(resolve(root, project))) {
    try {
      const feature = parseFeature(await readUtf8File(path));
      if (!feature.scenario.name) continue;
      const key = feature.scenario.name.toLowerCase();
      const hits = index.get(key) ?? [];
      hits.push(relative(root, path).split("\\").join("/"));
      index.set(key, hits);
    } catch { /* malformed cases are skipped by the Python resolver */ }
  }
  const matched = new Map<string, string>(), ambiguous = new Set<string>();
  for (const name of names) {
    const hits = index.get(name.toLowerCase()) ?? [];
    if (hits.length === 1) matched.set(name, hits[0]);
    else if (hits.length > 1) ambiguous.add(name);
  }
  return { matched, ambiguous };
}

type Classified = { no: number; name: string; result: string; match: "matched" | "unmatched" | "ambiguous"; file_path?: string; example?: { table: number; row: number } };

async function classify(report: ParsedReport, project: string): Promise<Classified[]> {
  const splits = report.scenarios.map((scenario) => splitExampleSuffix(scenario.name));
  const bases = [...new Set(splits.map(([base]) => base))];
  const resolution = await resolveScenarios(project, bases);
  return report.scenarios.map((scenario, index) => {
    const [base, example] = splits[index];
    const filePath = resolution.matched.get(base);
    const match = filePath ? "matched" : resolution.ambiguous.has(base) ? "ambiguous" : "unmatched";
    return { no: index + 1, name: scenario.name, result: scenario.result, match, ...(filePath ? { file_path: filePath } : {}), ...(example ? { example } : {}) };
  });
}

function importError(message: string, reasons?: string[]): NextResponse {
  return NextResponse.json({ error: { code: "import_validation_error", message, ...(reasons ? { details: { reasons } } : {}) } }, { status: 422 });
}

function rowMessage(row: Classified, project: string): string {
  const reason = row.match === "ambiguous" ? `multiple cases in project '${project}' share this scenario name` : `no case in project '${project}' has this scenario name`;
  return `${row.no}.${row.name} : cannot import - ${reason}`;
}

async function readInput(request: Request): Promise<{ body: Record<string, unknown>; project: string; html: string }> {
  const body = await jsonObject(request);
  const project = requiredString(body, "project");
  const html = body.html;
  if (typeof html !== "string") throw new Error("Body field 'html' must be a string.");
  if (Buffer.byteLength(html) > MAX_HTML_BYTES) throw new Error("Imported report exceeds the 30 MB limit.");
  return { body, project, html };
}

export async function POST(request: Request) {
  try {
    const { body, project, html } = await readInput(request);
    const report = parseAllureReport(html);
    const rows = await classify(report, project);
    const counts = { total: rows.length, matched: 0, unmatched: 0, ambiguous: 0 };
    const errors: string[] = [];
    for (const row of rows) { counts[row.match] += 1; if (row.match !== "matched") errors.push(rowMessage(row, project)); }
    if (request.url.includes("/preview")) return NextResponse.json({ report_name: report.report_name, created_at: report.created_at, scenarios: rows, counts, errors });
    if (!rows.length) return importError("Import validation failed.", ["No scenarios found to import."]);
    if (errors.length) return importError("Import validation failed.", errors);
    const group = requiredString(body, "group");
    const name = requiredString(body, "name");
    const fileName = requiredString(body, "file_name");
    const description = body.description === undefined ? "" : body.description;
    if (typeof description !== "string") throw new Error("Body field 'description' must be a string.");
    const results: RunResult[] = rows.map((row) => ({ file_path: row.file_path!, result: row.result, remark: "", ...(row.example ? { example: row.example } : {}) }));
    await createImportedRun(project, group, fileName, { name, created_at: report.created_at, description, results });
    return NextResponse.json({ ok: true }, { status: 201 });
  } catch (error) {
    if (error instanceof AllureParseError) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    return runError(error);
  }
}

export const GET = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
