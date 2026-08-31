import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { GET, POST } from "../app/ui/[...path]/route";

const roots: string[] = [];
async function makeRoot() {
  const root = await mkdtemp(join(tmpdir(), "tms-ui-route-"));
  roots.push(root);
  return root;
}

afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true })));
  delete process.env.TMS_DATA_ROOT;
});

function request(path: string, headers?: HeadersInit) {
  const [pathname] = path.split("?");
  return GET(new Request(`http://localhost/ui/${path}`, { headers }), { params: Promise.resolve({ path: pathname.split("/") }) });
}

describe("legacy /ui compatibility adapter", () => {
  it("renders tree, folder, file, and search fragments as HTML", async () => {
    const root = await makeRoot();
    await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
    await writeFile(join(root, "Alpha", "Checkout", "case.feature"), "Feature: Checkout\n\nScenario: Buy\n  Given a cart\n");
    process.env.TMS_DATA_ROOT = root;

    const tree = await request("tree");
    expect(tree.status).toBe(200);
    expect(tree.headers.get("content-type")).toBe("text/html; charset=utf-8");
    await expect(tree.text()).resolves.toContain("Alpha");

    const folder = await request("folder/Alpha/Checkout");
    await expect(folder.text()).resolves.toContain("case.feature");
    const file = await request("file/Alpha/Checkout/case.feature");
    await expect(file.text()).resolves.toContain("&quot;scenario&quot;");
    const search = await request("search?q=Buy");
    await expect(search.text()).resolves.toContain("case.feature");
  });

  it("keeps UI parse failures as HTML 500 responses", async () => {
    const root = await makeRoot();
    await mkdir(join(root, "Alpha", "Checkout"), { recursive: true });
    await writeFile(join(root, "Alpha", "Checkout", "broken.feature"), "not valid gherkin\n");
    process.env.TMS_DATA_ROOT = root;
    const response = await request("file/Alpha/Checkout/broken.feature");
    expect(response.status).toBe(500);
    expect(response.headers.get("content-type")).toBe("text/html; charset=utf-8");
    await expect(response.text()).resolves.toContain("An unexpected error occurred.");
  });

  it("bridges browser navigation to the real shell with view state", async () => {
    const response = await GET(new Request("http://localhost/ui/file/Alpha/Checkout/case.feature", { headers: { "Sec-Fetch-Mode": "navigate" } }), { params: Promise.resolve({ path: ["file", "Alpha", "Checkout", "case.feature"] }) });
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("text/html; charset=utf-8");
    const body = await response.text();
    expect(body).toContain("Opening workspace");
    expect(body).toContain("/?tab=directory&path=Alpha%2FCheckout%2Fcase.feature");
  });

  it("uses the framework-style HTML response for unsupported methods", async () => {
    const response = await POST();
    expect(response.status).toBe(405);
    expect(response.headers.get("content-type")).toBe("text/html; charset=utf-8");
  });
});
