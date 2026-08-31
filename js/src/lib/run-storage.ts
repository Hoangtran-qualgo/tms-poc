import { mkdir, readdir, rmdir, stat, unlink } from "node:fs/promises";
import { resolve } from "node:path";
import { atomicCreateUtf8, atomicWriteUtf8 } from "./atomic-write";
import { resolveDataRoot } from "./data-root";
import { validateLogicalSegments } from "./path";
import { parseRun, serializeRun, normalizeRunFilename, RunConflictError, type RunResult, type TestRun } from "./run";
import { readUtf8File } from "./utf8";
import { markWrite } from "./events";

const RUN_AREA = "test-run";
const TEMP_FILE_RE = /.+\.tmp\.\d+\.[0-9a-f]+$/i;

export function runFilePath(project: string, group: string, fileName: string): { path: string; name: string } {
  const name = normalizeRunFilename(fileName);
  validateLogicalSegments([project, group, name]);
  return { path: resolve(resolveDataRoot(), project, RUN_AREA, group, name), name };
}

function groupPath(project: string, group: string): string {
  validateLogicalSegments([project, group]);
  return resolve(resolveDataRoot(), project, RUN_AREA, group);
}

export async function listProjects(): Promise<string[]> {
  const root = resolveDataRoot();
  const entries = await readdir(root, { withFileTypes: true }).catch((error: unknown) => {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw error;
  });
  return entries.filter((entry) => entry.isDirectory() && !TEMP_FILE_RE.test(entry.name)).map((entry) => entry.name).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
}

export async function listRunGroups(project: string): Promise<string[]> {
  validateLogicalSegments([project]);
  const target = resolve(resolveDataRoot(), project, RUN_AREA);
  const entries = await readdir(target, { withFileTypes: true }).catch((error: unknown) => {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw error;
  });
  return entries.filter((entry) => entry.isDirectory() && !TEMP_FILE_RE.test(entry.name)).map((entry) => entry.name);
}

export async function createRunGroup(project: string, group: string): Promise<void> {
  validateLogicalSegments([project, group]);
  const root = resolve(resolveDataRoot(), project);
  await stat(root);
  const area = resolve(root, RUN_AREA), target = resolve(area, group);
  try { await mkdir(area); markWrite(area); } catch (error) { if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error; }
  try { await mkdir(target); } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "EEXIST") throw new RunConflictError(`A group named '${group}' already exists.`);
    throw error;
  }
  markWrite(target);
}

export async function deleteRunGroup(project: string, group: string): Promise<void> {
  const target = groupPath(project, group);
  try {
    const entries = await readdir(target);
    if (entries.length) throw new Error(`Group '${group}' is not empty; delete its runs first.`);
    await rmdir(target); markWrite(target);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return;
    throw error;
  }
}

export async function createRun(project: string, group: string, fileName: string, name: string, casePaths: string[], description = ""): Promise<void> {
  const { path } = runFilePath(project, group, fileName);
  await stat(resolve(path, ".."));
  // Match Python's UTC ISO serializer, which keeps the explicit +00:00
  // offset in newly-created run documents.
  const run: TestRun = { name, created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00"), description, results: casePaths.map((file_path) => ({ file_path, result: "PENDING", remark: "" })) };
  try { await atomicCreateUtf8(path, serializeRun(run)); }
  catch (error) { if ((error as NodeJS.ErrnoException).code === "EEXIST") throw new RunConflictError(`A run named '${fileName}' already exists.`); throw error; }
}

export async function createImportedRun(project: string, group: string, fileName: string, run: TestRun): Promise<void> {
  const { path } = runFilePath(project, group, fileName);
  await stat(resolve(path, ".."));
  try { await atomicCreateUtf8(path, serializeRun(run)); }
  catch (error) { if ((error as NodeJS.ErrnoException).code === "EEXIST") throw new RunConflictError(`A run named '${fileName}' already exists.`); throw error; }
}

export async function readRun(project: string, group: string, fileName: string): Promise<TestRun> {
  const { path } = runFilePath(project, group, fileName);
  return parseRun(await readUtf8File(path));
}

export async function writeRun(project: string, group: string, fileName: string, run: TestRun): Promise<void> {
  const { path } = runFilePath(project, group, fileName);
  await stat(/*turbopackIgnore: true*/ path);
  await atomicWriteUtf8(path, serializeRun(run));
}

export async function deleteRun(project: string, group: string, fileName: string): Promise<void> {
  const { path } = runFilePath(project, group, fileName);
  await unlink(path).then(() => markWrite(path)).catch((error: unknown) => { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; });
}

export async function addRunCase(project: string, group: string, fileName: string, filePath: string): Promise<void> {
  if (!filePath) throw new Error("file_path must be a non-empty string.");
  const run = await readRun(project, group, fileName);
  if (run.results.some((item) => item.file_path === filePath)) throw new RunConflictError(`Case '${filePath}' is already in this run.`);
  run.results.push({ file_path: filePath, result: "PENDING", remark: "" });
  await writeRun(project, group, fileName, run);
}

export async function removeRunCase(project: string, group: string, fileName: string, filePath: string): Promise<void> {
  if (!filePath) throw new Error("file_path must be a non-empty string.");
  const run = await readRun(project, group, fileName);
  run.results = run.results.filter((item) => item.file_path !== filePath);
  await writeRun(project, group, fileName, run);
}

export async function updateRunResult(project: string, group: string, fileName: string, filePath: string, result?: string, remark?: string): Promise<void> {
  if (!filePath) throw new Error("file_path must be a non-empty string.");
  if (result === undefined && remark === undefined) throw new Error("update_run_result requires at least one of 'result' or 'remark'.");
  const run = await readRun(project, group, fileName);
  const item = run.results.find((entry) => entry.file_path === filePath);
  if (!item) throw new Error(`Case '${filePath}' is not in this run; add it via add_run_case first.`);
  if (result !== undefined) item.result = result;
  if (remark !== undefined) item.remark = remark;
  await writeRun(project, group, fileName, run);
}

export async function listRuns(project: string, group: string): Promise<Array<Record<string, unknown>>> {
  const target = groupPath(project, group);
  const entries = await readdir(target, { withFileTypes: true }).catch((error: unknown) => {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw error;
  });
  const runs: Array<Record<string, unknown>> = [];
  for (const entry of entries) {
    if (!entry.isFile() || TEMP_FILE_RE.test(entry.name) || !entry.name.toLowerCase().endsWith(".yaml")) continue;
    try {
      const run = await readRun(project, group, entry.name);
      const counts: Record<string, number> = {};
      for (const item of run.results) counts[item.result] = (counts[item.result] ?? 0) + 1;
      runs.push({ file_name: entry.name, name: run.name, created_at: run.created_at, case_count: run.results.length, results_count_by_status: counts });
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") runs.push({ file_name: entry.name, name: "", created_at: "", case_count: 0, results_count_by_status: {} });
    }
  }
  return runs;
}

export type { RunResult, TestRun };
