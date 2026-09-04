import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { POST } from "../app/api/folders/route";
import { PATCH as renameFolder } from "../app/api/folders/[...path]/route";
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

it("creates canonical features with the next available folder-based filename", async () => {
  const root = await makeRoot();
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await writeFile(join(root, "Alpha", "Checkout", "checkout_1.feature"), "Feature: Existing\n\nScenario: Existing\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const request = () => createFile(new Request("http://localhost/api/files", { method: "POST", body: JSON.stringify({ parent: "Alpha/Checkout", scenario_name: "Buy", description: "Checkout" }) }));
    await expect((await request()).status).toBe(201);
    await expect((await request()).status).toBe(201);
    await expect(readFile(join(root, "Alpha", "Checkout", "Checkout_2.feature"), "utf8")).resolves.toContain("Scenario: Buy");
    await expect(readFile(join(root, "Alpha", "Checkout", "Checkout_3.feature"), "utf8")).resolves.toContain("Feature: Checkout");
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("keeps existing filenames when a folder is renamed", async () => {
  const root = await makeRoot();
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const create = (parent: string) => createFile(new Request("http://localhost/api/files", { method: "POST", body: JSON.stringify({ parent, scenario_name: "Buy" }) }));
    expect((await create("Alpha/Checkout")).status).toBe(201);
    expect((await renameFolder(new Request("http://localhost", { method: "PATCH", body: JSON.stringify({ name: "Basket" }) }), { params: Promise.resolve({ path: ["Alpha", "Checkout"] }) })).status).toBe(200);
    expect((await create("Alpha/Basket")).status).toBe(201);
    await expect(readFile(join(root, "Alpha", "Basket", "Checkout_1.feature"), "utf8")).resolves.toContain("Scenario: Buy");
    await expect(readFile(join(root, "Alpha", "Basket", "Basket_1.feature"), "utf8")).resolves.toContain("Scenario: Buy");
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});
