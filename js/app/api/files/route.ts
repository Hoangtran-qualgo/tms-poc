import { readdir, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { NextResponse } from "next/server";
import { atomicCreateUtf8 } from "../../../src/lib/atomic-write";
import { resolveDataRoot } from "../../../src/lib/data-root";
import { serializeFeature, type FeaturePayload } from "../../../src/lib/feature";
import { validateFeature, validateEnumReferences } from "../../../src/lib/feature";
import { readProjectEnums } from "../../../src/lib/enums";
import { validateLogicalSegments } from "../../../src/lib/path";
import { defaultMethodNotAllowed } from "../../../src/lib/http-errors";

async function createGeneratedFeature(parent: string[], source: string): Promise<void> {
  const root = resolveDataRoot();
  const folder = resolve(root, ...parent);
  const stem = parent.at(-1)!;
  const usedNames = new Set((await readdir(folder)).map((name) => name.toLowerCase()));
  for (let number = 1; ; number += 1) {
    const fileName = `${stem}_${number}.feature`;
    if (usedNames.has(fileName.toLowerCase())) continue;
    validateLogicalSegments([...parent, fileName]);
    try {
      await atomicCreateUtf8(resolve(folder, fileName), source);
      return;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
      usedNames.add(fileName.toLowerCase());
    }
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json() as { parent?: unknown; file_name?: unknown; scenario_name?: unknown; description?: unknown };
    if (typeof body.parent !== "string" || typeof body.scenario_name !== "string" || !body.scenario_name.trim() || (body.file_name !== undefined && (typeof body.file_name !== "string" || !body.file_name))) throw new Error("invalid");
    const parent = body.parent.split("/").filter(Boolean);
    validateLogicalSegments(parent);
    if (parent.length < 2 || parent.length > 10) throw new Error("invalid");
    if (!(await stat(resolve(resolveDataRoot(), ...parent))).isDirectory()) return NextResponse.json({ error: { code: "not_found", message: "Folder not found." } }, { status: 404 });
    const feature: FeaturePayload = { description: typeof body.description === "string" ? body.description : "", tags: [], background: { steps: [] }, scenario: { kind: "scenario", name: body.scenario_name, tags: [], steps: [], examples: [] }, enums: {} };
    validateFeature(feature);
    try { validateEnumReferences(feature, await readProjectEnums(resolve(resolveDataRoot(), parent[0], "enums.yaml"))); } catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
    const source = serializeFeature(feature);
    if (body.file_name) {
      const fileName = body.file_name.toLowerCase().endsWith(".feature") ? body.file_name : `${body.file_name}.feature`;
      validateLogicalSegments([fileName]);
      await atomicCreateUtf8(resolve(resolveDataRoot(), ...parent, fileName), source);
    } else {
      await createGeneratedFeature(parent, source);
    }
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
