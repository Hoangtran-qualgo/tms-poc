import { NextResponse } from "next/server";
import { deleteReport, readReport, writeReport } from "../../../../../src/lib/report-storage";
import { reportError, reportJson } from "../../../../../src/lib/report-http";
import { parseReport, ReportValidationError } from "../../../../../src/lib/report";
import { defaultMethodNotAllowed } from "../../../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: Promise<{ project: string; file_name: string }> }) {
  try { const { project, file_name } = await context.params; return NextResponse.json(await readReport(project, file_name)); }
  catch (error) { return reportError(error); }
}

export async function PATCH(request: Request, context: { params: Promise<{ project: string; file_name: string }> }) {
  try {
    const { project, file_name } = await context.params;
    const existing = await readReport(project, file_name);
    const incoming = parseReport(JSON.stringify(await reportJson(request)));
    if (incoming.type !== existing.type) throw new ReportValidationError("type", "Report type is immutable.");
    if (incoming.created_at && incoming.created_at !== existing.created_at) throw new ReportValidationError("created_at", "created_at is immutable.");
    incoming.created_at = existing.created_at;
    await writeReport(project, file_name, incoming);
    return NextResponse.json({ ok: true });
  } catch (error) { return reportError(error); }
}

export async function DELETE(_request: Request, context: { params: Promise<{ project: string; file_name: string }> }) {
  try { const { project, file_name } = await context.params; await deleteReport(project, file_name); return new NextResponse(null, { status: 204 }); }
  catch (error) { return reportError(error); }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
