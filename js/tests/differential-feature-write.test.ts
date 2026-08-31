import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, mkdir, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { describe, expect, it } from "vitest";

import { POST as createFile } from "../app/api/files/route";
import { GET as readFileRoute, PATCH as patchFile, PUT as putRawFile } from "../app/api/files/[...path]/route";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");
const featurePath = ["Alpha", "Checkout", "case.feature"];
const patchPayload = {
  description: "Checkout\nFlow",
  tags: ["smoke", "smoke"],
  background: { steps: [{ keyword: "Given", text: "a cart", data_table: [["header", "long-value"], ["x", "y"]] }] },
  scenario: { kind: "scenario", name: "Updated", tags: ["critical", "critical"], steps: [{ keyword: "When", text: "paying", data_table: null }], examples: [] },
  enums: {},
};
const rawSource = "Feature: Raw\r\n\r\n  Scenario: Raw\r\n    Given   spacing\r\n";

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-differential-feature-write-"));
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  return root;
}

async function nodeMutation(root: string): Promise<unknown> {
  const original = process.env.TMS_DATA_ROOT;
  process.env.TMS_DATA_ROOT = root;
  try {
    const post = await createFile(new Request("http://localhost/api/files", { method: "POST", body: JSON.stringify({ parent: "Alpha/Checkout", file_name: "case.feature", scenario_name: "Initial", description: "Initial" }) }));
    const patch = await patchFile(new Request("http://localhost/api/files/Alpha/Checkout/case.feature", { method: "PATCH", body: JSON.stringify(patchPayload) }), { params: Promise.resolve({ path: featurePath }) });
    const patched = await readFileRoute(new Request("http://localhost"), { params: Promise.resolve({ path: featurePath }) });
    const raw = await putRawFile(new Request("http://localhost", { method: "PUT", body: rawSource }), { params: Promise.resolve({ path: [...featurePath, "raw"] }) });
    return { post_status: post.status, post_body: await post.json(), patch_status: patch.status, patch_body: await patch.json(), patched: await patched.json(), raw_status: raw.status, raw_body: await raw.json(), raw_source: await readFile(join(root, ...featurePath), "utf8") };
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
    "payload = json.loads(sys.stdin.read())",
    "app = create_app(data_root=root)",
    "app.extensions['watcher'].stop()",
    "client = app.test_client()",
    "post = client.post('/api/files', json={'parent': 'Alpha/Checkout', 'file_name': 'case.feature', 'scenario_name': 'Initial', 'description': 'Initial'})",
    "patched_request = client.patch('/api/files/Alpha/Checkout/case.feature', json=payload['patch'])",
    "patched = client.get('/api/files/Alpha/Checkout/case.feature')",
    "raw = client.put('/api/files/Alpha/Checkout/case.feature/raw', data=payload['raw'], content_type='text/plain')",
    "source = (root / 'Alpha' / 'Checkout' / 'case.feature').read_text()",
    "print(json.dumps({'post_status': post.status_code, 'post_body': post.get_json(), 'patch_status': patched_request.status_code, 'patch_body': patched_request.get_json(), 'patched': patched.get_json(), 'raw_status': raw.status_code, 'raw_body': raw.get_json(), 'raw_source': source}, sort_keys=True))",
  ].join("; ");
  const result = spawnSync(python, ["-c", script, root], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, input: JSON.stringify({ patch: patchPayload, raw: rawSource }), encoding: "utf8", timeout: 15_000 });
  expect(result.status, result.stderr).toBe(0);
  return JSON.parse(result.stdout);
}

describe.sequential("Python↔TypeScript feature-write differential", () => {
  it.skipIf(!existsSync(python))("matches structured canonical writes and raw source-preserving writes", async () => {
    const pythonRoot = await makeRoot();
    const nodeRoot = await makeRoot();
    try { expect(await nodeMutation(nodeRoot)).toEqual(pythonMutation(pythonRoot)); }
    finally { await Promise.all([rm(nodeRoot, { recursive: true, force: true }), rm(pythonRoot, { recursive: true, force: true })]); }
  });
});
