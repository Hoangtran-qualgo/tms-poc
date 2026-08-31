import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { parse as parseYaml } from "yaml";
import { describe, expect, it } from "vitest";

import { POST as createGroup } from "../app/api/runs/[project]/groups/route";
import { POST as createRun } from "../app/api/runs/route";
import { GET as getRun } from "../app/api/runs/[project]/[group]/[file_name]/route";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");
const runParams = { project: "Alpha", group: "smoke", file_name: "fresh.yaml" };
const runBody = { project: "Alpha", group: "smoke", name: "Fresh run", file_name: "fresh", case_paths: ["Alpha/Checkout/case.feature"], description: "Description" };

function scrubCreatedAt(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(scrubCreatedAt);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, key === "created_at" ? "<created_at>" : scrubCreatedAt(item)]));
  return value;
}

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-differential-run-create-"));
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n");
  await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "Feature: Case\n\nScenario: Case\n  Given a step\n");
  return root;
}

async function nodeMutation(root: string): Promise<unknown> {
  const original = process.env.TMS_DATA_ROOT;
  process.env.TMS_DATA_ROOT = root;
  try {
    const group = await createGroup(new Request("http://localhost", { method: "POST", body: JSON.stringify({ name: "smoke" }) }), { params: Promise.resolve({ project: "Alpha" }) });
    const created = await createRun(new Request("http://localhost/api/runs", { method: "POST", body: JSON.stringify(runBody) }));
    const run = await getRun(new Request("http://localhost"), { params: Promise.resolve(runParams) });
    const body = await run.json() as Record<string, unknown>;
    expect(body.created_at).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/);
    return { group_status: group.status, create_status: created.status, create_body: await created.json(), run_status: run.status, run_body: scrubCreatedAt(body), source: scrubCreatedAt(parseYaml(await readFile(join(root, "Alpha", "test-run", "smoke", "fresh.yaml"), "utf8"))) };
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
    "group = client.post('/api/runs/Alpha/groups', json={'name': 'smoke'})",
    "created = client.post('/api/runs', json={'project': 'Alpha', 'group': 'smoke', 'name': 'Fresh run', 'file_name': 'fresh', 'case_paths': ['Alpha/Checkout/case.feature'], 'description': 'Description'})",
    "run = client.get('/api/runs/Alpha/smoke/fresh.yaml')",
    "source = (root / 'Alpha' / 'test-run' / 'smoke' / 'fresh.yaml').read_text()",
    "print(json.dumps({'group_status': group.status_code, 'create_status': created.status_code, 'create_body': created.get_json(), 'run_status': run.status_code, 'run_body': run.get_json(), 'source': source}))",
  ].join("; ");
  const result = spawnSync(python, ["-c", script, root], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, encoding: "utf8", timeout: 15_000 });
  expect(result.status, result.stderr).toBe(0);
  const payload = JSON.parse(result.stdout) as { source: string; [key: string]: unknown };
  return { ...scrubCreatedAt(payload) as Record<string, unknown>, source: scrubCreatedAt(parseYaml(payload.source)) };
}

describe.sequential("Python↔TypeScript fresh-run differential", () => {
  it.skipIf(!existsSync(python))("matches group/create/read and persisted timestamp semantics", async () => {
    const pythonRoot = await makeRoot();
    const nodeRoot = await makeRoot();
    try { expect(await nodeMutation(nodeRoot)).toEqual(pythonMutation(pythonRoot)); }
    finally { await Promise.all([rm(nodeRoot, { recursive: true, force: true }), rm(pythonRoot, { recursive: true, force: true })]); }
  });
});
