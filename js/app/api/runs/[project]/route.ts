import { NextResponse } from "next/server";
import { listRunGroups, listRuns } from "../../../../src/lib/run-storage";
import { runError } from "../../../../src/lib/run-http";
import { defaultMethodNotAllowed } from "../../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: Promise<{ project: string }> }) {
  try {
    const { project } = await context.params;
    const runs: Array<Record<string, unknown>> = [];
    for (const group of await listRunGroups(project)) for (const run of await listRuns(project, group)) runs.push({ path: `${project}/test-run/${group}/${run.file_name}`, group, ...run });
    runs.sort((left, right) => String(left.path).localeCompare(String(right.path)));
    runs.sort((left, right) => String(right.created_at ?? "").localeCompare(String(left.created_at ?? "")));
    return NextResponse.json({ runs });
  } catch (error) { return runError(error); }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
