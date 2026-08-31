import { NextResponse } from "next/server";
import { addRunCase } from "../../../../../../../src/lib/run-storage";
import { jsonObject, requiredString, runError } from "../../../../../../../src/lib/run-http";
import { defaultMethodNotAllowed } from "../../../../../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function POST(request: Request, context: { params: Promise<{ project: string; group: string; file_name: string }> }) {
  try {
    const { project, group, file_name } = await context.params;
    await addRunCase(project, group, file_name, requiredString(await jsonObject(request), "file_path"));
    return NextResponse.json({ ok: true }, { status: 201 });
  } catch (error) { return runError(error); }
}

export const GET = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
