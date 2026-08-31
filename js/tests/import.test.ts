import { mkdir, mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, expect, it, vi } from "vitest";
import { POST as commit } from "../app/api/files/import/route";
import { POST as preview } from "../app/api/files/import/preview/route";
import * as atomic from "../src/lib/atomic-write";

const roots: string[] = [];
afterEach(async () => { await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true }))); });
const source = (first: string, second?: string) => `Feature: Batch\n\n  Scenario: ${first}\n    Given a step\n${second ? `\n  Scenario: ${second}\n    Given another step\n` : ""}`;

it("previews multiple sources in source/scenario order and commits generated names", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-import-")); roots.push(root); await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  const body = { parent: "Alpha/Checkout", sources: [{ name: "one.feature", source: source("One", "Two") }, { name: "two.feature", source: source("Three") }], names: ["Checkout_1.feature", "Checkout_2.feature", "Checkout_3.feature"] };
  try {
    const inspected = await preview(new Request("http://localhost/api/files/import/preview", { method: "POST", body: JSON.stringify(body) }));
    expect(inspected.status).toBe(200); expect((await inspected.json()).scenarios.map((item: { scenario_name: string }) => item.scenario_name)).toEqual(["One", "Two", "Three"]);
    const response = await commit(new Request("http://localhost/api/files/import", { method: "POST", body: JSON.stringify(body) }));
    expect(response.status).toBe(201); expect((await response.json()).created).toEqual(["Alpha/Checkout/Checkout_1.feature", "Alpha/Checkout/Checkout_2.feature", "Alpha/Checkout/Checkout_3.feature"]);
    await expect(readFile(join(root, "Alpha", "Checkout", "Checkout_2.feature"), "utf8")).resolves.toContain("Scenario: Two");
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("rejects a batch over twenty sources before writing", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-import-limit-")); roots.push(root); await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try { const response = await commit(new Request("http://localhost", { method: "POST", body: JSON.stringify({ parent: "Alpha/Checkout", sources: Array.from({ length: 21 }, (_, index) => ({ name: `${index}.feature`, source: source(String(index)) })) }) })); expect(response.status).toBe(400); expect(await readdir(join(root, "Alpha", "Checkout"))).toEqual([]); }
  finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("collects malformed and unsupported sources during preview", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-import-errors-")); roots.push(root); await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await preview(new Request("http://localhost/api/files/import/preview", { method: "POST", body: JSON.stringify({ parent: "Alpha/Checkout", sources: [{ name: "broken.feature", source: "Feature: Broken\n\nScenario: Bad\n  Given" }, { name: "notes.txt", source: "Feature: Notes" }] }) }));
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({ errors: [
      { source_index: 0, source_name: "broken.feature", code: "validation_error" },
      { source_index: 1, source_name: "notes.txt", code: "invalid_file_type" },
    ], scenarios: [] });
    expect(await readdir(join(root, "Alpha", "Checkout"))).toEqual([]);
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("validates the whole batch before committing any scenario", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-import-preflight-")); roots.push(root); await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await commit(new Request("http://localhost/api/files/import", { method: "POST", body: JSON.stringify({ parent: "Alpha/Checkout", sources: [{ name: "good.feature", source: source("Good") }, { name: "bad.txt", source: source("Bad") }], names: ["good.feature", "bad.feature"] }) }));
    expect(response.status).toBe(422);
    expect(await readdir(join(root, "Alpha", "Checkout"))).toEqual([]);
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});

it("rolls back already-created files when a later atomic create fails", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-import-rollback-")); roots.push(root); await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  const original = atomic.atomicCreateUtf8;
  let calls = 0;
  vi.spyOn(atomic, "atomicCreateUtf8").mockImplementation(async (target, text) => { calls += 1; if (calls === 2) throw new Error("simulated write failure"); return original(target, text); });
  try {
    const response = await commit(new Request("http://localhost/api/files/import", { method: "POST", body: JSON.stringify({ parent: "Alpha/Checkout", sources: [{ name: "one.feature", source: source("One") }, { name: "two.feature", source: source("Two") }], names: ["one.feature", "two.feature"] }) }));
    expect(response.status).toBe(400);
    expect(await readdir(join(root, "Alpha", "Checkout"))).toEqual([]);
  } finally { vi.restoreAllMocks(); if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});
