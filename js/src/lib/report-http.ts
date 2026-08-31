import { NextResponse } from "next/server";
import { PathValidationError } from "./path";
import { ReportConflictError, ReportParseError, ReportValidationError } from "./report";

export function reportError(error: unknown): NextResponse {
  if (error instanceof PathValidationError) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
  if (error instanceof ReportConflictError) return NextResponse.json({ error: { code: "name_conflict", message: error.message } }, { status: 409 });
  if (error instanceof ReportParseError) return NextResponse.json({ error: { code: "report_parse_error", message: error.message, details: { line: error.line, column: error.column } } }, { status: 422 });
  if (error instanceof ReportValidationError) return NextResponse.json({ error: { code: "validation_error", message: error.message, details: { field: error.field } } }, { status: 422 });
  if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
  if (error instanceof SyntaxError) return NextResponse.json({ error: { code: "bad_request", message: "Request body must be a JSON object." } }, { status: 400 });
  if (error instanceof Error) return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
  console.error("Unexpected error in report API handler", error);
  return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
}

export async function reportJson(request: Request) {
  const body = await request.json();
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error("Request body must be a JSON object.");
  return body as Record<string, unknown>;
}
