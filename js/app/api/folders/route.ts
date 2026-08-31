import { mkdir, stat, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { NextResponse } from "next/server";
import { resolveDataRoot } from "../../../src/lib/data-root";
import { PathValidationError, validateLogicalSegments } from "../../../src/lib/path";
import { defaultMethodNotAllowed } from "../../../src/lib/http-errors";

const MAX_FOLDER_DEPTH = 10;
const RESERVED = new Set(["test-run", "report"]);

function error(code: string, message: string, status: number, details?: object) {
  return NextResponse.json({ error: { code, message, ...(details ? { details } : {}) } }, { status });
}

export async function POST(request: Request) {
  try {
    const body: unknown = await request.json();
    if (typeof body !== "object" || body === null || Array.isArray(body)) throw new PathValidationError("Request body must be a JSON object.");
    const { parent = "", name } = body as { parent?: unknown; name?: unknown };
    if (typeof parent !== "string") throw new PathValidationError("Body field 'parent' must be a string.");
    if (typeof name !== "string" || !name) throw new PathValidationError("Body field 'name' must be a non-empty string.");
    const segments = [...parent.split("/").filter(Boolean), name];
    validateLogicalSegments(segments);
    if (segments.length > MAX_FOLDER_DEPTH) throw new PathValidationError(`create_folder only supports paths up to depth ${MAX_FOLDER_DEPTH}; got depth ${segments.length}.`);
    if (segments.length >= 2 && RESERVED.has(segments[1])) {
      return error("name_conflict", `'${segments[1]}' is a reserved typed area under '${segments[0]}'; writes must go through the dedicated API (e.g. /api/runs).`, 409, { path: segments.join("/") });
    }
    const target = resolve(resolveDataRoot(), ...segments);
    if (segments.length >= 2) {
      try { if (!(await stat(resolve(resolveDataRoot(), ...segments.slice(0, -1)))).isDirectory()) return error("not_found", `Parent folder does not exist: '${segments.slice(0, -1).join("/")}'`, 404); }
      catch (cause: unknown) { if ((cause as NodeJS.ErrnoException).code === "ENOENT") return error("not_found", `Parent folder does not exist: '${segments.slice(0, -1).join("/")}'`, 404); throw cause; }
    }
    try { await mkdir(target); } catch (cause: unknown) {
      if ((cause as NodeJS.ErrnoException).code === "EEXIST") return error("name_conflict", `A folder named '${name}' already exists.`, 409, { path: segments.join("/") });
      throw cause;
    }
    if (segments.length === 1) await writeFile(resolve(target, "enums.yaml"), "components:\n", { encoding: "utf8", flag: "wx" });
    return NextResponse.json({ ok: true }, { status: 201 });
  } catch (cause: unknown) {
    if (cause instanceof PathValidationError || cause instanceof SyntaxError) return error("bad_request", cause instanceof SyntaxError ? "Request body must be a JSON object." : cause.message, 400);
    console.error("Unexpected error in API handler", cause);
    return error("internal_error", "An unexpected error occurred.", 500);
  }
}

export const GET = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
