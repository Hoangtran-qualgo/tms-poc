import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { POST as createGroup } from "../app/api/runs/[project]/groups/route";
import { POST as createRun } from "../app/api/runs/route";
import { GET as listRuns } from "../app/api/runs/[project]/[group]/route";
import { GET as getRun, PATCH as patchRun, DELETE as deleteRun } from "../app/api/runs/[project]/[group]/[file_name]/route";
import { POST as addCase } from "../app/api/runs/[project]/[group]/[file_name]/cases/route";
import { PATCH as patchCase, DELETE as deleteCase } from "../app/api/runs/[project]/[group]/[file_name]/cases/[...case_path]/route";
import { DELETE as deleteGroup } from "../app/api/runs/[project]/groups/[group]/route";

const roots: string[] = [];
afterEach(async () => { await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true }))); });

describe("run API", () => {
  it("creates, lists, updates, and deletes a run through typed routes", async () => {
    const root = await mkdtemp(join(tmpdir(), "tms-runs-")); roots.push(root); await mkdir(join(root, "Alpha"));
    const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
    try {
      const group = await createGroup(new Request("http://localhost", { method: "POST", body: JSON.stringify({ name: "smoke" }) }), { params: Promise.resolve({ project: "Alpha" }) });
      expect(group.status).toBe(201);
      const created = await createRun(new Request("http://localhost/api/runs", { method: "POST", body: JSON.stringify({ project: "Alpha", group: "smoke", name: "Run 1", file_name: "run-1", case_paths: ["Alpha/Checkout/a.feature"] }) }));
      expect(created.status).toBe(201);
      const full = await getRun(new Request("http://localhost"), { params: Promise.resolve({ project: "Alpha", group: "smoke", file_name: "run-1.yaml" }) });
      expect(full.status).toBe(200);
      const run = await full.json();
      expect(run.results).toEqual([{ file_path: "Alpha/Checkout/a.feature", result: "PENDING", remark: "" }]);
      const listed = await listRuns(new Request("http://localhost"), { params: Promise.resolve({ project: "Alpha", group: "smoke" }) });
      expect(await listed.json()).toMatchObject({ runs: [{ file_name: "run-1.yaml", case_count: 1 }] });
      const add = await addCase(new Request("http://localhost", { method: "POST", body: JSON.stringify({ file_path: "Alpha/Checkout/b.feature" }) }), { params: Promise.resolve({ project: "Alpha", group: "smoke", file_name: "run-1.yaml" }) });
      expect(add.status).toBe(201);
      const update = await patchCase(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ result: "PASSED", remark: "ok" }) }), { params: Promise.resolve({ project: "Alpha", group: "smoke", file_name: "run-1.yaml", case_path: ["Alpha", "Checkout", "b.feature"] }) });
      expect(update.status).toBe(200);
      const after = await getRun(new Request("http://localhost"), { params: Promise.resolve({ project: "Alpha", group: "smoke", file_name: "run-1.yaml" }) });
      expect((await after.json()).results[1]).toMatchObject({ file_path: "Alpha/Checkout/b.feature", result: "PASSED", remark: "ok" });
      expect((await deleteCase(new Request("http://localhost", { method: "DELETE" }), { params: Promise.resolve({ project: "Alpha", group: "smoke", file_name: "run-1.yaml", case_path: ["Alpha", "Checkout", "b.feature"] }) })).status).toBe(204);
      expect((await deleteRun(new Request("http://localhost", { method: "DELETE" }), { params: Promise.resolve({ project: "Alpha", group: "smoke", file_name: "run-1.yaml" }) })).status).toBe(204);
      expect((await deleteGroup(new Request("http://localhost", { method: "DELETE" }), { params: Promise.resolve({ project: "Alpha", group: "smoke" }) })).status).toBe(204);
    } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
  });

  it("rejects a changed created_at without changing the run", async () => {
    const root = await mkdtemp(join(tmpdir(), "tms-runs-immutable-")); roots.push(root); await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
    await writeFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "name: Run\ncreated_at: 2026-01-01T00:00:00Z\ndescription: ''\nresults: []\n");
    const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
    try {
      const response = await patchRun(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ name: "Changed", created_at: "2027-01-01T00:00:00Z", description: "", results: [] }) }), { params: Promise.resolve({ project: "Alpha", group: "smoke", file_name: "run.yaml" }) });
      expect(response.status).toBe(422);
      await expect(readFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "utf8")).resolves.toContain("name: Run");
    } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
  });

  it("preserves the generic 500 contract for malformed nested run JSON", async () => {
    const root = await mkdtemp(join(tmpdir(), "tms-runs-shape-")); roots.push(root); await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
    await writeFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "name: Run\ncreated_at: 2026-01-01T00:00:00Z\ndescription: ''\nresults: []\n");
    const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
    try {
      const response = await patchRun(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ name: "Run", created_at: "2026-01-01T00:00:00Z", results: { bad: true } }) }), { params: Promise.resolve({ project: "Alpha", group: "smoke", file_name: "run.yaml" }) });
      expect(response.status).toBe(500);
      await expect(response.json()).resolves.toMatchObject({ error: { code: "internal_error" } });
    } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
  });
});
