import { NextResponse } from "next/server";
import { createReport, listReports } from "../../../../src/lib/report-storage";
import { reportError, reportJson } from "../../../../src/lib/report-http";
import { parseReport } from "../../../../src/lib/report";
import { defaultMethodNotAllowed } from "../../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function POST(request: Request, context: { params: Promise<{ project: string }> }) {
  try {
    const { project } = await context.params;
    const body = await reportJson(request);
    const fileName = body.file_name;
    if (typeof fileName !== "string" || !fileName) throw new Error("Body field 'file_name' must be a non-empty string.");
    await createReport(project, fileName, parseReport(JSON.stringify(body)));
    return NextResponse.json({ ok: true }, { status: 201 });
  } catch (error) { return reportError(error); }
}

export async function GET(_request: Request, context: { params: Promise<{ project: string }> }) {
  try { return NextResponse.json({ reports: await listReports((await context.params).project) }); }
  catch (error) { return reportError(error); }
}

export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
