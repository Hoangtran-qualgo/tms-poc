import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, expect, it } from "vitest";
import { atomicCreateUtf8, atomicWriteUtf8 } from "../src/lib/atomic-write";

const roots: string[] = [];
afterEach(async () => { await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true }))); });

it("replaces a UTF-8 file without leaving a temporary sibling", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-atomic-"));
  roots.push(root);
  const target = join(root, "case.feature");
  await writeFile(target, "before");
  await atomicWriteUtf8(target, "after");
  await expect(readFile(target, "utf8")).resolves.toBe("after");
});

it("creates exclusively and preserves an existing target", async () => {
  const root = await mkdtemp(join(tmpdir(), "tms-atomic-create-"));
  roots.push(root);
  const target = join(root, "case.feature");
  await atomicCreateUtf8(target, "first");
  await expect(atomicCreateUtf8(target, "second")).rejects.toMatchObject({ code: "EEXIST" });
  await expect(readFile(target, "utf8")).resolves.toBe("first");
});
