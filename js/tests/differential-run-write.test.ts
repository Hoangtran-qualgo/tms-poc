import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { parse as parseYaml } from "yaml";
import { describe, expect, it } from "vitest";

import { POST as createGroup } from "../app/api/runs/[project]/groups/route";
import { GET as getGroupRuns } from "../app/api/runs/[project]/[group]/route";
import { GET as getRun } from "../app/api/runs/[project]/[group]/[file_name]/route";
import { POST as addCase } from "../app/api/runs/[project]/[group]/[file_name]/cases/route";
import { PATCH as patchCase } from "../app/api/runs/[project]/[group]/[file_name]/cases/[...case_path]/route";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");
const runParams = { project: "Alpha", group: "smoke", file_name: "run.yaml" };
const runSource = "name: Baseline\ncreated_at: '2026-01-01T00:00:00Z'\ndescription: baseline\nresults:\n  - file_path: Alpha/Checkout/a.feature\n    result: PENDING\n    remark: ''\n";

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-differential-run-write-"));
  await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
  await writeFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), runSource);
  return root;
}

async function nodeMutation(root: string): Promise<unknown> {
  const original = process.env.TMS_DATA_ROOT;
  process.env.TMS_DATA_ROOT = root;
  try {
    const group = await createGroup(new Request("http://localhost", { method: "POST", body: JSON.stringify({ name: "regression" }) }), { params: Promise.resolve({ project: "Alpha" }) });
    const initial = await getRun(new Request("http://localhost"), { params: Promise.resolve(runParams) });
    const add = await addCase(new Request("http://localhost", { method: "POST", body: JSON.stringify({ file_path: "Alpha/Checkout/b.feature" }) }), { params: Promise.resolve(runParams) });
    const update = await patchCase(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ result: "PASSED", remark: "ok" }) }), { params: Promise.resolve({ ...runParams, case_path: ["Alpha", "Checkout", "b.feature"] }) });
    const after = await getRun(new Request("http://localhost"), { params: Promise.resolve(runParams) });
    const listed = await getGroupRuns(new Request("http://localhost"), { params: Promise.resolve({ project: "Alpha", group: "smoke" }) });
    const emptyGroup = await getGroupRuns(new Request("http://localhost"), { params: Promise.resolve({ project: "Alpha", group: "regression" }) });
    return { group_status: group.status, initial_status: initial.status, initial: await initial.json(), add_status: add.status, update_status: update.status, after: await after.json(), listed: await listed.json(), empty_group_status: emptyGroup.status, empty_group: await emptyGroup.json(), source: parseYaml(await readFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "utf8")) };
  } finally {
    if (original === undefined) delete process.env.TMS_DATA_ROOT;
    else process.env.TMS_DATA_ROOT = original;
  }
}

function pythonMutation(root: string): unknown {
  const script = [
    "import json, pathlib, sys",
    "from app import create_app",
    "root = pathlib.Path(sys.argv[1])",
    "app = create_app(data_root=root)",
    "app.extensions['watcher'].stop()",
    "client = app.test_client()",
    "group = client.post('/api/runs/Alpha/groups', json={'name': 'regression'})",
    "initial = client.get('/api/runs/Alpha/smoke/run.yaml')",
    "add = client.post('/api/runs/Alpha/smoke/run.yaml/cases', json={'file_path': 'Alpha/Checkout/b.feature'})",
    "update = client.patch('/api/runs/Alpha/smoke/run.yaml/cases/Alpha/Checkout/b.feature', json={'result': 'PASSED', 'remark': 'ok'})",
    "after = client.get('/api/runs/Alpha/smoke/run.yaml')",
    "listed = client.get('/api/runs/Alpha/smoke')",
    "empty_group = client.get('/api/runs/Alpha/regression')",
    "source = (root / 'Alpha' / 'test-run' / 'smoke' / 'run.yaml').read_text()",
    "print(json.dumps({'group_status': group.status_code, 'initial_status': initial.status_code, 'initial': initial.get_json(), 'add_status': add.status_code, 'update_status': update.status_code, 'after': after.get_json(), 'listed': listed.get_json(), 'empty_group_status': empty_group.status_code, 'empty_group': empty_group.get_json(), 'source': source}))",
  ].join("; ");
  const result = spawnSync(python, ["-c", script, root], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, encoding: "utf8", timeout: 15_000 });
  expect(result.status, result.stderr).toBe(0);
  const payload = JSON.parse(result.stdout) as { source: string; [key: string]: unknown };
  return { ...payload, source: parseYaml(payload.source) };
}

describe.sequential("Python↔TypeScript run-write differential", () => {
  it.skipIf(!existsSync(python))("matches run group/case mutations and persisted YAML semantics", async () => {
    const pythonRoot = await makeRoot();
    const nodeRoot = await makeRoot();
    try { expect(await nodeMutation(nodeRoot)).toEqual(pythonMutation(pythonRoot)); }
    finally { await Promise.all([rm(nodeRoot, { recursive: true, force: true }), rm(pythonRoot, { recursive: true, force: true })]); }
  });
});
