import { NextResponse } from "next/server";
import { listProjects, listRunGroups } from "../../../src/lib/run-storage";
import { runError } from "../../../src/lib/run-http";
import { defaultMethodNotAllowed } from "../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function GET() {
  try {
    const projects = await listProjects();
    const groups: Array<{ project: string; group: string }> = [];
    for (const project of projects) for (const group of await listRunGroups(project)) groups.push({ project, group });
    return NextResponse.json({ projects, groups });
  } catch (error) { return runError(error); }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
