import { stat } from "node:fs/promises";
import { resolve } from "node:path";
import { NextResponse } from "next/server";
import { atomicCreateUtf8 } from "../../../src/lib/atomic-write";
import { resolveDataRoot } from "../../../src/lib/data-root";
import { serializeFeature, type FeaturePayload } from "../../../src/lib/feature";
import { validateFeature, validateEnumReferences } from "../../../src/lib/feature";
import { readProjectEnums } from "../../../src/lib/enums";
import { validateLogicalSegments } from "../../../src/lib/path";
import { defaultMethodNotAllowed } from "../../../src/lib/http-errors";

export async function POST(request: Request) {
  try {
    const body = await request.json() as { parent?: unknown; file_name?: unknown; scenario_name?: unknown; description?: unknown };
    if (typeof body.parent !== "string" || typeof body.file_name !== "string" || typeof body.scenario_name !== "string" || !body.file_name || !body.scenario_name.trim()) throw new Error("invalid");
    const parent = body.parent.split("/").filter(Boolean);
    validateLogicalSegments([...parent, body.file_name]);
    if (parent.length < 2 || parent.length > 10) throw new Error("invalid");
    const target = resolve(resolveDataRoot(), ...parent, body.file_name.toLowerCase().endsWith(".feature") ? body.file_name : `${body.file_name}.feature`);
    if (!(await stat(resolve(resolveDataRoot(), ...parent))).isDirectory()) return NextResponse.json({ error: { code: "not_found", message: "Folder not found." } }, { status: 404 });
    const feature: FeaturePayload = { description: typeof body.description === "string" ? body.description : "", tags: [], background: { steps: [] }, scenario: { kind: "scenario", name: body.scenario_name, tags: [], steps: [], examples: [] }, enums: {} };
    validateFeature(feature);
    try { validateEnumReferences(feature, await readProjectEnums(resolve(resolveDataRoot(), parent[0], "enums.yaml"))); } catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
    await atomicCreateUtf8(target, serializeFeature(feature));
    return NextResponse.json({ ok: true }, { status: 201 });
  } catch (error: unknown) {
    if ((error as NodeJS.ErrnoException).code === "EEXIST") return NextResponse.json({ error: { code: "name_conflict", message: "A file with that name already exists." } }, { status: 409 });
    return NextResponse.json({ error: { code: "bad_request", message: "Invalid file create request." } }, { status: 400 });
  }
}

export const GET = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
