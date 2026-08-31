import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { parse as parseYaml } from "yaml";
import { describe, expect, it } from "vitest";

import { GET as getEnums, PUT as putEnums } from "../app/api/enums/[project]/route";
import { POST as renameEnum } from "../app/api/enums/[project]/rename/route";
import { POST as clearEnums } from "../app/api/enums/[project]/clear/route";
import { GET as enumUsage } from "../app/api/enums/[project]/usage/route";
import { PUT as putKindLabels } from "../app/api/enums/[project]/kind-labels/route";
import { GET as getFeature } from "../app/api/files/[...path]/route";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");
const enumParams = { params: Promise.resolve({ project: "Alpha" }) };
const featureParams = { params: Promise.resolve({ path: ["Alpha", "Checkout", "case.feature"] }) };
const updatedVocabulary = { components: { old: "Old label", keep: "Keep" }, sprint: { one: "One" } };

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-differential-enum-write-"));
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n  - old: Old\n  - keep: Keep\nsprint:\n  - one: One\n");
  await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "# enum.components: old\n# enum.sprint: one\nFeature: Case\n\nScenario: Buy\n  Given a step\n");
  return root;
}

async function nodeMutation(root: string): Promise<unknown> {
  const original = process.env.TMS_DATA_ROOT;
  process.env.TMS_DATA_ROOT = root;
  try {
    const initial = await getEnums(new Request("http://localhost"), enumParams);
    const replaced = await putEnums(new Request("http://localhost", { method: "PUT", body: JSON.stringify(updatedVocabulary) }), enumParams);
    const usageBefore = await enumUsage(new Request("http://localhost/api/enums/Alpha/usage?kind=components&key=old"), enumParams);
    const labels = await putKindLabels(new Request("http://localhost", { method: "PUT", body: JSON.stringify({ components: "Components", sprint: "Sprint" }) }), enumParams);
    const renamed = await renameEnum(new Request("http://localhost", { method: "POST", body: JSON.stringify({ kind: "components", old_key: "old", new_key: "new" }) }), enumParams);
    const after = await getEnums(new Request("http://localhost"), enumParams);
    const feature = await getFeature(new Request("http://localhost"), featureParams);
    const usageAfter = await enumUsage(new Request("http://localhost/api/enums/Alpha/usage?kind=components&key=new"), enumParams);
    const clear = await clearEnums(new Request("http://localhost"), enumParams);
    const remove = await putEnums(new Request("http://localhost", { method: "PUT", body: JSON.stringify({ components: { keep: "Keep" }, sprint: { one: "One" } }) }), enumParams);
    return {
      initial_status: initial.status,
      initial_body: await initial.json(),
      replaced_status: replaced.status,
      replaced_body: await replaced.json(),
      usage_before_status: usageBefore.status,
      usage_before_body: await usageBefore.json(),
      labels_status: labels.status,
      labels_body: await labels.json(),
      renamed_status: renamed.status,
      renamed_body: await renamed.json(),
      after_status: after.status,
      after_body: await after.json(),
      feature_status: feature.status,
      feature_body: await feature.json(),
      usage_after_status: usageAfter.status,
      usage_after_body: await usageAfter.json(),
      clear_status: clear.status,
      clear_body: await clear.json(),
      remove_status: remove.status,
      remove_body: await remove.json(),
      enums_source: parseYaml(await readFile(join(root, "Alpha", "enums.yaml"), "utf8")),
      labels_source: parseYaml(await readFile(join(root, "Alpha", "enum-kind-labels.yaml"), "utf8")),
      feature_source: await readFile(join(root, "Alpha", "Checkout", "case.feature"), "utf8"),
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
    "app = create_app(data_root=root)",
    "app.extensions['watcher'].stop()",
    "client = app.test_client()",
    "vocab = {'components': {'old': 'Old label', 'keep': 'Keep'}, 'sprint': {'one': 'One'}}",
    "initial = client.get('/api/enums/Alpha')",
    "replaced = client.put('/api/enums/Alpha', json=vocab)",
    "usage_before = client.get('/api/enums/Alpha/usage?kind=components&key=old')",
    "labels = client.put('/api/enums/Alpha/kind-labels', json={'components': 'Components', 'sprint': 'Sprint'})",
    "renamed = client.post('/api/enums/Alpha/rename', json={'kind': 'components', 'old_key': 'old', 'new_key': 'new'})",
    "after = client.get('/api/enums/Alpha')",
    "feature = client.get('/api/files/Alpha/Checkout/case.feature')",
    "usage_after = client.get('/api/enums/Alpha/usage?kind=components&key=new')",
    "clear = client.post('/api/enums/Alpha/clear')",
    "remove = client.put('/api/enums/Alpha', json={'components': {'keep': 'Keep'}, 'sprint': {'one': 'One'}})",
    "enums_source = yaml.safe_load((root / 'Alpha' / 'enums.yaml').read_text())",
    "labels_source = yaml.safe_load((root / 'Alpha' / 'enum-kind-labels.yaml').read_text())",
    "feature_source = (root / 'Alpha' / 'Checkout' / 'case.feature').read_text()",
    "print(json.dumps({'initial_status': initial.status_code, 'initial_body': initial.get_json(), 'replaced_status': replaced.status_code, 'replaced_body': replaced.get_json(), 'usage_before_status': usage_before.status_code, 'usage_before_body': usage_before.get_json(), 'labels_status': labels.status_code, 'labels_body': labels.get_json(), 'renamed_status': renamed.status_code, 'renamed_body': renamed.get_json(), 'after_status': after.status_code, 'after_body': after.get_json(), 'feature_status': feature.status_code, 'feature_body': feature.get_json(), 'usage_after_status': usage_after.status_code, 'usage_after_body': usage_after.get_json(), 'clear_status': clear.status_code, 'clear_body': clear.get_json(), 'remove_status': remove.status_code, 'remove_body': remove.get_json(), 'enums_source': enums_source, 'labels_source': labels_source, 'feature_source': feature_source}))",
  ].join("; ");
  const result = spawnSync(python, ["-c", script, root], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, encoding: "utf8", timeout: 15_000 });
  expect(result.status, result.stderr).toBe(0);
  return JSON.parse(result.stdout);
}

describe.sequential("Python↔TypeScript enum-write differential", () => {
  it.skipIf(!existsSync(python))("matches vocabulary replace, labels, usage, rename cascade, and in-use guards", async () => {
    const pythonRoot = await makeRoot();
    const nodeRoot = await makeRoot();
    try { expect(await nodeMutation(nodeRoot)).toEqual(pythonMutation(pythonRoot)); }
    finally { await Promise.all([rm(nodeRoot, { recursive: true, force: true }), rm(pythonRoot, { recursive: true, force: true })]); }
  });
});
