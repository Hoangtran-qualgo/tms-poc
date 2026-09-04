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

it("moves nested folders under a project or another folder and cascades references", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-folder-move-")); roots.push(root);
  await mkdir(join(root, "Alpha", "Checkout", "legacy"), { recursive: true });
  await mkdir(join(root, "Alpha", "Checkout", "root-child"), { recursive: true });
  await mkdir(join(root, "Alpha", "Regression"), { recursive: true });
  await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n");
  await writeFile(join(root, "Alpha", "Checkout", "legacy", "case.feature"), "Feature: Case\n\nScenario: Case\n  Given a step\n");
  await writeFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "name: Smoke\ncreated_at: 2026-01-01T00:00:00Z\ndescription: ''\nresults:\n  - file_path: Alpha/Checkout/legacy/case.feature\n    result: PENDING\n    remark: ''\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    expect((await renameFolder(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ parent: "Alpha/Regression" }) }), params(["Alpha", "Checkout", "legacy", "move"]))).status).toBe(200);
    await expect(readFile(join(root, "Alpha", "Regression", "legacy", "case.feature"), "utf8")).resolves.toContain("Scenario: Case");
    await expect(readFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "utf8")).resolves.toContain("Alpha/Regression/legacy/case.feature");
    expect((await renameFolder(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ parent: "Alpha" }) }), params(["Alpha", "Checkout", "root-child", "move"]))).status).toBe(200);
    await expect(readdir(join(root, "Alpha", "root-child"))).resolves.toEqual([]);
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("renames, duplicates, and deletes feature files", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-file-mutate-")); roots.push(root); await mkdir(join(root, "Alpha", "Checkout"), { recursive: true }); await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n"); await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "Feature: Case\n\nScenario: Case\n  Given a step\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    expect((await filePatch(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ file_name: "renamed.feature" }) }), params(["Alpha", "Checkout", "case.feature", "rename"]))).status).toBe(200);
    const copied = await duplicate(new Request("http://localhost", { method: "POST", body: "{}" }), params(["Alpha", "Checkout", "renamed.feature", "duplicate"]));
    expect(copied.status).toBe(201);
    await expect(copied.json()).resolves.toEqual({ ok: true, file_name: "Checkout_1.feature" });
    expect((await deleteFile(new Request("http://localhost", { method: "DELETE" }), params(["Alpha", "Checkout", "Checkout_1.feature"]))).status).toBe(204);
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("writes multiple feature files in the same folder", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-multi-write-")); roots.push(root);
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n");
  await writeFile(join(root, "Alpha", "Checkout", "one.feature"), "Feature: One\n\nScenario: One\n");
  await writeFile(join(root, "Alpha", "Checkout", "two.feature"), "Feature: Two\n\nScenario: Two\n");
  const body = (name: string) => ({ description: name, tags: ["deferred"], background: { steps: [] }, scenario: { kind: "scenario", name, tags: ["checked"], steps: [], examples: [] }, enums: {} });
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    expect((await filePatch(new Request("http://localhost", { method: "PATCH", body: JSON.stringify(body("One")) }), params(["Alpha", "Checkout", "one.feature"]))).status).toBe(200);
    expect((await filePatch(new Request("http://localhost", { method: "PATCH", body: JSON.stringify(body("Two")) }), params(["Alpha", "Checkout", "two.feature"]))).status).toBe(200);
    await expect(readFile(join(root, "Alpha", "Checkout", "one.feature"), "utf8")).resolves.toContain("@deferred");
    await expect(readFile(join(root, "Alpha", "Checkout", "two.feature"), "utf8")).resolves.toContain("Scenario: Two");
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});
