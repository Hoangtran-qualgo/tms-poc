import { NextResponse } from "next/server";
import { readReport } from "../../../../../../src/lib/report-storage";
import { reportError } from "../../../../../../src/lib/report-http";
import { computeReport } from "../../../../../../src/lib/reporting";
import { defaultMethodNotAllowed } from "../../../../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: Promise<{ project: string; file_name: string }> }) {
  try { const { project, file_name } = await context.params; return NextResponse.json(await computeReport(project, await readReport(project, file_name))); }
  catch (error) { return reportError(error); }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
