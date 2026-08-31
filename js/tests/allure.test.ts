import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, expect, it } from "vitest";
import { parseAllureReport } from "../src/lib/allure";
import { POST as preview } from "../app/api/runs/import/preview/route";
import { POST as commit } from "../app/api/runs/import/route";
import { POST as createGroup } from "../app/api/runs/[project]/groups/route";

const roots: string[] = [];
afterEach(async () => { await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true }))); });
const encoded = (value: unknown) => Buffer.from(JSON.stringify(value), "utf8").toString("base64");
const report = (scenarios: unknown[], summary: unknown = { reportName: "Nightly", time: { start: 1_700_000_000_000 } }) => `<!doctype html><script>d('data/suites.json','${encoded({ children: [{ children: scenarios }] })}');d('widgets/summary.json','${encoded(summary)}');</script>`;
const leaf = (name: string, status: string, stop: number) => ({ name, status, time: { start: stop - 100, stop } });
const feature = (name: string) => `Feature: ${name}\n\nScenario: ${name}\n  Given a step\n`;

it("parses nested suites, maps statuses, and collapses retries", () => {
  const parsed = parseAllureReport(report([leaf("Buy", "failed", 2), leaf("Buy", "passed", 3), leaf("Ship", "unknown", 4)]));
  expect(parsed).toEqual({ report_name: "Nightly", created_at: "2023-11-14T22:13:20+00:00", scenarios: [{ name: "Buy", result: "PASSED" }, { name: "Ship", result: "SKIPPED" }] });
});

it("previews and commits only fully-resolved report scenarios", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-allure-")); roots.push(root);
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await writeFile(join(root, "Alpha", "enums.yaml"), "components:\n");
  await writeFile(join(root, "Alpha", "Checkout", "buy.feature"), feature("Buy"));
  await writeFile(join(root, "Alpha", "Checkout", "ship.feature"), feature("Ship"));
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const html = report([leaf("Buy", "passed", 3), leaf("Missing", "failed", 4)]);
    const inspected = await preview(new Request("http://localhost/api/runs/import/preview", { method: "POST", body: JSON.stringify({ project: "Alpha", html }) }));
    expect(inspected.status).toBe(200); expect(await inspected.json()).toMatchObject({ counts: { total: 2, matched: 1, unmatched: 1 }, errors: ["2.Missing : cannot import - no case in project 'Alpha' has this scenario name"] });
    expect((await commit(new Request("http://localhost/api/runs/import", { method: "POST", body: JSON.stringify({ project: "Alpha", group: "smoke", name: "Nightly", file_name: "nightly", html }) }))).status).toBe(422);
    const group = await createGroup(new Request("http://localhost", { method: "POST", body: JSON.stringify({ name: "smoke" }) }), { params: Promise.resolve({ project: "Alpha" }) }); expect(group.status).toBe(201);
    const successHtml = report([leaf("Buy", "broken", 5), leaf("Ship", "skipped", 6)]);
    const response = await commit(new Request("http://localhost/api/runs/import", { method: "POST", body: JSON.stringify({ project: "Alpha", group: "smoke", name: "Nightly", file_name: "nightly", html: successHtml }) }));
    expect(response.status).toBe(201);
    await expect(readFile(join(root, "Alpha", "test-run", "smoke", "nightly.yaml"), "utf8")).resolves.toContain("created_at: 2023-11-14T22:13:20+00:00");
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});
