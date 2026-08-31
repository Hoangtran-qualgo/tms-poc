import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { describe, expect, it } from "vitest";

import { GET as getTree } from "../app/api/tree/route";
import { GET as getRootFolder } from "../app/api/folders/contents/route";
import { GET as getFolder } from "../app/api/folders/[...path]/route";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");

async function fixtureRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-differential-tree-"));
  await mkdir(join(root, "Alpha", "Checkout", "Nested"), { recursive: true });
  await mkdir(join(root, "Alpha", "test-run", "nightly"), { recursive: true });
  await mkdir(join(root, "Alpha", "report"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "priority:\n  - p1: Priority 1\n");
  await writeFile(join(root, "Alpha", "Checkout", "login.feature"), "@AUTO\nFeature: Login\n\n  Scenario: Valid credentials\n    Given a configured browser\n");
  await writeFile(join(root, "Alpha", "Checkout", "notes.txt"), "ignored by feature summaries");
  return root;
}

async function nodeResponses(root: string): Promise<unknown> {
  const original = process.env.TMS_DATA_ROOT;
  process.env.TMS_DATA_ROOT = root;
  try {
    const tree = await getTree();
    const rootFolder = await getRootFolder();
    const folder = await getFolder(new Request("http://localhost/api/folders/Alpha/Checkout/contents"), { params: Promise.resolve({ path: ["Alpha", "Checkout", "contents"] }) });
    return { tree: await tree.json(), root: await rootFolder.json(), folder: await folder.json() };
  } finally {
    if (original === undefined) delete process.env.TMS_DATA_ROOT;
    else process.env.TMS_DATA_ROOT = original;
  }
}

function pythonResponses(root: string): unknown {
  const script = [
    "import json, sys",
    "from app import create_app",
    "app = create_app(data_root=sys.argv[1])",
    "app.extensions['watcher'].stop()",
    "client = app.test_client()",
    "paths = ['/api/tree', '/api/folders/contents', '/api/folders/Alpha/Checkout/contents']",
    "print(json.dumps({path: client.get(path).get_json() for path in paths}, sort_keys=True))",
  ].join("; ");
  const result = spawnSync(python, ["-c", script, root], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, encoding: "utf8", timeout: 15_000 });
  expect(result.status, result.stderr).toBe(0);
  const payload = JSON.parse(result.stdout) as Record<string, unknown>;
  return { tree: payload["/api/tree"], root: payload["/api/folders/contents"], folder: payload["/api/folders/Alpha/Checkout/contents"] };
}

describe.sequential("Python↔TypeScript tree/folder differential", () => {
  it.skipIf(!existsSync(python))("matches response shapes and persisted-read semantics", async () => {
    const root = await fixtureRoot();
    try { expect(await nodeResponses(root)).toEqual(pythonResponses(root)); }
    finally { await rm(root, { recursive: true, force: true }); }
  });
});
