import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { parse as parseYaml } from "yaml";
import { describe, expect, it } from "vitest";

import { PATCH as renameFile } from "../app/api/files/[...path]/route";
import { PATCH as renameFolder } from "../app/api/folders/[...path]/route";
import { GET as getRun } from "../app/api/runs/[project]/[group]/[file_name]/route";
import { GET as getReport } from "../app/api/reports/[project]/[file_name]/route";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");
const fixedRun = "name: Smoke\ncreated_at: '2026-01-01T00:00:00+00:00'\ndescription: ''\nresults:\n  - file_path: Alpha/Checkout/case.feature\n    result: PENDING\n    remark: ''\n";
const fixedTrend = "type: case_trend\ntitle: Trend\ncreated_at: '2026-01-02T00:00:00+00:00'\ncase_path: Alpha/Checkout/case.feature\nrun_paths:\n  - Alpha/test-run/smoke/run.yaml\n";
const fixedInventory = "type: tag_inventory\ntitle: Inventory\ncreated_at: '2026-01-03T00:00:00+00:00'\ntag: smoke\nscope: Alpha/Checkout\n";

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-differential-relocation-"));
  await mkdir(join(root, "Alpha", "Checkout", "nested"), { recursive: true });
  await mkdir(join(root, "Alpha", "test-run", "smoke"), { recursive: true });
  await mkdir(join(root, "Alpha", "report"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n");
  await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "Feature: Case\n\nScenario: Case\n  Given a step\n");
  await writeFile(join(root, "Alpha", "Checkout", "nested", "keep.feature"), "Feature: Keep\n\nScenario: Keep\n  Given a step\n");
  await writeFile(join(root, "Alpha", "test-run", "smoke", "run.yaml"), fixedRun);
  await writeFile(join(root, "Alpha", "report", "trend.yaml"), fixedTrend);
  await writeFile(join(root, "Alpha", "report", "inventory.yaml"), fixedInventory);
  return root;
}

async function snapshot(root: string, project: string): Promise<unknown> {
  const runPath = join(root, project, "test-run", "smoke", "run.yaml");
  const reportPath = (name: string) => join(root, project, "report", name);
  const sourcePath = join(root, project, "Basket", "primary.feature");
  return {
    run: parseYaml(await readFile(runPath, "utf8")),
    trend: parseYaml(await readFile(reportPath("trend.yaml"), "utf8")),
    inventory: parseYaml(await readFile(reportPath("inventory.yaml"), "utf8")),
    feature: await readFile(sourcePath, "utf8"),
    project_entries: (await readdir(join(root, project), { withFileTypes: true })).map((entry) => `${entry.name}:${entry.isDirectory() ? "dir" : "file"}`).sort(),
  };
}

async function nodeMutation(root: string): Promise<unknown> {
  const original = process.env.TMS_DATA_ROOT;
  process.env.TMS_DATA_ROOT = root;
  try {
    const renamedFile = await renameFile(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ file_name: "primary" }) }), { params: Promise.resolve({ path: ["Alpha", "Checkout", "case.feature", "rename"] }) });
    const renamedFolder = await renameFolder(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ name: "Basket" }) }), { params: Promise.resolve({ path: ["Alpha", "Checkout"] }) });
    const renamedProject = await renameFolder(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ name: "Beta" }) }), { params: Promise.resolve({ path: ["Alpha"] }) });
    const run = await getRun(new Request("http://localhost"), { params: Promise.resolve({ project: "Beta", group: "smoke", file_name: "run.yaml" }) });
    const trend = await getReport(new Request("http://localhost"), { params: Promise.resolve({ project: "Beta", file_name: "trend.yaml" }) });
    const inventory = await getReport(new Request("http://localhost"), { params: Promise.resolve({ project: "Beta", file_name: "inventory.yaml" }) });
    return { renamed_file_status: renamedFile.status, renamed_folder_status: renamedFolder.status, renamed_project_status: renamedProject.status, run_status: run.status, trend_status: trend.status, inventory_status: inventory.status, run_body: await run.json(), trend_body: await trend.json(), inventory_body: await inventory.json(), snapshot: await snapshot(root, "Beta") };
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
    "renamed_file = client.patch('/api/files/Alpha/Checkout/case.feature/rename', json={'file_name': 'primary'})",
    "renamed_folder = client.patch('/api/folders/Alpha/Checkout', json={'name': 'Basket'})",
    "renamed_project = client.patch('/api/folders/Alpha', json={'name': 'Beta'})",
    "run = client.get('/api/runs/Beta/smoke/run.yaml')",
    "trend = client.get('/api/reports/Beta/trend.yaml')",
    "inventory = client.get('/api/reports/Beta/inventory.yaml')",
    "run_path = root / 'Beta' / 'test-run' / 'smoke' / 'run.yaml'",
    "trend_path = root / 'Beta' / 'report' / 'trend.yaml'",
    "inventory_path = root / 'Beta' / 'report' / 'inventory.yaml'",
    "feature_path = root / 'Beta' / 'Basket' / 'primary.feature'",
    "snapshot = {'run': yaml.safe_load(run_path.read_text()), 'trend': yaml.safe_load(trend_path.read_text()), 'inventory': yaml.safe_load(inventory_path.read_text()), 'feature': feature_path.read_text(), 'project_entries': sorted(f'{entry.name}:{\"dir\" if entry.is_dir() else \"file\"}' for entry in (root / 'Beta').iterdir())}",
    "print(json.dumps({'renamed_file_status': renamed_file.status_code, 'renamed_folder_status': renamed_folder.status_code, 'renamed_project_status': renamed_project.status_code, 'run_status': run.status_code, 'trend_status': trend.status_code, 'inventory_status': inventory.status_code, 'run_body': run.get_json(), 'trend_body': trend.get_json(), 'inventory_body': inventory.get_json(), 'snapshot': snapshot}))",
  ].join("; ");
  const result = spawnSync(python, ["-c", script, root], { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, encoding: "utf8", timeout: 15_000 });
  expect(result.status, result.stderr).toBe(0);
  return JSON.parse(result.stdout);
}

describe.sequential("Python↔TypeScript relocation differential", () => {
  it.skipIf(!existsSync(python))("matches file, folder, and project rename cascades across run/report references", async () => {
    const pythonRoot = await makeRoot();
    const nodeRoot = await makeRoot();
    try { expect(await nodeMutation(nodeRoot)).toEqual(pythonMutation(pythonRoot)); }
    finally { await Promise.all([rm(nodeRoot, { recursive: true, force: true }), rm(pythonRoot, { recursive: true, force: true })]); }
  });
});
