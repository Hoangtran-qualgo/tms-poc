import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { PATCH as patchRun } from "../app/api/runs/[project]/[group]/[file_name]/route";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");
const params = { params: Promise.resolve({ project: "Alpha", group: "smoke", file_name: "run.yaml" }) };
const malformed = { name: "Run", created_at: "2026-01-01T00:00:00Z", description: "", results: { broken: true } };

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-differential-error-"));
  await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
  await writeFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "name: Run\ncreated_at: '2026-01-01T00:00:00Z'\ndescription: ''\nresults: []\n");
  return root;
}

async function nodeResponse(root: string): Promise<unknown> {
  const original = process.env.TMS_DATA_ROOT;
  process.env.TMS_DATA_ROOT = root;
  try {
    const response = await patchRun(new Request("http://localhost", { method: "PATCH", body: JSON.stringify(malformed) }), params);
    const body = await response.json();
    return { status: response.status, body, source: await readFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), "utf8") };
  } finally {
    if (original === undefined) delete process.env.TMS_DATA_ROOT;
    else process.env.TMS_DATA_ROOT = original;
  }
}

function pythonResponse(root: string): unknown {
  const script = [
    "import json, pathlib, sys",
    "from app import create_app",
    "root = pathlib.Path(sys.argv[1])",
    "app = create_app(data_root=root)",
    "app.extensions['watcher'].stop()",
    "client = app.test_client()",
    "body = {'name': 'Run', 'created_at': '2026-01-01T00:00:00Z', 'description': '', 'results': {'broken': True}}",
    "response = client.patch('/api/runs/Alpha/smoke/run.yaml', json=body)",
    "source = (root / 'Alpha' / 'test-run' / 'smoke' / 'run.yaml').read_text()",
    "print(json.dumps({'status': response.status_code, 'body': response.get_json(), 'source': source}))",
  ].join("; ");
  const result = spawnSync(python, ["-c", script, root], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, encoding: "utf8", timeout: 15_000 });
  expect(result.status, result.stderr).toBe(0);
  return JSON.parse(result.stdout);
}

describe.sequential("Python↔TypeScript error-contract differential", () => {
  it.skipIf(!existsSync(python))("preserves the generic 500 for malformed nested run payloads and leaves storage unchanged", async () => {
    const pythonRoot = await makeRoot();
    const nodeRoot = await makeRoot();
    try { expect(await nodeResponse(nodeRoot)).toEqual(pythonResponse(pythonRoot)); }
    finally { await Promise.all([rm(nodeRoot, { recursive: true, force: true }), rm(pythonRoot, { recursive: true, force: true })]); }
  });
});
