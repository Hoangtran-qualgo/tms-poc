import { readdir, rename, rm, stat, unlink } from "node:fs/promises";
import { resolve } from "node:path";
import { atomicCreateUtf8, atomicWriteUtf8 } from "./atomic-write";
import { resolveDataRoot } from "./data-root";
import { parseReport, serializeReport, type Report } from "./report";
import { parseRun, serializeRun, type TestRun } from "./run";
import { readUtf8File } from "./utf8";
import { validateLogicalSegments } from "./path";
import { markWrite } from "./events";

const TYPED = new Set(["test-run", "report"]);
export class MutationConflictError extends Error {}

export function assertGenericPathAllowed(parts: string[]): void {
  validateLogicalSegments(parts);
  if (parts.length >= 2 && TYPED.has(parts[1])) throw new MutationConflictError(`'${parts[1]}' is a reserved typed area.`);
}

function logicalPath(parts: string[]): string { return parts.join("/"); }
function relocated(value: string, oldKey: string, newKey: string): string { return value === oldKey ? newKey : value.startsWith(`${oldKey}/`) ? `${newKey}${value.slice(oldKey.length)}` : value; }

async function metadataFiles(projectDirectory: string): Promise<string[]> {
  const result: string[] = [];
  for (const area of ["test-run", "report"]) {
    const root = resolve(projectDirectory, area);
    const walk = async (directory: string) => {
      const entries = await readdir(directory, { withFileTypes: true }).catch((error: unknown) => { if ((error as NodeJS.ErrnoException).code === "ENOENT") return []; throw error; });
      for (const entry of entries) {
        const path = resolve(directory, entry.name);
        if (entry.isDirectory()) await walk(path);
        else if (entry.isFile() && entry.name.toLowerCase().endsWith(".yaml")) result.push(path);
      }
    };
    await walk(root);
  }
  return result;
}

type Rewrite = { original: string; target: string; before: string; content: string };
async function planRewrites(source: string, target: string, oldKey: string, newKey: string, project: string): Promise<Rewrite[]> {
  const root = resolveDataRoot();
  const rewrites: Rewrite[] = [];
  for (const path of await metadataFiles(resolve(root, project))) {
    const isRun = path.includes(`/${project}/test-run/`);
    const text = await readUtf8File(path);
    if (isRun) {
      const run: TestRun = parseRun(text);
      let changed = false;
      run.results = run.results.map((item) => { const next = relocated(item.file_path, oldKey, newKey); changed ||= next !== item.file_path; return next === item.file_path ? item : { ...item, file_path: next }; });
      if (changed) rewrites.push({ original: path, target: path.startsWith(source) ? resolve(target, path.slice(source.length + 1)) : path, before: text, content: serializeRun(run) });
    } else {
      const report: Report = parseReport(text);
      const runPaths = report.run_paths.map((item) => relocated(item, oldKey, newKey));
      const casePath = relocated(report.case_path, oldKey, newKey);
      const scope = relocated(report.scope, oldKey, newKey);
      if (runPaths.some((item, index) => item !== report.run_paths[index]) || casePath !== report.case_path || scope !== report.scope) {
        rewrites.push({ original: path, target: path.startsWith(source) ? resolve(target, path.slice(source.length + 1)) : path, before: text, content: serializeReport({ ...report, run_paths: runPaths, case_path: casePath, scope }) });
      }
    }
  }
  return rewrites;
}

export async function renameFolder(parts: string[], newName: string): Promise<void> {
  if (!parts.length) throw new Error("rename_folder requires a non-empty path.");
  assertGenericPathAllowed(parts); validateLogicalSegments([newName]);
  const targetParts = [...parts.slice(0, -1), newName]; assertGenericPathAllowed(targetParts);
  const root = resolveDataRoot(); const source = resolve(root, ...parts); const target = resolve(root, ...targetParts);
  if (!(await stat(source).catch(() => null))?.isDirectory()) throw new Error(`Folder not found: ${source}`);
  if (source === target) return;
  if (await stat(target).then(() => true).catch(() => false)) throw new MutationConflictError(`A folder named '${newName}' already exists.`);
  const oldKey = logicalPath(parts), newKey = logicalPath(targetParts), rewrites = await planRewrites(source, target, oldKey, newKey, parts[0]);
  await rename(source, target); markWrite(source); markWrite(target);
  const written: Rewrite[] = [];
  try { for (const rewrite of rewrites) { await atomicWriteUtf8(rewrite.target, rewrite.content); written.push(rewrite); } }
  catch (error) { await rename(target, source).catch(() => undefined); for (const rewrite of written) await atomicWriteUtf8(rewrite.original, rewrite.before).catch(() => undefined); throw error; }
}

export async function moveFolder(parts: string[], destination: string[]): Promise<void> {
  assertGenericPathAllowed(parts); assertGenericPathAllowed(destination);
  if (parts.length < 3) throw new Error("Only nested folders can be moved.");
  if (destination.length < 1 || destination.length > 9) throw new Error("Destination folder must be a project or folder up to depth 9.");
  if (destination[0] !== parts[0]) throw new Error("Destination folder must be in the same project.");
  const sourceParent = parts.slice(0, -1);
  if (sourceParent.join("/") === destination.join("/")) throw new Error("Destination folder is the same as the source parent.");
  const sourceKey = logicalPath(parts), destinationKey = logicalPath(destination);
  if (destinationKey === sourceKey || destinationKey.startsWith(`${sourceKey}/`)) throw new Error("A folder cannot be moved into itself or a descendant.");
  const root = resolveDataRoot(), source = resolve(root, ...parts), target = resolve(root, ...destination, parts.at(-1)!);
  if (!(await stat(source).catch(() => null))?.isDirectory()) throw new Error(`Folder not found: ${source}`);
  if (!(await stat(resolve(root, ...destination)).catch(() => null))?.isDirectory()) throw new Error("Destination folder does not exist.");
  if (await stat(target).then(() => true).catch(() => false)) throw new MutationConflictError(`A folder named '${parts.at(-1)}' already exists at '${destinationKey}'.`);
  const newKey = logicalPath([...destination, parts.at(-1)!]), rewrites = await planRewrites(source, target, sourceKey, newKey, parts[0]);
  await rename(source, target); markWrite(source); markWrite(target);
  const written: Rewrite[] = [];
  try { for (const rewrite of rewrites) { await atomicWriteUtf8(rewrite.target, rewrite.content); written.push(rewrite); } }
  catch (error) { await rename(target, source).catch(() => undefined); for (const rewrite of written) await atomicWriteUtf8(rewrite.original, rewrite.before).catch(() => undefined); throw error; }
}

