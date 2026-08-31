import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { parse as parseYaml } from "yaml";
import { describe, expect, it } from "vitest";

import { POST as createReport } from "../app/api/reports/[project]/route";
import { GET as getReport, PATCH as patchReport, DELETE as deleteReport } from "../app/api/reports/[project]/[file_name]/route";
import { GET as listReports } from "../app/api/reports/[project]/route";
import { GET as viewReport } from "../app/api/reports/[project]/[file_name]/view/route";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");
const reportParams = { project: "Alpha", file_name: "failed.yaml" };
const reportBody = {
  file_name: "failed",
  type: "tag_ranking",
  title: "Failed tags",
  status: "FAILED",
  run_paths: ["Alpha/test-run/smoke/run.yaml"],
};

function scrubCreatedAt(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(scrubCreatedAt);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, key === "created_at" ? "<created_at>" : scrubCreatedAt(item)]));
  }
  return value;
}

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-differential-report-write-"));
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n  - ui: UI\n");
  await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "@smoke\nFeature: Checkout\n\n  Scenario: Pay\n    Given a cart\n");
  await writeFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "name: Smoke\ncreated_at: '2026-01-01T00:00:00Z'\ndescription: ''\nresults:\n  - file_path: Alpha/Checkout/case.feature\n    result: FAILED\n    remark: ''\n");
  return root;
}

async function nodeMutation(root: string): Promise<unknown> {
  const original = process.env.TMS_DATA_ROOT;
  process.env.TMS_DATA_ROOT = root;
  try {
    const created = await createReport(new Request("http://localhost/api/reports/Alpha", { method: "POST", body: JSON.stringify(reportBody) }), { params: Promise.resolve({ project: "Alpha" }) });
    const read = await getReport(new Request("http://localhost"), { params: Promise.resolve(reportParams) });
    const listed = await listReports(new Request("http://localhost"), { params: Promise.resolve({ project: "Alpha" }) });
    const view = await viewReport(new Request("http://localhost"), { params: Promise.resolve(reportParams) });
    const saved = await read.clone().json() as Record<string, unknown>;
    expect(saved.created_at).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/);
    const updated = await patchReport(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ ...saved, title: "Updated failed tags" }) }), { params: Promise.resolve(reportParams) });
    const afterPatch = await getReport(new Request("http://localhost"), { params: Promise.resolve(reportParams) });
    const changedTimestamp = await patchReport(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ ...(await afterPatch.clone().json()), created_at: "1999-01-01T00:00:00Z" }) }), { params: Promise.resolve(reportParams) });
    const source = parseYaml(await readFile(join(root, "Alpha", "report", "failed.yaml"), "utf8"));
    expect((source as Record<string, unknown>).created_at).toBe(saved.created_at);
    const removed = await deleteReport(new Request("http://localhost", { method: "DELETE" }), { params: Promise.resolve(reportParams) });
    const afterDelete = await listReports(new Request("http://localhost"), { params: Promise.resolve({ project: "Alpha" }) });
    return {
      created_status: created.status,
      created_body: await created.json(),
      read_status: read.status,
      read_body: scrubCreatedAt(saved),
      listed_status: listed.status,
      listed_body: scrubCreatedAt(await listed.json()),
      view_status: view.status,
      view_body: scrubCreatedAt(await view.json()),
      updated_status: updated.status,
      updated_body: await updated.json(),
      after_patch_status: afterPatch.status,
      after_patch_body: scrubCreatedAt(await afterPatch.json()),
      changed_timestamp_status: changedTimestamp.status,
      changed_timestamp_body: await changedTimestamp.json(),
      removed_status: removed.status,
      after_delete_status: afterDelete.status,
      after_delete_body: await afterDelete.json(),
      source: scrubCreatedAt(source),
    };
  } finally {
    if (original === undefined) delete process.env.TMS_DATA_ROOT;
    else process.env.TMS_DATA_ROOT = original;
  }
}

function pythonMutation(root: string): unknown {
  const script = [
    "import json, pathlib, sys",
    "from app import create_app",
    "from app.models import Report",
    "from app.reporting import compute_report",
    "root = pathlib.Path(sys.argv[1])",
    "app = create_app(data_root=root)",
    "app.extensions['watcher'].stop()",
    "client = app.test_client()",
    "body = {'file_name': 'failed', 'type': 'tag_ranking', 'title': 'Failed tags', 'status': 'FAILED', 'run_paths': ['Alpha/test-run/smoke/run.yaml']}",
    "created = client.post('/api/reports/Alpha', json=body)",
    "read = client.get('/api/reports/Alpha/failed.yaml')",
    "listed = client.get('/api/reports/Alpha')",
    "saved = read.get_json()",
    "view = compute_report(app.extensions['storage'], 'Alpha', Report.from_dict(saved))",
    "updated = client.patch('/api/reports/Alpha/failed.yaml', json=dict(saved, title='Updated failed tags'))",
    "after_patch = client.get('/api/reports/Alpha/failed.yaml')",
    "changed_timestamp = client.patch('/api/reports/Alpha/failed.yaml', json=dict(after_patch.get_json(), created_at='1999-01-01T00:00:00Z'))",
    "source = (root / 'Alpha' / 'report' / 'failed.yaml').read_text()",
    "removed = client.delete('/api/reports/Alpha/failed.yaml')",
    "after_delete = client.get('/api/reports/Alpha')",
    "print(json.dumps({'created_status': created.status_code, 'created_body': created.get_json(), 'read_status': read.status_code, 'read_body': saved, 'listed_status': listed.status_code, 'listed_body': listed.get_json(), 'view_status': 200, 'view_body': view, 'updated_status': updated.status_code, 'updated_body': updated.get_json(), 'after_patch_status': after_patch.status_code, 'after_patch_body': after_patch.get_json(), 'changed_timestamp_status': changed_timestamp.status_code, 'changed_timestamp_body': changed_timestamp.get_json(), 'removed_status': removed.status_code, 'after_delete_status': after_delete.status_code, 'after_delete_body': after_delete.get_json(), 'source': source}))",
  ].join("; ");
  const result = spawnSync(python, ["-c", script, root], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, encoding: "utf8", timeout: 15_000 });
  expect(result.status, result.stderr).toBe(0);
  const payload = JSON.parse(result.stdout) as { source: string; [key: string]: unknown };
  return { ...(scrubCreatedAt(payload) as Record<string, unknown>), source: scrubCreatedAt(parseYaml(payload.source)) };
}

describe.sequential("Python↔TypeScript report-write differential", () => {
  it.skipIf(!existsSync(python))("matches report CRUD, live view, immutable timestamp, and persisted YAML semantics", async () => {
    const pythonRoot = await makeRoot();
    const nodeRoot = await makeRoot();
    try { expect(await nodeMutation(nodeRoot)).toEqual(pythonMutation(pythonRoot)); }
    finally { await Promise.all([rm(nodeRoot, { recursive: true, force: true }), rm(pythonRoot, { recursive: true, force: true })]); }
  });
});
