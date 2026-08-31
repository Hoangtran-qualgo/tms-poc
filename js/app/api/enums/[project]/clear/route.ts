import { readdir, unlink } from "node:fs/promises";
import { relative, resolve } from "node:path";
import { NextResponse } from "next/server";
import { atomicWriteUtf8 } from "../../../../../src/lib/atomic-write";
import { EnumInUseError, readProjectEnums } from "../../../../../src/lib/enums";
import { parseFeature } from "../../../../../src/lib/feature";
import { resolveDataRoot } from "../../../../../src/lib/data-root";
import { PathValidationError, validateLogicalSegments } from "../../../../../src/lib/path";
import { readUtf8File } from "../../../../../src/lib/utf8";
import { defaultMethodNotAllowed } from "../../../../../src/lib/http-errors";

async function featureFiles(directory: string): Promise<string[]> {
  const found: string[] = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) found.push(...await featureFiles(path));
    else if (entry.isFile() && entry.name.toLowerCase().endsWith(".feature")) found.push(path);
  }
  return found;
}

export async function POST(_request: Request, context: { params: Promise<{ project: string }> }) {
  const project = (await context.params).project;
  try {
    validateLogicalSegments([project]);
    const projectDirectory = resolve(resolveDataRoot(), project);
    const target = resolve(projectDirectory, "enums.yaml");
    const vocabulary = await readProjectEnums(target);
    for (const [kind, entries] of Object.entries(vocabulary)) {
      for (const key of Object.keys(entries)) {
        let count = 0;
        const sample: string[] = [];
        for (const path of await featureFiles(projectDirectory)) {
          const feature = parseFeature(await readUtf8File(path));
          if (feature.enums[kind] !== key) continue;
          count += 1;
          if (sample.length < 5) sample.push(relative(resolveDataRoot(), path).split("\\").join("/"));
        }
        if (count) throw new EnumInUseError(kind, key, count, sample, `Cannot clear: enum ${kind}: ${key} is in use by test case ${sample[0]}${count > 1 ? ` (and ${count - 1} more)` : ""} — please clear that enum in the test case first.`);
      }
    }
    await atomicWriteUtf8(target, "components:\n");
    await unlink(resolve(projectDirectory, "enum-kind-labels.yaml")).catch((error: unknown) => {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    });
    return NextResponse.json({ cleared: true });
  } catch (error: unknown) {
    if (error instanceof EnumInUseError) return NextResponse.json({ error: { code: "enum_in_use", message: error.message, details: { kind: error.kind, key: error.key, count: error.count, sample: error.sample } } }, { status: 409 });
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    if (error instanceof PathValidationError) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    if (error instanceof Error && "line" in error && "column" in error) return NextResponse.json({ error: { code: "parse_error", message: error.message, details: { line: (error as { line: number }).line, column: (error as { column: number }).column } } }, { status: 422 });
    console.error("Unexpected error in API handler", error);
    return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
  }
}

export const GET = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
