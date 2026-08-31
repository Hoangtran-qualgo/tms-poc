import { mkdir, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { POST } from "../app/api/folders/route";
import { POST as createFile } from "../app/api/files/route";

const roots: string[] = [];
async function makeRoot() { const root = await mkdtemp(join(tmpdir(), "tms-folder-create-")); roots.push(root); return root; }
afterEach(async () => { await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true }))); });

describe("POST /api/folders", () => {
  it("creates a project with its default enum file and a child module", async () => {
    const root = await makeRoot();
    const before = process.env.TMS_DATA_ROOT;
    process.env.TMS_DATA_ROOT = root;
    try {
      const project = await POST(new Request("http://localhost/api/folders", { method: "POST", body: JSON.stringify({ parent: "", name: "Alpha" }) }));
      expect(project.status).toBe(201);
      await expect(project.json()).resolves.toEqual({ ok: true });
      await expect(readFile(join(root, "Alpha", "enums.yaml"), "utf8")).resolves.toBe("components:\n");
      const module = await POST(new Request("http://localhost/api/folders", { method: "POST", body: JSON.stringify({ parent: "Alpha", name: "Checkout" }) }));
      expect(module.status).toBe(201);
    } finally {
      if (before === undefined) delete process.env.TMS_DATA_ROOT;
      else process.env.TMS_DATA_ROOT = before;
    }
  });
});

it("creates a canonical feature through POST /api/files and rejects duplicates", async () => {
  const root = await makeRoot();
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const request = () => createFile(new Request("http://localhost/api/files", { method: "POST", body: JSON.stringify({ parent: "Alpha/Checkout", file_name: "case", scenario_name: "Buy", description: "Checkout" }) }));
    await expect((await request()).status).toBe(201);
    await expect((await request()).status).toBe(409);
    await expect(readFile(join(root, "Alpha", "Checkout", "case.feature"), "utf8")).resolves.toContain("Scenario: Buy");
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});
