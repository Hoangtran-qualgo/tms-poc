import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { parse as parseYaml } from "yaml";
import { describe, expect, it } from "vitest";

import { POST as preview } from "../app/api/runs/import/preview/route";
import { POST as commit } from "../app/api/runs/import/route";
import { POST as createGroup } from "../app/api/runs/[project]/groups/route";
import { GET as getRun } from "../app/api/runs/[project]/[group]/[file_name]/route";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");
const runParams = { project: "Alpha", group: "smoke", file_name: "nightly.yaml" };
const encoded = (value: unknown) => Buffer.from(JSON.stringify(value), "utf8").toString("base64");
const html = `<!doctype html><script>d('data/suites.json','${encoded({ children: [{ name: "Epic", children: [{ name: "Checkout", children: [{ name: "Buy", status: "failed", time: { start: 1_700_000_000_001, stop: 1_700_000_000_002 }, }, { name: "Buy", status: "passed", time: { start: 1_700_000_000_003, stop: 1_700_000_000_004 }, }, { name: "Ship", status: "broken", time: { start: 1_700_000_000_005, stop: 1_700_000_000_006 }, }] }] }] })}');d('widgets/summary.json','${encoded({ reportName: "Nightly", time: { start: 1_700_000_000_000 } })}');</script>`;

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-differential-allure-import-"));
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n");
  await writeFile(join(root, "Alpha", "Checkout", "buy.feature"), "Feature: Buy\n\nScenario: Buy\n  Given a cart\n");
  await writeFile(join(root, "Alpha", "Checkout", "ship.feature"), "Feature: Ship\n\nScenario: Ship\n  Given a parcel\n");
  return root;
}

async function nodeMutation(root: string): Promise<unknown> {
  const original = process.env.TMS_DATA_ROOT;
  process.env.TMS_DATA_ROOT = root;
  try {
    const inspected = await preview(new Request("http://localhost/api/runs/import/preview", { method: "POST", body: JSON.stringify({ project: "Alpha", html }) }));
    const group = await createGroup(new Request("http://localhost", { method: "POST", body: JSON.stringify({ name: "smoke" }) }), { params: Promise.resolve({ project: "Alpha" }) });
    const imported = await commit(new Request("http://localhost/api/runs/import", { method: "POST", body: JSON.stringify({ project: "Alpha", group: "smoke", name: "Nightly", file_name: "nightly", description: "Imported", html }) }));
    const run = await getRun(new Request("http://localhost"), { params: Promise.resolve(runParams) });
    return {
      preview_status: inspected.status,
      preview_body: await inspected.json(),
      group_status: group.status,
      imported_status: imported.status,
      imported_body: await imported.json(),
      run_status: run.status,
      run_body: await run.json(),
      source: parseYaml(await readFile(join(root, "Alpha", "test-run", "smoke", "nightly.yaml"), "utf8")),
    };
  } finally {
    if (original === undefined) delete process.env.TMS_DATA_ROOT;
    else process.env.TMS_DATA_ROOT = original;
  }
}

function pythonMutation(root: string): unknown {
  const script = [
    "import json, pathlib, sys, yaml",
    "from app import create_app",
    "root = pathlib.Path(sys.argv[1])",
    "payload = json.loads(sys.stdin.read())",
    "app = create_app(data_root=root)",
    "app.extensions['watcher'].stop()",
    "client = app.test_client()",
    "body = {'project': 'Alpha', 'html': payload['html']}",
    "inspected = client.post('/api/runs/import/preview', json=body)",
    "group = client.post('/api/runs/Alpha/groups', json={'name': 'smoke'})",
    "imported = client.post('/api/runs/import', json={'project': 'Alpha', 'group': 'smoke', 'name': 'Nightly', 'file_name': 'nightly', 'description': 'Imported', 'html': payload['html']})",
    "run = client.get('/api/runs/Alpha/smoke/nightly.yaml')",
    "source = (root / 'Alpha' / 'test-run' / 'smoke' / 'nightly.yaml').read_text()",
    "print(json.dumps({'preview_status': inspected.status_code, 'preview_body': inspected.get_json(), 'group_status': group.status_code, 'imported_status': imported.status_code, 'imported_body': imported.get_json(), 'run_status': run.status_code, 'run_body': run.get_json(), 'source': source}))",
  ].join("; ");
  const result = spawnSync(python, ["-c", script, root], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, input: JSON.stringify({ html }), encoding: "utf8", timeout: 15_000 });
  expect(result.status, result.stderr).toBe(0);
  const payload = JSON.parse(result.stdout) as { source: string; [key: string]: unknown };
  return { ...payload, source: parseYaml(payload.source) };
}

describe.sequential("Python↔TypeScript Allure-import differential", () => {
  it.skipIf(!existsSync(python))("matches preview, retry/status mapping, report timestamp, and imported run persistence", async () => {
    const pythonRoot = await makeRoot();
    const nodeRoot = await makeRoot();
    try { expect(await nodeMutation(nodeRoot)).toEqual(pythonMutation(pythonRoot)); }
    finally { await Promise.all([rm(nodeRoot, { recursive: true, force: true }), rm(pythonRoot, { recursive: true, force: true })]); }
  });
});
