import { NextResponse } from "next/server";
import { deleteRun, readRun, writeRun } from "../../../../../../src/lib/run-storage";
import { jsonObject, runError } from "../../../../../../src/lib/run-http";
import { parseRun, RunValidationError } from "../../../../../../src/lib/run";
import { defaultMethodNotAllowed } from "../../../../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: Promise<{ project: string; group: string; file_name: string }> }) {
  try {
    const { project, group, file_name } = await context.params;
    return NextResponse.json(await readRun(project, group, file_name));
  } catch (error) { return runError(error); }
}

export async function PATCH(request: Request, context: { params: Promise<{ project: string; group: string; file_name: string }> }) {
  try {
    const { project, group, file_name } = await context.params;
    const body = await jsonObject(request);
    const next = parseRun(JSON.stringify(body));
    const current = await readRun(project, group, file_name);
    if (next.created_at !== current.created_at) throw new RunValidationError("created_at", "created_at is immutable.");
    await writeRun(project, group, file_name, next);
    return NextResponse.json({ ok: true });
  } catch (error) { return runError(error); }
}

export async function DELETE(_request: Request, context: { params: Promise<{ project: string; group: string; file_name: string }> }) {
  try {
    const { project, group, file_name } = await context.params;
    await deleteRun(project, group, file_name);
    return new NextResponse(null, { status: 204 });
  } catch (error) { return runError(error); }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
