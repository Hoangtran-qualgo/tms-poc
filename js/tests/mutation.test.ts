import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, expect, it } from "vitest";
import { POST as createFolder } from "../app/api/folders/route";
import { PATCH as renameFolder, DELETE as deleteFolder } from "../app/api/folders/[...path]/route";
import { PATCH as filePatch, POST as duplicate, DELETE as deleteFile } from "../app/api/files/[...path]/route";

const roots: string[] = [];
afterEach(async () => { await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true }))); });
const params = (path: string[]) => ({ params: Promise.resolve({ path }) });

it("renames folders with run-reference cascade and recursively deletes them", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-folder-mutate-")); roots.push(root);
  await mkdir(join(root, "Alpha", "Checkout", "nested"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n");
  await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "Feature: Case\n\nScenario: Case\n  Given a step\n");
  await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
  await writeFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "name: Smoke\ncreated_at: 2026-01-01T00:00:00Z\ndescription: ''\nresults:\n  - file_path: Alpha/Checkout/case.feature\n    result: PENDING\n    remark: ''\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const renamed = await renameFolder(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ name: "Basket" }) }), params(["Alpha", "Checkout"]));
    expect(renamed.status).toBe(200);
    await expect(readFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "utf8")).resolves.toContain("Alpha/Basket/case.feature");
    expect((await deleteFolder(new Request("http://localhost", { method: "DELETE" }), params(["Alpha", "Basket"]))).status).toBe(204);
    await expect(readdir(join(root, "Alpha", "Basket"))).rejects.toMatchObject({ code: "ENOENT" });
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("prohibits generic mutations in typed areas", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-typed-guard-")); roots.push(root); await mkdir(join(root, "Alpha", "test-run"), { recursive: true });
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    expect((await renameFolder(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ name: "other" }) }), params(["Alpha", "test-run"]))).status).toBe(409);
    expect((await deleteFolder(new Request("http://localhost", { method: "DELETE" }), params(["Alpha", "test-run"]))).status).toBe(409);
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("renames, duplicates, and deletes feature files", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-file-mutate-")); roots.push(root); await mkdir(join(root, "Alpha", "Checkout"), { recursive: true }); await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n"); await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "Feature: Case\n\nScenario: Case\n  Given a step\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    expect((await filePatch(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ file_name: "renamed.feature" }) }), params(["Alpha", "Checkout", "case.feature", "rename"]))).status).toBe(200);
    expect((await duplicate(new Request("http://localhost", { method: "POST", body: JSON.stringify({ file_name: "copy" }) }), params(["Alpha", "Checkout", "renamed.feature", "duplicate"]))).status).toBe(201);
    expect((await deleteFile(new Request("http://localhost", { method: "DELETE" }), params(["Alpha", "Checkout", "copy.feature"]))).status).toBe(204);
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});
