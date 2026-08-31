import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { GET } from "../app/api/tree/route";
import { resolveDataRoot } from "../src/lib/data-root";
import { listTree } from "../src/lib/tree";

const roots: string[] = [];

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-tree-"));
  roots.push(root);
  return root;
}

afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, { force: true, recursive: true })));
});

describe("listTree", () => {
  it("matches recursive counts, typed-area hiding, and folder-first ordering", async () => {
    const root = await makeRoot();
    const module = join(root, "Alpha", "Checkout");
    await mkdir(join(module, "Nested"), { recursive: true });
    await mkdir(join(root, "Alpha", "test-run"), { recursive: true });
    await mkdir(join(root, "Alpha", "report"), { recursive: true });
    await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n");
    await writeFile(
      join(module, "feature-auto.feature"),
      "@AUTO\nFeature: F\n\n  Scenario: One\n    Given a step\n\n  Scenario: Two\n    When another step\n",
    );
    await writeFile(
      join(module, "scenario-auto.feature"),
      "Feature: F\n\n  @Auto\n  Scenario: One\n    Given a step\n\n  Scenario: Two\n    When another step\n",
    );
    await writeFile(join(module, "broken.feature"), "not valid gherkin");
    await writeFile(join(module, "notes.txt"), "other");

    const tree = await listTree(root);

    expect(tree.children).toHaveLength(1);
    const project = tree.children[0];
    expect(project).toMatchObject({
      type: "folder",
      path: "Alpha",
      counts: { total: 5, auto: 3, non_auto: 2 },
    });
    if (project.type !== "folder") throw new Error("expected folder");
    expect(project.children.map((child) => child.name)).toEqual(["Checkout"]);
    const folder = project.children[0];
    if (folder.type !== "folder") throw new Error("expected folder");
    expect(folder.children[0]).toMatchObject({ type: "folder", name: "Nested" });
    expect(folder.children.slice(1).map((child) => child.name).sort()).toEqual([
      "broken.feature",
      "feature-auto.feature",
      "notes.txt",
      "scenario-auto.feature",
    ]);
  });

  it("counts a zero-scenario feature as one non-auto case", async () => {
    const root = await makeRoot();
    const module = join(root, "Alpha", "Checkout");
    await mkdir(module, { recursive: true });
    await writeFile(join(module, "empty.feature"), "Feature: Empty\n");

    const tree = await listTree(root);
    const project = tree.children[0];
    if (project.type !== "folder") throw new Error("expected folder");
    expect(project.counts).toEqual({ total: 1, auto: 0, non_auto: 1 });
  });
});

describe("resolveDataRoot", () => {
  it("uses TMS_DATA_ROOT when configured and the repository project root otherwise", () => {
    expect(resolveDataRoot("/workspace/js", "/tmp/cases")).toBe("/tmp/cases");
    expect(resolveDataRoot("/workspace/js", undefined)).toBe("/workspace/project");
  });
});

describe("GET /api/tree", () => {
  it("returns the tree JSON for the configured filesystem root", async () => {
    const root = await makeRoot();
    await mkdir(join(root, "Alpha"), { recursive: true });
    await writeFile(join(root, "Alpha", "case.feature"), "Feature: Case\n\nScenario: One\n");

    const originalRoot = process.env.TMS_DATA_ROOT;
    process.env.TMS_DATA_ROOT = root;
    try {
      const response = await GET();
      expect(response.status).toBe(200);
      await expect(response.json()).resolves.toMatchObject({
        children: [{ name: "Alpha", counts: { total: 1, auto: 0, non_auto: 1 } }],
      });
    } finally {
      if (originalRoot === undefined) delete process.env.TMS_DATA_ROOT;
      else process.env.TMS_DATA_ROOT = originalRoot;
    }
  });
});
