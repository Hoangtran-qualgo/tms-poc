import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { GET } from "../app/api/files/[...path]/route";
import { PUT } from "../app/api/files/[...path]/route";
import { splitFeatureSource } from "../src/lib/feature";

const roots: string[] = [];

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "tms-raw-"));
  roots.push(root);
  return root;
}

afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, { force: true, recursive: true })));
});

describe("GET /api/files/<path>/raw", () => {
  it("returns malformed feature source as UTF-8 plain text", async () => {
    const root = await makeRoot();
    await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
    await writeFile(join(root, "Alpha", "Checkout", "broken.feature"), "this is not gherkin\n");

    const originalRoot = process.env.TMS_DATA_ROOT;
    process.env.TMS_DATA_ROOT = root;
    try {
      const response = await GET(new Request("http://localhost"), {
        params: Promise.resolve({ path: ["Alpha", "Checkout", "broken.feature", "raw"] }),
      });
      expect(response.status).toBe(200);
      expect(response.headers.get("content-type")).toBe("text/plain; charset=utf-8");
      await expect(response.text()).resolves.toBe("this is not gherkin\n");
    } finally {
      if (originalRoot === undefined) delete process.env.TMS_DATA_ROOT;
      else process.env.TMS_DATA_ROOT = originalRoot;
    }
  });

  it("returns the documented unsupported-type and missing-file responses", async () => {
    const root = await makeRoot();
    const originalRoot = process.env.TMS_DATA_ROOT;
    process.env.TMS_DATA_ROOT = root;
    try {
      const unsupported = await GET(new Request("http://localhost"), {
        params: Promise.resolve({ path: ["Alpha", "case.yaml", "raw"] }),
      });
      expect(unsupported.status).toBe(415);
      await expect(unsupported.json()).resolves.toMatchObject({ error: { code: "unsupported_type" } });

      const missing = await GET(new Request("http://localhost"), {
        params: Promise.resolve({ path: ["Alpha", "case.feature", "raw"] }),
      });
      expect(missing.status).toBe(404);
      await expect(missing.json()).resolves.toMatchObject({ error: { code: "not_found" } });
    } finally {
      if (originalRoot === undefined) delete process.env.TMS_DATA_ROOT;
      else process.env.TMS_DATA_ROOT = originalRoot;
    }
  });
});

describe("GET /api/files/<path>", () => {
  it("returns the editor feature payload and maps malformed Gherkin to 422", async () => {
    const root = await makeRoot();
    await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
    await writeFile(
      join(root, "Alpha", "Checkout", "case.feature"),
      "# enum.priority: p1\n@feature\nFeature: Checkout\\nDetail\n\n  Background:\n    Given a cart\n\n  @scenario\n  Scenario: Buy\n    When paying\n",
    );
    await writeFile(join(root, "Alpha", "Checkout", "broken.feature"), "not valid gherkin");

    const originalRoot = process.env.TMS_DATA_ROOT;
    process.env.TMS_DATA_ROOT = root;
    try {
      const success = await GET(new Request("http://localhost"), {
        params: Promise.resolve({ path: ["Alpha", "Checkout", "case.feature"] }),
      });
      expect(success.status).toBe(200);
      await expect(success.json()).resolves.toMatchObject({
        description: "Checkout\nDetail",
        tags: ["feature"],
        background: { steps: [{ keyword: "Given", text: "a cart" }] },
        scenario: { kind: "scenario", name: "Buy", tags: ["scenario"] },
        enums: { priority: "p1" },
      });

      const malformed = await GET(new Request("http://localhost"), {
        params: Promise.resolve({ path: ["Alpha", "Checkout", "broken.feature"] }),
      });
      expect(malformed.status).toBe(422);
      await expect(malformed.json()).resolves.toMatchObject({ error: { code: "parse_error" } });
    } finally {
      if (originalRoot === undefined) delete process.env.TMS_DATA_ROOT;
      else process.env.TMS_DATA_ROOT = originalRoot;
    }
  });
});

it("raw PUT normalizes line endings without canonicalizing source", async () => {
  const root = await makeRoot();
  const folder = join(root, "Alpha", "Checkout");
  await mkdir(folder, { recursive: true });
  await writeFile(join(folder, "case.feature"), "Feature: old\n\n  Scenario: Old\n    Given old\n");
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await PUT(new Request("http://localhost", { method: "PUT", body: "Feature: New\r\n\r\n  Scenario: New\r\n    Given   spaced\r\n" }), { params: Promise.resolve({ path: ["Alpha", "Checkout", "case.feature", "raw"] }) });
    expect(response.status).toBe(200);
    await expect(readFile(join(folder, "case.feature"), "utf8")).resolves.toBe("Feature: New\n\n  Scenario: New\n    Given   spaced\n");
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("splits multiple scenarios while retaining shared feature metadata", () => {
  const cases = splitFeatureSource("@feature\nFeature: Checkout\n\n  Background:\n    Given a cart\n\n  @one\n  Scenario: Buy\n    When paying\n\n  @two\n  Scenario: Cancel\n    When cancelling\n");
  expect(cases.map((item) => item.scenario.name)).toEqual(["Buy", "Cancel"]);
  expect(cases[0].background.steps[0].text).toBe("a cart");
  expect(cases.every((item) => item.enums && Object.keys(item.enums).length === 0)).toBe(true);
});
