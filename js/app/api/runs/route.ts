import { NextResponse } from "next/server";
import { createRun } from "../../../src/lib/run-storage";
import { jsonObject, requiredString, runError } from "../../../src/lib/run-http";
import { defaultMethodNotAllowed } from "../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await jsonObject(request);
    const project = requiredString(body, "project");
    const group = requiredString(body, "group");
    const name = requiredString(body, "name");
    const fileName = requiredString(body, "file_name");
    const casePaths = body.case_paths ?? [];
    if (!Array.isArray(casePaths) || casePaths.some((value) => typeof value !== "string")) throw new Error("Body field 'case_paths' must be a list of strings.");
    const description = body.description === undefined ? "" : body.description;
    if (typeof description !== "string") throw new Error("Body field 'description' must be a string.");
    await createRun(project, group, fileName, name, casePaths as string[], description);
    return NextResponse.json({ ok: true }, { status: 201 });
  } catch (error) { return runError(error); }
}

export const GET = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
