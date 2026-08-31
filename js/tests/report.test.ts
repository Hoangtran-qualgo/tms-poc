import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, expect, it } from "vitest";
import { POST as create, GET as list } from "../app/api/reports/[project]/route";
import { GET as get, PATCH as patch, DELETE as remove } from "../app/api/reports/[project]/[file_name]/route";
import { GET as view } from "../app/api/reports/[project]/[file_name]/view/route";

const roots: string[] = [];
afterEach(async () => { await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true }))); });

it("creates, reads, lists, patches, and deletes a validated report", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-report-")); roots.push(root);
  await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n  - ui: UI\n");
  await writeFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "name: Smoke\ncreated_at: 2026-01-01T00:00:00Z\ndescription: ''\nresults: []\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const body = { file_name: "failed", type: "enum_ranking", title: "Failed UI", status: "FAILED", kind: "components", run_paths: ["Alpha/test-run/smoke/run.yaml"] };
    const response = await create(new Request("http://localhost/api/reports/Alpha", { method: "POST", body: JSON.stringify(body) }), { params: Promise.resolve({ project: "Alpha" }) });
    expect(response.status).toBe(201);
    const full = await get(new Request("http://localhost"), { params: Promise.resolve({ project: "Alpha", file_name: "failed.yaml" }) });
    expect(full.status).toBe(200); const saved = await full.json(); expect(saved).toMatchObject({ type: "enum_ranking", title: "Failed UI", kind: "components" });
    expect((await list(new Request("http://localhost"), { params: Promise.resolve({ project: "Alpha" }) })).status).toBe(200);
    const changed = await patch(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ ...saved, created_at: "2027-01-01T00:00:00Z" }) }), { params: Promise.resolve({ project: "Alpha", file_name: "failed.yaml" }) });
    expect(changed.status).toBe(422);
    expect((await remove(new Request("http://localhost", { method: "DELETE" }), { params: Promise.resolve({ project: "Alpha", file_name: "failed.yaml" }) })).status).toBe(204);
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("rejects a report that references a missing run before writing", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-report-invalid-")); roots.push(root); await mkdir(join(root, "Alpha")); await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await create(new Request("http://localhost/api/reports/Alpha", { method: "POST", body: JSON.stringify({ file_name: "bad", type: "tag_ranking", title: "Bad", status: "FAILED", run_paths: ["Alpha/test-run/missing/run.yaml"] }) }), { params: Promise.resolve({ project: "Alpha" }) });
    expect(response.status).toBe(422);
    await expect(readFile(join(root, "Alpha", "report", "bad.yaml"), "utf8")).rejects.toMatchObject({ code: "ENOENT" });
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("recomputes ranking data from current feature tags and run results", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-report-view-")); roots.push(root);
  await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n  - ui: UI\n");
  await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "# enum.components: ui\n@smoke\nFeature: Case\n\nScenario: Case\n  Given a step\n");
  await writeFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "name: Smoke\ncreated_at: 2026-01-01T00:00:00Z\ndescription: ''\nresults:\n  - file_path: Alpha/Checkout/case.feature\n    result: FAILED\n    remark: ''\n");
  await mkdir(join(root, "Alpha", "report"));
  await writeFile(join(root, "Alpha", "report", "failed.yaml"), "type: tag_ranking\ntitle: Failed tags\ncreated_at: 2026-01-02T00:00:00Z\nstatus: FAILED\nrun_paths:\n  - Alpha/test-run/smoke/run.yaml\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await view(new Request("http://localhost"), { params: Promise.resolve({ project: "Alpha", file_name: "failed.yaml" }) });
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({ type: "tag_ranking", total: 1, buckets: [{ value: "smoke", count: 1 }] });
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});
