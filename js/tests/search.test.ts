import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { searchFeatures } from "../src/lib/search";

const roots: string[] = [];
async function makeRoot() { const root = await mkdtemp(join(tmpdir(), "tms-search-")); roots.push(root); return root; }
afterEach(async () => { await Promise.all(roots.splice(0).map((root) => rm(root, { force: true, recursive: true }))); });

describe("searchFeatures", () => {
  it("matches text and de-duplicated tags while skipping malformed sources", async () => {
    const root = await makeRoot();
    const folder = join(root, "Alpha", "Module");
    await mkdir(folder, { recursive: true });
    await writeFile(join(folder, "case.feature"), "@Fast\nFeature: Checkout Needle\n\n  @fast @api\n  Scenario: Buy\n    Given a cart\n");
    await writeFile(join(folder, "broken.feature"), "not valid gherkin");
    await expect(searchFeatures(root, "needle")).resolves.toEqual([
      { file_path: "Alpha/Module/case.feature", description: "Checkout Needle", scenario_name: "Buy", matched_field: "description", match_value: "needle" },
    ]);
    await expect(searchFeatures(root, "fast", "module:Alpha/Module", "tag")).resolves.toEqual([
      { file_path: "Alpha/Module/case.feature", description: "Checkout Needle", scenario_name: "Buy", matched_field: "tag", match_value: "Fast" },
      { file_path: "Alpha/Module/case.feature", description: "Checkout Needle", scenario_name: "Buy", matched_field: "tag", match_value: "fast" },
    ]);
    await expect(searchFeatures(root, "FAST", "all", "tag", true)).resolves.toEqual([]);
  });
});
