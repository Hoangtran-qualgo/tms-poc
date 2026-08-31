import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, expect, it } from "vitest";
import { GET } from "../app/api/search/route";

const roots: string[] = [];
afterEach(async () => { await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true }))); });

it("keeps search query options and file_path hit shape at the HTTP boundary", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-search-route-")); roots.push(root);
  await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
  await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "@Fast\nFeature: Checkout\n\n  @api\n  Scenario: Buy\n    Given a cart\n");
  const previous = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await GET(new Request("http://localhost/api/search?q=FAST&scope=module%3AAlpha%2FCheckout&match=tag&case=false"));
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ hits: [{ file_path: "Alpha/Checkout/case.feature", scenario_name: "Buy", description: "Checkout", matched_field: "tag", match_value: "Fast" }] });
  } finally { if (previous === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = previous; }
});
