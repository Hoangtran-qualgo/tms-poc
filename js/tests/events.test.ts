import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, expect, it } from "vitest";
import { GET } from "../app/api/events/route";
import { publishChange } from "../src/lib/events";

const roots: string[] = [];
afterEach(async () => { await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true }))); });

it("opens the SSE stream with the connected marker and change event", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-events-")); roots.push(root); await mkdir(root, { recursive: true });
  const before = process.env.TMS_DATA_ROOT; process.env.TMS_DATA_ROOT = root;
  try {
    const response = await GET();
    expect(response.headers.get("content-type")).toContain("text/event-stream");
    const reader = response.body!.getReader();
    expect(new TextDecoder().decode((await reader.read()).value)).toContain(": connected");
    publishChange();
    expect(new TextDecoder().decode((await reader.read()).value)).toContain("event: change");
    await reader.cancel();
  } finally { if (before === undefined) delete process.env.TMS_DATA_ROOT; else process.env.TMS_DATA_ROOT = before; }
});
