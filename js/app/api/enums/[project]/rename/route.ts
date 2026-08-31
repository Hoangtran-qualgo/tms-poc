import { readdir } from "node:fs/promises";
import { resolve } from "node:path";
import { NextResponse } from "next/server";
import { atomicWriteUtf8 } from "../../../../../src/lib/atomic-write";
import { EnumsParseError, readProjectEnums, serializeEnumVocabulary } from "../../../../../src/lib/enums";
import { GherkinParseError, parseFeature, serializeFeature, type FeaturePayload } from "../../../../../src/lib/feature";
import { resolveDataRoot } from "../../../../../src/lib/data-root";
import { readUtf8File } from "../../../../../src/lib/utf8";
import { defaultMethodNotAllowed } from "../../../../../src/lib/http-errors";

const ENUM_KEY_RE = /^[A-Za-z_][A-Za-z0-9_-]*$/;

async function featureFiles(directory: string): Promise<string[]> {
  const found: string[] = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) found.push(...await featureFiles(path));
    else if (entry.isFile() && entry.name.toLowerCase().endsWith(".feature")) found.push(path);
  }
  return found;
}

export async function POST(request: Request, context: { params: Promise<{ project: string }> }) {
  const project = (await context.params).project;
  try {
    const body = await request.json() as { kind?: unknown; old_key?: unknown; new_key?: unknown };
    if (typeof body.kind !== "string" || typeof body.old_key !== "string" || typeof body.new_key !== "string" || !body.kind || !body.old_key || !body.new_key) throw new Error("kind, old_key, and new_key are required.");
    if (!ENUM_KEY_RE.test(body.new_key)) throw new Error("Invalid new enum key.");
    const root = resolveDataRoot();
    const enumPath = resolve(root, project, "enums.yaml");
    const vocabulary = await readProjectEnums(enumPath);
    if (!vocabulary[body.kind]?.[body.old_key]) throw new Error("Unknown enum kind or key.");
    if (vocabulary[body.kind][body.new_key]) return NextResponse.json({ error: { code: "name_conflict", message: "Enum key already exists." } }, { status: 409 });
    const files = await featureFiles(resolve(root, project));
    if (body.new_key === body.old_key) return NextResponse.json({ renamed: 0 });
    const updates: Array<{ path: string; feature: FeaturePayload }> = [];
    for (const path of files) {
      const feature = parseFeature(await readUtf8File(path));
      if (feature.enums[body.kind] === body.old_key) updates.push({ path, feature: { ...feature, enums: { ...feature.enums, [body.kind]: body.new_key } } });
    }
    const next = { ...vocabulary, [body.kind]: { ...vocabulary[body.kind], [body.new_key]: vocabulary[body.kind][body.old_key] } };
    // Alias-first ordering matches the Python cascade: readers never observe
    // a feature selecting a key that is absent from enums.yaml.
    await atomicWriteUtf8(enumPath, serializeEnumVocabulary(next));
    for (const update of updates) await atomicWriteUtf8(update.path, serializeFeature(update.feature));
    const finalEntries = Object.entries(vocabulary[body.kind]).filter(([key]) => key !== body.old_key);
    finalEntries.push([body.new_key, vocabulary[body.kind][body.old_key]]);
    const final = { ...vocabulary, [body.kind]: Object.fromEntries(finalEntries) };
    await atomicWriteUtf8(enumPath, serializeEnumVocabulary(final));
    return NextResponse.json({ renamed: updates.length });
  } catch (error: unknown) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    if (error instanceof GherkinParseError) return NextResponse.json({ error: { code: "parse_error", message: error.message, details: { line: error.line, column: error.column } } }, { status: 422 });
    if (error instanceof EnumsParseError) return NextResponse.json({ error: { code: "enums_parse_error", message: error.message, details: { line: error.line, column: error.column } } }, { status: 422 });
    return NextResponse.json({ error: { code: "validation_error", message: (error as Error).message, details: { field: "enum" } } }, { status: 422 });
  }
}

export const GET = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
