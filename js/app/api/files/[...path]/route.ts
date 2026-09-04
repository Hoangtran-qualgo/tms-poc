import { stat } from "node:fs/promises";
import { resolve } from "node:path";

import { NextResponse } from "next/server";

import { resolveDataRoot } from "../../../../src/lib/data-root";
import { FeatureValidationError, GherkinParseError, parseFeature, serializeFeature, validateEnumReferences, validateFeature, type FeaturePayload } from "../../../../src/lib/feature";
import { readProjectEnums } from "../../../../src/lib/enums";
import { atomicWriteUtf8 } from "../../../../src/lib/atomic-write";
import { PathValidationError, validateLogicalSegments } from "../../../../src/lib/path";
import { readUtf8File } from "../../../../src/lib/utf8";
import { deleteFeature, duplicateFeature, moveFeature, MutationConflictError, renameFeature } from "../../../../src/lib/relocate";
import { defaultMethodNotAllowed } from "../../../../src/lib/http-errors";

export const runtime = "nodejs";

function unsupported(path: string) {
  return NextResponse.json(
    { error: { code: "unsupported_type", message: "File type not supported", details: { path } } },
    { status: 415 },
  );
}

export async function GET(_request: Request, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path;
  const raw = path.at(-1) === "raw";
  const fileSegments = raw ? path.slice(0, -1) : path;
  const filePath = fileSegments.join("/");
  if (!filePath.toLowerCase().endsWith(".feature")) return unsupported(filePath);

  try {
    validateLogicalSegments(fileSegments);
    const target = resolve(resolveDataRoot(), ...fileSegments);
    if (!(await stat(target)).isFile()) {
      return NextResponse.json({ error: { code: "not_found", message: `File not found: ${target}` } }, { status: 404 });
    }
    const source = await readUtf8File(target);
    return raw
      ? new Response(source, { headers: { "content-type": "text/plain; charset=utf-8" } })
      : NextResponse.json(parseFeature(source));
  } catch (error: unknown) {
    if (error instanceof PathValidationError) {
      return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    }
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    }
    if (error instanceof GherkinParseError) {
      return NextResponse.json(
        { error: { code: "parse_error", message: error.message, details: { line: error.line, column: error.column } } },
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

export async function PATCH(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path;
  if (path.at(-1) === "rename" || path.at(-1) === "move") {
    try {
      const body = await request.json() as { file_name?: unknown; parent?: unknown };
      if (path.at(-1) === "rename") {
        if (typeof body.file_name !== "string" || !body.file_name) return NextResponse.json({ error: { code: "bad_request", message: "Body field 'file_name' must be a non-empty string." } }, { status: 400 });
        await renameFeature(path.slice(0, -1), body.file_name);
      } else {
        if (typeof body.parent !== "string") return NextResponse.json({ error: { code: "bad_request", message: "Body field 'parent' must be a string." } }, { status: 400 });
        await moveFeature(path.slice(0, -1), body.parent.split("/").filter(Boolean));
      }
      return NextResponse.json({ ok: true });
    } catch (error: unknown) {
      if (error instanceof MutationConflictError) return NextResponse.json({ error: { code: "name_conflict", message: error.message } }, { status: 409 });
      if (error instanceof PathValidationError) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
      if ((error as NodeJS.ErrnoException).code === "ENOENT" || /not found/i.test((error as Error).message ?? "")) return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
      if ((error as Error).message) return NextResponse.json({ error: { code: "bad_request", message: (error as Error).message } }, { status: 400 });
      return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
    }
  }
  if (path.at(-1) === "raw" || !path.at(-1)?.toLowerCase().endsWith(".feature")) return unsupported(path.join("/"));
  try {
    validateLogicalSegments(path);
    const root = resolveDataRoot();
    const target = resolve(root, ...path);
    if (!(await stat(target)).isFile()) return NextResponse.json({ error: { code: "not_found", message: `File not found: ${target}` } }, { status: 404 });
    const feature = await request.json() as FeaturePayload;
    validateFeature(feature);
    try { validateEnumReferences(feature, await readProjectEnums(resolve(root, path[0], "enums.yaml"))); } catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
    await atomicWriteUtf8(target, serializeFeature(feature));
    return NextResponse.json({ ok: true });
  } catch (error: unknown) {
    if (error instanceof FeatureValidationError) return NextResponse.json({ error: { code: "validation_error", message: error.message, details: { field: error.field } } }, { status: 422 });
    if (error instanceof PathValidationError || error instanceof SyntaxError) return NextResponse.json({ error: { code: "bad_request", message: "Request body must be a JSON object." } }, { status: 400 });
    if (error instanceof GherkinParseError) return NextResponse.json({ error: { code: "parse_error", message: error.message, details: { line: error.line, column: error.column } } }, { status: 422 });
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    console.error("Unexpected error in API handler", error);
    return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
  }
}

export async function POST(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path;
  if (path.at(-1) !== "duplicate") return unsupported(path.join("/"));
  try {
    const body = await request.json() as { file_name?: unknown };
    if (body.file_name !== undefined && (typeof body.file_name !== "string" || !body.file_name)) return NextResponse.json({ error: { code: "bad_request", message: "Body field 'file_name' must be a non-empty string." } }, { status: 400 });
    const fileName = await duplicateFeature(path.slice(0, -1), body.file_name);
    return NextResponse.json(body.file_name === undefined ? { ok: true, file_name: fileName } : { ok: true }, { status: 201 });
  } catch (error: unknown) {
    if (error instanceof MutationConflictError) return NextResponse.json({ error: { code: "name_conflict", message: error.message } }, { status: 409 });
    if (error instanceof PathValidationError) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    if ((error as NodeJS.ErrnoException).code === "ENOENT" || /not found/i.test((error as Error).message ?? "")) return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    return NextResponse.json({ error: { code: "bad_request", message: (error as Error).message } }, { status: 400 });
  }
}

export async function DELETE(_request: Request, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path;
  try {
    if (!path.at(-1)?.toLowerCase().endsWith(".feature")) return unsupported(path.join("/"));
    await deleteFeature(path);
    return new Response(null, { status: 204 });
  } catch (error: unknown) {
    if (error instanceof MutationConflictError) return NextResponse.json({ error: { code: "name_conflict", message: error.message } }, { status: 409 });
    if (error instanceof PathValidationError) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    if ((error as Error).message?.startsWith("Target is a directory")) return NextResponse.json({ error: { code: "bad_request", message: (error as Error).message } }, { status: 400 });
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return new Response(null, { status: 204 });
    return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
  }
}

export async function PUT(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path;
  if (path.at(-1) !== "raw") return unsupported(path.join("/"));
  const filePath = path.slice(0, -1);
  if (!filePath.at(-1)?.toLowerCase().endsWith(".feature")) return unsupported(filePath.join("/"));
  try {
    validateLogicalSegments(filePath);
    const root = resolveDataRoot();
    const target = resolve(root, ...filePath);
    if (!(await stat(target)).isFile()) return NextResponse.json({ error: { code: "not_found", message: `File not found: ${target}` } }, { status: 404 });
    const source = (await request.text()).replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    const feature = parseFeature(source);
    try { validateEnumReferences(feature, await readProjectEnums(resolve(root, filePath[0], "enums.yaml"))); } catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
    await atomicWriteUtf8(target, source);
    return NextResponse.json({ ok: true });
  } catch (error: unknown) {
    if (error instanceof GherkinParseError) return NextResponse.json({ error: { code: "parse_error", message: error.message, details: { line: error.line, column: error.column } } }, { status: 422 });
    if (error instanceof FeatureValidationError) return NextResponse.json({ error: { code: "validation_error", message: error.message, details: { field: error.field } } }, { status: 422 });
    if (error instanceof PathValidationError) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    console.error("Unexpected error in API handler", error);
    return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
  }
}
