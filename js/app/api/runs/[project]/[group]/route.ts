import { NextResponse } from "next/server";
import { listRuns } from "../../../../../src/lib/run-storage";
import { runError } from "../../../../../src/lib/run-http";
import { defaultMethodNotAllowed } from "../../../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: Promise<{ project: string; group: string }> }) {
  try {
    const { project, group } = await context.params;
    return NextResponse.json({ runs: await listRuns(project, group) });
  } catch (error) { return runError(error); }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