export async function deleteFolder(parts: string[]): Promise<void> {
  if (!parts.length) throw new Error("Cannot delete the data root.");
  assertGenericPathAllowed(parts);
  const target = resolve(resolveDataRoot(), ...parts);
  if (!(await stat(target).catch(() => null))) return;
  if (!(await stat(target)).isDirectory()) throw new Error(`Target is a file, not a folder: ${target}`);
  await rm(target, { recursive: true, force: true }); markWrite(target);
}

export async function renameFeature(parts: string[], newName: string): Promise<void> {
  assertGenericPathAllowed(parts); const source = resolve(resolveDataRoot(), ...parts); if (!(await stat(source).catch(() => null))?.isFile()) throw new Error(`File not found: ${source}`);
  const leaf = newName.toLowerCase().endsWith(".feature") ? newName : newName.includes(".") ? (() => { throw new Error(`File name must end with '.feature'; got '${newName}'.`); })() : `${newName}.feature`;
  validateLogicalSegments([leaf]); const target = resolve(resolveDataRoot(), ...parts.slice(0, -1), leaf); if (source === target) return; if (await stat(target).then(() => true).catch(() => false)) throw new MutationConflictError(`A file named '${leaf}' already exists.`);
  const oldKey = logicalPath(parts), newKey = logicalPath([...parts.slice(0, -1), leaf]); const rewrites = await planRewrites(source, target, oldKey, newKey, parts[0]);
  await rename(source, target); markWrite(source); markWrite(target); const written: Rewrite[] = [];
  try { for (const rewrite of rewrites) { await atomicWriteUtf8(rewrite.target, rewrite.content); written.push(rewrite); } }
  catch (error) { await rename(target, source).catch(() => undefined); for (const rewrite of written) await atomicWriteUtf8(rewrite.original, rewrite.before).catch(() => undefined); throw error; }
}

export async function moveFeature(parts: string[], destination: string[]): Promise<void> {
  assertGenericPathAllowed(parts); assertGenericPathAllowed(destination); if (destination.length < 2 || destination.length > 10) throw new Error("Destination folder must be a module or sub-folder.");
  const root = resolveDataRoot(), source = resolve(root, ...parts), sourceParent = parts.slice(0, -1); if (sourceParent.join("/") === destination.join("/")) throw new Error("Destination folder is the same as the source parent.");
  if (!(await stat(source).catch(() => null))?.isFile()) throw new Error(`File not found: ${source}`); if (!(await stat(resolve(root, ...destination)).catch(() => null))?.isDirectory()) throw new Error("Destination folder does not exist.");
  const target = resolve(root, ...destination, parts.at(-1)!); if (await stat(target).then(() => true).catch(() => false)) throw new MutationConflictError(`A file named '${parts.at(-1)}' already exists at '${destination.join("/")}'.`); await rename(source, target); markWrite(source); markWrite(target);
}

export async function duplicateFeature(parts: string[], newName?: string): Promise<string> {
  assertGenericPathAllowed(parts); const root = resolveDataRoot(), source = resolve(root, ...parts); if (!(await stat(source).catch(() => null))?.isFile()) throw new Error(`File not found: ${source}`);
  const contents = await readUtf8File(source);
  if (newName) {
    const leaf = newName.toLowerCase().endsWith(".feature") ? newName : newName.includes(".") ? (() => { throw new Error(`File name must end with '.feature'; got '${newName}'.`); })() : `${newName}.feature`; validateLogicalSegments([leaf]); const target = resolve(root, ...parts.slice(0, -1), leaf); if (await stat(target).then(() => true).catch(() => false)) throw new MutationConflictError(`A file named '${leaf}' already exists.`); await atomicCreateUtf8(target, contents); return leaf;
  }
  const parent = parts.slice(0, -1), stem = parent.at(-1)!;
  const usedNames = new Set((await readdir(resolve(root, ...parent))).map((entry) => entry.toLowerCase()));
  for (let number = 1; ; number += 1) {
    const leaf = `${stem}_${number}.feature`;
    if (usedNames.has(leaf.toLowerCase())) continue;
    validateLogicalSegments([leaf]);
    try { await atomicCreateUtf8(resolve(root, ...parent, leaf), contents); return leaf; }
    catch (error) { if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error; usedNames.add(leaf.toLowerCase()); }
  }
}

export async function deleteFeature(parts: string[]): Promise<void> {
  assertGenericPathAllowed(parts);
  const target = resolve(resolveDataRoot(), ...parts);
  try { await unlink(target); markWrite(target); }
  catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return;
    if ((error as NodeJS.ErrnoException).code === "EISDIR") throw new Error(`Target is a directory, not a file: ${target}`);
    throw error;
  }
}
