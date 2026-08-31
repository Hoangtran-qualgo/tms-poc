import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { GET, POST as init, PUT } from "../app/api/enums/[project]/route";
import { POST as clear } from "../app/api/enums/[project]/clear/route";
import { POST as rename } from "../app/api/enums/[project]/rename/route";
import { EnumsParseError, parseEnumVocabulary } from "../src/lib/enums";

const roots: string[] = [];

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-enums-"));
  roots.push(root);
  return root;
}

afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, { force: true, recursive: true })));
});

describe("parseEnumVocabulary", () => {
  it("keeps YAML mapping order and normalizes an empty kind", () => {
    expect(parseEnumVocabulary("components:\npriority:\n  - p1: Priority 1\n")).toEqual({
      components: {},
      priority: { p1: "Priority 1" },
    });
  });

  it("rejects malformed YAML and schema-invalid values", () => {
    expect(() => parseEnumVocabulary("components: [unterminated\n")).toThrow(EnumsParseError);
    expect(() => parseEnumVocabulary("components:\n  - bad.key: Invalid\n")).toThrow(EnumsParseError);
  });
});

describe("GET /api/enums/<project>", () => {
  it("returns the parsed vocabulary and preserves an API parse error", async () => {
    const root = await makeRoot();
    await mkdir(join(root, "Alpha"));
    await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n  - login: Login\n");

    const originalRoot = process.env.TMS_DATA_ROOT;
    process.env.TMS_DATA_ROOT = root;
    try {
      const success = await GET(new Request("http://localhost/api/enums/Alpha"), {
        params: Promise.resolve({ project: "Alpha" }),
      });
      expect(success.status).toBe(200);
      await expect(success.json()).resolves.toEqual({ components: { login: "Login" } });

      await writeFile(join(root, "Alpha", "enums.yaml"), "components: [unterminated\n");
      const malformed = await GET(new Request("http://localhost/api/enums/Alpha"), {
        params: Promise.resolve({ project: "Alpha" }),
      });
      expect(malformed.status).toBe(422);
      await expect(malformed.json()).resolves.toMatchObject({
        error: { code: "enums_parse_error", details: { line: expect.any(Number), column: expect.any(Number) } },
      });
    } finally {
      if (originalRoot === undefined) delete process.env.TMS_DATA_ROOT;
      else process.env.TMS_DATA_ROOT = originalRoot;
    }
  });

  it("returns 404 when a legacy project has no enum file", async () => {
    const root = await makeRoot();
    await mkdir(join(root, "Legacy"));
    const originalRoot = process.env.TMS_DATA_ROOT;
    process.env.TMS_DATA_ROOT = root;
    try {
      const response = await GET(new Request("http://localhost/api/enums/Legacy"), {
        params: Promise.resolve({ project: "Legacy" }),
      });
      expect(response.status).toBe(404);
      await expect(response.json()).resolves.toMatchObject({ error: { code: "not_found" } });
    } finally {
      if (originalRoot === undefined) delete process.env.TMS_DATA_ROOT;
      else process.env.TMS_DATA_ROOT = originalRoot;
    }
  });
});

it("initializes a legacy project once and rejects a second initialization", async () => {
  const root = await makeRoot();
  await mkdir(join(root, "Legacy"));
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await init(new Request("http://localhost/api/enums/Legacy"), { params: Promise.resolve({ project: "Legacy" }) });
    expect(response.status).toBe(201);
    await expect(response.json()).resolves.toEqual({ components: {} });
    const conflict = await init(new Request("http://localhost/api/enums/Legacy"), { params: Promise.resolve({ project: "Legacy" }) });
    expect(conflict.status).toBe(409);
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("blocks removing an enum key while a feature still references it", async () => {
  const root = await makeRoot();
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n  - old: Old\n  - keep: Keep\n");
  await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "# enum.components: old\nFeature: Case\n\nScenario: Buy\n  Given a step\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await PUT(new Request("http://localhost/api/enums/Alpha", { method: "PUT", body: JSON.stringify({ components: { keep: "Keep" } }) }), { params: Promise.resolve({ project: "Alpha" }) });
    expect(response.status).toBe(409);
    await expect(response.json()).resolves.toMatchObject({ error: { code: "enum_in_use", details: { kind: "components", key: "old", count: 1 } } });
    await expect(readFile(join(root, "Alpha", "enums.yaml"), "utf8")).resolves.toContain("old: Old");
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("clears an unused vocabulary and removes display-label metadata", async () => {
  const root = await makeRoot();
  await mkdir(join(root, "Alpha"));
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n  - old: Old\n");
  await writeFile(join(root, "Alpha", "enum-kind-labels.yaml"), "components: Components\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await clear(new Request("http://localhost/api/enums/Alpha/clear"), { params: Promise.resolve({ project: "Alpha" }) });
    expect(response.status).toBe(200);
    await expect(readFile(join(root, "Alpha", "enums.yaml"), "utf8")).resolves.toBe("components:\n");
    await expect(readFile(join(root, "Alpha", "enum-kind-labels.yaml"), "utf8")).rejects.toMatchObject({ code: "ENOENT" });
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("renames only the selected enum key and cascades its feature references", async () => {
  const root = await makeRoot();
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n  - old: Old\n  - keep: Keep\nsprint:\n  - one: One\n");
  await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "# enum.components: old\n# enum.sprint: one\nFeature: Case\n\nScenario: Buy\n  Given a step\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await rename(new Request("http://localhost", { method: "POST", body: JSON.stringify({ kind: "components", old_key: "old", new_key: "new" }) }), { params: Promise.resolve({ project: "Alpha" }) });
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ renamed: 1 });
    await expect(readFile(join(root, "Alpha", "Checkout", "case.feature"), "utf8")).resolves.toContain("enum.components: new");
    await expect(readFile(join(root, "Alpha", "Checkout", "case.feature"), "utf8")).resolves.toContain("enum.sprint: one");
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});
