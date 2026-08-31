import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { POST as preview } from "../app/api/files/import/preview/route";
import { POST as commit } from "../app/api/files/import/route";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");
const sourceA = "@feat_a\nFeature: A\n  @scenario_a\n  Scenario: Alpha\n    Given alpha\n";
const sourceB = "@feat_b\nFeature: B\n  @scenario_b\n  Scenario: Beta\n    Given beta\n";
const batch = { parent: "Alpha/Checkout", sources: [{ name: "same.feature", source: sourceA }, { name: "same.feature", source: sourceB }], names: ["alpha-case", "beta-case"] };

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-differential-batch-import-"));
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n");
  return root;
}

async function nodeMutation(root: string): Promise<unknown> {
  const original = process.env.TMS_DATA_ROOT;
  process.env.TMS_DATA_ROOT = root;
  try {
    const inspected = await preview(new Request("http://localhost/api/files/import/preview", { method: "POST", body: JSON.stringify(batch) }));
    const created = await commit(new Request("http://localhost/api/files/import", { method: "POST", body: JSON.stringify(batch) }));
    const badBody = { ...batch, names: ["bad-case", "another-case"], sources: [...batch.sources, { name: "notes.txt", source: sourceA }] };
    const rejected = await commit(new Request("http://localhost/api/files/import", { method: "POST", body: JSON.stringify(badBody) }));
    const files = (await readdir(join(root, "Alpha", "Checkout"))).sort();
    const featureSources = Object.fromEntries(await Promise.all(files.filter((name) => name.endsWith(".feature")).map(async (name) => [name, await readFile(join(root, "Alpha", "Checkout", name), "utf8")])));
    return { preview_status: inspected.status, preview_body: await inspected.json(), create_status: created.status, create_body: await created.json(), rejected_status: rejected.status, rejected_body: await rejected.json(), files, feature_sources: featureSources };
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
    "inspected = client.post('/api/files/import/preview', json=payload['batch'])",
    "created = client.post('/api/files/import', json=payload['batch'])",
    "bad = dict(payload['batch'], names=['bad-case', 'another-case'], sources=payload['batch']['sources'] + [{'name': 'notes.txt', 'source': payload['source_a']}])",
    "rejected = client.post('/api/files/import', json=bad)",
    "directory = root / 'Alpha' / 'Checkout'",
    "files = sorted(entry.name for entry in directory.iterdir())",
    "feature_sources = {entry.name: entry.read_text() for entry in directory.iterdir() if entry.name.endswith('.feature')}",
    "print(json.dumps({'preview_status': inspected.status_code, 'preview_body': inspected.get_json(), 'create_status': created.status_code, 'create_body': created.get_json(), 'rejected_status': rejected.status_code, 'rejected_body': rejected.get_json(), 'files': files, 'feature_sources': feature_sources}))",
  ].join("; ");
  const result = spawnSync(python, ["-c", script, root], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, input: JSON.stringify({ batch, source_a: sourceA }), encoding: "utf8", timeout: 15_000 });
  expect(result.status, result.stderr).toBe(0);
  return JSON.parse(result.stdout);
}

describe.sequential("Python↔TypeScript batch-import differential", () => {
  it.skipIf(!existsSync(python))("matches explicit generated-name payloads and all-or-nothing validation", async () => {
    const pythonRoot = await makeRoot();
    const nodeRoot = await makeRoot();
    try { expect(await nodeMutation(nodeRoot)).toEqual(pythonMutation(pythonRoot)); }
    finally { await Promise.all([rm(nodeRoot, { recursive: true, force: true }), rm(pythonRoot, { recursive: true, force: true })]); }
  });
});
