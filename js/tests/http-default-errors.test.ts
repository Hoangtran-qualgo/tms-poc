import { describe, expect, it } from "vitest";

import { GET as foldersGet } from "../app/api/folders/[...path]/route";
import { POST as treePost } from "../app/api/tree/route";

describe("framework-default HTTP errors", () => {
  it("returns an HTML 405 for an unsupported method on a known API route", async () => {
    const response = await treePost();
    expect(response.status).toBe(405);
    expect(response.headers.get("content-type")).toBe("text/html; charset=utf-8");
    const body = await response.text();
    expect(body).toContain("<title>405 Method Not Allowed</title>");
    expect(body).not.toContain("\"error\"");
  });

  it("returns an HTML 404 for a non-public folder catch-all path", async () => {
    const response = await foldersGet(new Request("http://localhost/api/folders/Alpha"), { params: Promise.resolve({ path: ["Alpha"] }) });
    expect(response.status).toBe(404);
    expect(response.headers.get("content-type")).toBe("text/html; charset=utf-8");
    expect(await response.text()).toContain("<title>404 Not Found</title>");
  });
});
