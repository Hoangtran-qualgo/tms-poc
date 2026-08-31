import { NextResponse } from "next/server";
import { removeRunCase, updateRunResult } from "../../../../../../../../src/lib/run-storage";
import { jsonObject, runError } from "../../../../../../../../src/lib/run-http";
import { defaultMethodNotAllowed } from "../../../../../../../../src/lib/http-errors";

export const runtime = "nodejs";

function casePath(raw: string | string[]): string { return Array.isArray(raw) ? raw.join("/") : raw; }

export async function DELETE(_request: Request, context: { params: Promise<{ project: string; group: string; file_name: string; case_path: string[] }> }) {
  try {
    const { project, group, file_name, case_path } = await context.params;
    await removeRunCase(project, group, file_name, casePath(case_path));
    return new NextResponse(null, { status: 204 });
  } catch (error) { return runError(error); }
}

export async function PATCH(request: Request, context: { params: Promise<{ project: string; group: string; file_name: string; case_path: string[] }> }) {
  try {
    const { project, group, file_name, case_path } = await context.params;
    const body = await jsonObject(request);
    if (body.result !== undefined && typeof body.result !== "string") throw new Error("Body field 'result' must be a string if present.");
    if (body.remark !== undefined && typeof body.remark !== "string") throw new Error("Body field 'remark' must be a string if present.");
    await updateRunResult(project, group, file_name, casePath(case_path), body.result as string | undefined, body.remark as string | undefined);
    return NextResponse.json({ ok: true });
  } catch (error) { return runError(error); }
}

export const GET = defaultMethodNotAllowed;
export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
