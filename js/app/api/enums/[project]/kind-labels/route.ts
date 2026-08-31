import { unlink } from "node:fs/promises";
import { resolve } from "node:path";
import { NextResponse } from "next/server";
import { stringify } from "yaml";
import { atomicWriteUtf8 } from "../../../../../src/lib/atomic-write";
import { readProjectEnums } from "../../../../../src/lib/enums";
import { resolveDataRoot } from "../../../../../src/lib/data-root";
import { PathValidationError, validateLogicalSegments } from "../../../../../src/lib/path";
import { defaultMethodNotAllowed } from "../../../../../src/lib/http-errors";

export async function PUT(request: Request, context: { params: Promise<{ project: string }> }) {
  const project = (await context.params).project;
  try {
    validateLogicalSegments([project]);
    const root = resolveDataRoot();
    const vocabulary = await readProjectEnums(resolve(root, project, "enums.yaml"));
    const labels = await request.json() as Record<string, unknown>;
    if (typeof labels !== "object" || labels === null || Array.isArray(labels) || Object.keys(labels).some((kind) => !(kind in vocabulary))) throw new Error("Kind labels must contain exactly the current kinds.");
    const stored: Record<string, string> = {};
    for (const kind of Object.keys(vocabulary)) { const label = labels[kind]; if (typeof label !== "string" || !label.trim() || /[\r\n]/.test(label)) throw new Error("Kind label must be a non-empty single-line string."); if (label !== kind) stored[kind] = label; }
    const target = resolve(root, project, "enum-kind-labels.yaml");
    if (Object.keys(stored).length) await atomicWriteUtf8(target, stringify(stored)); else await unlink(target).catch(() => undefined);
    return NextResponse.json(Object.fromEntries(Object.keys(vocabulary).map((kind) => [kind, stored[kind] ?? kind])));
  } catch (error: unknown) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    if (error instanceof PathValidationError || error instanceof SyntaxError) return NextResponse.json({ error: { code: "bad_request", message: "Invalid request body." } }, { status: 400 });
    return NextResponse.json({ error: { code: "validation_error", message: (error as Error).message, details: { field: "kind_labels" } } }, { status: 422 });
  }
}

export const GET = defaultMethodNotAllowed;
export const POST = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
