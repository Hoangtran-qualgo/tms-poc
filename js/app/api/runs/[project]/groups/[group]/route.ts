import { NextResponse } from "next/server";
import { deleteRunGroup } from "../../../../../../src/lib/run-storage";
import { runError } from "../../../../../../src/lib/run-http";
import { defaultMethodNotAllowed } from "../../../../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function DELETE(_request: Request, context: { params: Promise<{ project: string; group: string }> }) {
  try {
    const { project, group } = await context.params;
    await deleteRunGroup(project, group);
    return new NextResponse(null, { status: 204 });
  } catch (error) { return runError(error); }
}

export const GET = defaultMethodNotAllowed;
export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
