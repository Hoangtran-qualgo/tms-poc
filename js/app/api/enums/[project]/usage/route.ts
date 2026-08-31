import { readdir } from "node:fs/promises";
import { resolve } from "node:path";
import { NextResponse } from "next/server";
import { resolveDataRoot } from "../../../../../src/lib/data-root";
import { readProjectEnums } from "../../../../../src/lib/enums";
import { parseFeature } from "../../../../../src/lib/feature";
import { readUtf8File } from "../../../../../src/lib/utf8";
import { defaultMethodNotAllowed } from "../../../../../src/lib/http-errors";

async function files(directory: string): Promise<string[]> {
  const result: string[] = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const target = resolve(directory, entry.name);
    if (entry.isDirectory()) result.push(...await files(target));
    else if (entry.isFile() && entry.name.toLowerCase().endsWith(".feature")) result.push(target);
  }
  return result;
}

export async function GET(request: Request, context: { params: Promise<{ project: string }> }) {
  const project = (await context.params).project;
  const query = new URL(request.url).searchParams;
  const kind = query.get("kind"), key = query.get("key");
  if (!kind || !key) return NextResponse.json({ error: { code: "bad_request", message: "Query parameters 'kind' and 'key' are required." } }, { status: 400 });
  try {
    const root = resolveDataRoot();
    const vocabulary = await readProjectEnums(resolve(root, project, "enums.yaml"));
    if (!vocabulary[kind] || vocabulary[kind][key] === undefined) return NextResponse.json({ count: 0, sample: [] });
    let count = 0; const sample: string[] = [];
    for (const path of await files(resolve(root, project))) { try { if (parseFeature(await readUtf8File(path)).enums[kind] === key) { count += 1; if (sample.length < 5) sample.push(path.slice(root.length + 1)); } } catch {} }
    return NextResponse.json({ count, sample });
  } catch (error: unknown) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
  }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
