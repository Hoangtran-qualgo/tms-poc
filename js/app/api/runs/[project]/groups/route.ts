import { NextResponse } from "next/server";
import { createRunGroup } from "../../../../../src/lib/run-storage";
import { jsonObject, requiredString, runError } from "../../../../../src/lib/run-http";
import { defaultMethodNotAllowed } from "../../../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function POST(request: Request, context: { params: Promise<{ project: string }> }) {
  try {
    const { project } = await context.params;
    const body = await jsonObject(request);
    await createRunGroup(project, requiredString(body, "name"));
    return NextResponse.json({ ok: true }, { status: 201 });
  } catch (error) { return runError(error); }
}

export const GET = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
