import { NextResponse } from "next/server";
import { relative, resolve } from "node:path";

import { EnumInUseError, EnumsParseError, readProjectEnums, serializeEnumVocabulary } from "../../../../src/lib/enums";
import { atomicCreateUtf8, atomicWriteUtf8 } from "../../../../src/lib/atomic-write";
import { resolveDataRoot } from "../../../../src/lib/data-root";
import { parseFeature } from "../../../../src/lib/feature";
import { PathValidationError, validateLogicalSegments } from "../../../../src/lib/path";
import { readUtf8File } from "../../../../src/lib/utf8";
import { readdir } from "node:fs/promises";
import { defaultMethodNotAllowed } from "../../../../src/lib/http-errors";

export const runtime = "nodejs";

async function featureFiles(directory: string): Promise<string[]> {
  const found: string[] = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) found.push(...await featureFiles(path));
    else if (entry.isFile() && entry.name.toLowerCase().endsWith(".feature")) found.push(path);
  }
  return found;
}

async function assertNoInUseRemovals(projectDirectory: string, current: Record<string, Record<string, string>>, next: Record<string, Record<string, string>>) {
  const removed = new Set(Object.entries(current).flatMap(([kind, entries]) => Object.keys(entries).filter((key) => next[kind]?.[key] === undefined).map((key) => `${kind}\u0000${key}`)));
  if (!removed.size) return;
  const usages = new Map<string, { count: number; sample: string[] }>();
  for (const path of await featureFiles(projectDirectory)) {
    const feature = parseFeature(await readUtf8File(path));
    for (const [kind, key] of Object.entries(feature.enums)) {
      const id = `${kind}\u0000${key}`;
      if (!removed.has(id)) continue;
      const usage = usages.get(id) ?? { count: 0, sample: [] };
      usage.count += 1;
      if (usage.sample.length < 5) usage.sample.push(relative(resolveDataRoot(), path).split("\\").join("/"));
      usages.set(id, usage);
    }
  }
  for (const id of removed) {
    const usage = usages.get(id);
    if (!usage?.count) continue;
    const [kind, key] = id.split("\u0000");
    throw new EnumInUseError(kind, key, usage.count, usage.sample, `enum ${kind}: ${key} is in use by test case ${usage.sample[0]}${usage.count > 1 ? ` (and ${usage.count - 1} more)` : ""} — please clear that enum in the test case first.`);
  }
}

export async function GET(_request: Request, context: { params: Promise<{ project: string }> }) {
  const project = (await context.params).project;
  try {
    validateLogicalSegments([project]);
    return NextResponse.json(await readProjectEnums(resolve(resolveDataRoot(), project, "enums.yaml")));
  } catch (error: unknown) {
    if (error instanceof PathValidationError) {
      return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    }
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return NextResponse.json(
        { error: { code: "not_found", message: (error as Error).message } },
        { status: 404 },
      );
    }
    if (error instanceof EnumsParseError) {
      return NextResponse.json(
        {
          error: {
            code: "enums_parse_error",
            message: error.message,
            details: { line: error.line, column: error.column },
          },
        },
        { status: 422 },
      );
    }
    console.error("Unexpected error in API handler", error);
    return NextResponse.json(
      { error: { code: "internal_error", message: "An unexpected error occurred." } },
      { status: 500 },
    );
  }
}

export async function PUT(request: Request, context: { params: Promise<{ project: string }> }) {
  const project = (await context.params).project;
  try {
    validateLogicalSegments([project]);
    const root = resolveDataRoot();
    const target = resolve(root, project, "enums.yaml");
    const current = await readProjectEnums(target);
    const next = await request.json() as unknown;
    if (typeof next !== "object" || next === null || Array.isArray(next)) throw new EnumsParseError("enums.yaml root must be a YAML mapping; got object.");
    let serialized: string;
    try {
      serialized = serializeEnumVocabulary(next as Record<string, Record<string, string>>);
    } catch (error) {
      if (error instanceof EnumsParseError) throw error;
      throw new EnumsParseError((error as Error).message || "Invalid enum vocabulary.");
    }
    await assertNoInUseRemovals(resolve(root, project), current, next as Record<string, Record<string, string>>);
    await atomicWriteUtf8(target, serialized);
    return NextResponse.json(next);
  } catch (error: unknown) {
    if (error instanceof EnumInUseError) return NextResponse.json({ error: { code: "enum_in_use", message: error.message, details: { kind: error.kind, key: error.key, count: error.count, sample: error.sample } } }, { status: 409 });
    if (error instanceof EnumsParseError) return NextResponse.json({ error: { code: "enums_parse_error", message: error.message, details: { line: error.line, column: error.column } } }, { status: 422 });
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    if (error instanceof PathValidationError || error instanceof SyntaxError) return NextResponse.json({ error: { code: "bad_request", message: "Request body must be a JSON object." } }, { status: 400 });
    console.error("Unexpected error in API handler", error);
    return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
  }
}

export async function POST(_request: Request, context: { params: Promise<{ project: string }> }) {
  const project = (await context.params).project;
  try {
    validateLogicalSegments([project]);
    const projectDirectory = resolve(resolveDataRoot(), project);
    const target = resolve(projectDirectory, "enums.yaml");
    await atomicCreateUtf8(target, "components:\n");
    return NextResponse.json({ components: {} }, { status: 201 });
  } catch (error: unknown) {
    if ((error as NodeJS.ErrnoException).code === "EEXIST") return NextResponse.json({ error: { code: "name_conflict", message: "A file named 'enums.yaml' already exists." } }, { status: 409 });
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    if (error instanceof PathValidationError) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    console.error("Unexpected error in API handler", error);
    return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
  }
}

export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
