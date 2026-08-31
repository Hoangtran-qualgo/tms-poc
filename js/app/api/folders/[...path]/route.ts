import { NextResponse } from "next/server";

import { resolveDataRoot } from "../../../../src/lib/data-root";
import { FolderNotFoundError, FolderPathError, listFolder } from "../../../../src/lib/folder";
import { deleteFolder, MutationConflictError, renameFolder } from "../../../../src/lib/relocate";
import { PathValidationError } from "../../../../src/lib/path";
import { defaultNotFound, defaultMethodNotAllowed } from "../../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path;
  if (path.at(-1) !== "contents") return defaultNotFound();

  try {
    return NextResponse.json(await listFolder(resolveDataRoot(), path.slice(0, -1)));
  } catch (error) {
    if (error instanceof FolderPathError) {
      return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    }
    if (error instanceof FolderNotFoundError) {
      return NextResponse.json({ error: { code: "not_found", message: error.message } }, { status: 404 });
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
  try {
    if (path.at(-1) === "contents" || !path.length) return NextResponse.json({ error: { code: "bad_request", message: "A folder path is required." } }, { status: 400 });
    const body = await request.json() as { name?: unknown };
    if (typeof body?.name !== "string" || !body.name) return NextResponse.json({ error: { code: "bad_request", message: "Body field 'name' must be a non-empty string." } }, { status: 400 });
    await renameFolder(path, body.name);
    return NextResponse.json({ ok: true });
  } catch (error: unknown) {
    if (error instanceof MutationConflictError) return NextResponse.json({ error: { code: "name_conflict", message: error.message } }, { status: 409 });
    if (error instanceof PathValidationError) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    if ((error as NodeJS.ErrnoException).code === "ENOENT" || (error as Error).message?.startsWith("Folder not found")) return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    return NextResponse.json({ error: { code: "bad_request", message: (error as Error).message } }, { status: 400 });
  }
}

export async function DELETE(_request: Request, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path;
  try {
    if (path.at(-1) === "contents" || !path.length) return NextResponse.json({ error: { code: "bad_request", message: "A folder path is required." } }, { status: 400 });
    await deleteFolder(path);
    return new NextResponse(null, { status: 204 });
  } catch (error: unknown) {
    if (error instanceof MutationConflictError) return NextResponse.json({ error: { code: "name_conflict", message: error.message } }, { status: 409 });
    if (error instanceof PathValidationError) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    if ((error as Error).message?.startsWith("Target is a file")) return NextResponse.json({ error: { code: "bad_request", message: (error as Error).message } }, { status: 400 });
    return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
  }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
