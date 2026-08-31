import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { GET as getFolderContents } from "../app/api/folders/[...path]/route";
import { FolderPathError, listFolder } from "../src/lib/folder";

const roots: string[] = [];

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-folder-"));
  roots.push(root);
  return root;
}

afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, { force: true, recursive: true })));
});

describe("listFolder", () => {
  it("lists projects and hides typed areas from a project", async () => {
    const root = await makeRoot();
    await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
    await mkdir(join(root, "Alpha", "test-run"), { recursive: true });
    await mkdir(join(root, "Alpha", "report"), { recursive: true });
    await mkdir(join(root, "ignore.tmp.1.abcd"), { recursive: true });

    await expect(listFolder(root, [])).resolves.toEqual({ kind: "root", projects: ["Alpha"] });
    await expect(listFolder(root, ["Alpha"])).resolves.toEqual({ kind: "project", modules: ["Checkout"] });
  });

  it("returns best-effort feature summaries with resolved enum labels", async () => {
    const root = await makeRoot();
    const module = join(root, "Alpha", "Checkout");
    await mkdir(join(module, "Nested"), { recursive: true });
    await writeFile(
      join(root, "Alpha", "enums.yaml"),
      "priority:\n  - p1: Priority 1\ncomponents:\n  - login: login\n",
    );
    await writeFile(
      join(module, "good.feature"),
      "# enum.priority: p1\n# enum.components: login\n@feature\nFeature: Checkout\nFeature body\n\n  @scenario\n  Scenario: Buy\n    Given a cart\n",
    );
    await writeFile(join(module, "broken.feature"), "not valid gherkin");
    await writeFile(join(module, "invalid-utf8.feature"), Buffer.from([0xff, 0xfe]));
    await writeFile(join(module, "draft.feature"), "@draft\nFeature: Draft\n");
    await writeFile(join(module, "skip.feature.tmp.1.abcd"), "Feature: ignored");

    const listing = await listFolder(root, ["Alpha", "Checkout"]);
    expect(listing.kind).toBe("module");
    if (listing.kind !== "module") throw new Error("expected module listing");
    expect(listing.folders).toEqual(["Nested"]);
    expect([...listing.features].sort((left, right) => left.file_name.localeCompare(right.file_name))).toEqual(
      [
        {
          file_name: "broken.feature",
          description: "",
          scenario_name: "",
          tags: [],
          enums: [],
        },
        {
          file_name: "draft.feature",
          description: "Draft",
          scenario_name: "",
          tags: ["draft"],
          enums: [],
        },
        {
          file_name: "good.feature",
          description: "Checkout\nFeature body",
          scenario_name: "Buy",
          tags: ["feature", "scenario"],
          enums: [
            { kind: "components", key: "login", label: "" },
            { kind: "priority", key: "p1", label: "Priority 1" },
          ],
        },
        {
          file_name: "invalid-utf8.feature",
          description: "",
          scenario_name: "",
          tags: [],
          enums: [],
        },
      ],
    );
  });

  it("rejects excessive depth and reports a missing requested folder", async () => {
    const root = await makeRoot();
    await expect(listFolder(root, Array.from({ length: 11 }, () => "a"))).rejects.toBeInstanceOf(FolderPathError);
    await expect(listFolder(root, ["missing"])).rejects.toMatchObject({ name: "Error", message: expect.stringContaining("Folder not found:") });
  });
});

describe("GET /api/folders/<path>/contents", () => {
  it("returns the Node filesystem listing", async () => {
    const root = await makeRoot();
    await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });

    const originalRoot = process.env.TMS_DATA_ROOT;
    process.env.TMS_DATA_ROOT = root;
    try {
      const response = await getFolderContents(new Request("http://localhost/api/folders/Alpha/contents"), {
        params: Promise.resolve({ path: ["Alpha", "contents"] }),
      });
      expect(response.status).toBe(200);
      await expect(response.json()).resolves.toEqual({ kind: "project", modules: ["Checkout"] });
    } finally {
      if (originalRoot === undefined) delete process.env.TMS_DATA_ROOT;
      else process.env.TMS_DATA_ROOT = originalRoot;
    }
  });
});
