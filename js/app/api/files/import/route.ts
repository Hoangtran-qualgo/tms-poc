import { readdir, unlink } from "node:fs/promises";
import { resolve } from "node:path";
import { NextResponse } from "next/server";
import { atomicCreateUtf8 } from "../../../../src/lib/atomic-write";
import { resolveDataRoot } from "../../../../src/lib/data-root";
import { FeatureValidationError, GherkinParseError, parseFeature, splitFeatureSource, serializeFeature } from "../../../../src/lib/feature";
import { PathValidationError, validateLogicalSegments } from "../../../../src/lib/path";
import { readUtf8File } from "../../../../src/lib/utf8";
import { defaultMethodNotAllowed } from "../../../../src/lib/http-errors";

const MAX_FILES = 20, MAX_BYTES = 3 * 1024 * 1024, MAX_FOLDER_DEPTH = 10;
const bad = (message: string) => NextResponse.json({ error: { code: "bad_request", message } }, { status: 400 });
function normalizeFeatureName(name: string): string {
  if (!name) throw new Error("Feature file name must not be empty.");
  const leaf = name.toLowerCase().endsWith(".feature") ? name : name.includes(".") ? (() => { throw new Error(`Feature file name must end with '.feature'; got '${name}'.`); })() : `${name}.feature`;
  validateLogicalSegments([leaf]);
  return leaf;
}
type ImportBody = { parent?: unknown; project?: unknown; source?: unknown; sources?: unknown; names?: unknown };

function requireLegacySource(body: ImportBody): string {
  const source = body.source ?? "";
  if (typeof source !== "string") throw new Error("Body field 'source' must be a string.");
  if (Buffer.byteLength(source) > MAX_BYTES) throw new Error("Imported file exceeds the 3 MB limit.");
  return source;
}

function requireParent(body: ImportBody): string[] {
  if (typeof body.parent !== "string") throw new Error("Body field 'parent' must be a string.");
  const parent = body.parent.split("/").filter(Boolean);
  if (!parent.length) throw new PathValidationError("Import destination is required.");
  validateLogicalSegments(parent);
  if (parent.length < 2 || parent.length > MAX_FOLDER_DEPTH) throw new Error(`Import destination must be a module or sub-folder (2..${MAX_FOLDER_DEPTH} segments); got ${parent.length}.`);
  return parent;
}

function validateProject(body: ImportBody, parent: string[]): void {
  if (body.project === undefined) return;
  if (typeof body.project !== "string") throw new Error("Body field 'project' must be a string.");
  if (body.project && body.project !== parent[0]) throw new Error(`Body field 'project' (${body.project}) must match the first segment of 'parent' (${parent[0]}).`);
}

async function input(body: ImportBody, preview: boolean) {
  if (!Array.isArray(body.sources) || !body.sources.length || body.sources.length > MAX_FILES) throw new Error("Invalid batch request.");
  if (body.parent !== undefined && typeof body.parent !== "string") throw new Error("Body field 'parent' must be a string.");
  let bytes = 0; const sources: Array<{ name: string; source: string }> = [];
  for (const value of body.sources) { const item = value as { name?: unknown; source?: unknown }; if (typeof item?.name !== "string" || !item.name || typeof item.source !== "string") throw new Error("Each source needs a name and source."); bytes += Buffer.byteLength(item.source); sources.push({ name: item.name, source: item.source }); }
  if (bytes > MAX_BYTES) throw new Error("Import batch exceeds the 3 MB total limit.");
  const parent = typeof body.parent === "string" ? body.parent.split("/").filter(Boolean) : [];
  if (!preview && !parent.length) throw new PathValidationError("Import destination is required.");
  if (parent.length) validateLogicalSegments(parent);
  if (!preview && (parent.length < 2 || parent.length > MAX_FOLDER_DEPTH)) throw new Error(`Import destination must be a module or sub-folder (2..${MAX_FOLDER_DEPTH} segments); got ${parent.length}.`);
  if (!preview && parent.length) validateProject(body, parent);
  const names = body.names;
  if (!preview && (!Array.isArray(names) || names.some((value) => typeof value !== "string"))) throw new Error("Body field 'names' must be a list of strings.");
  return { parent, sources, names: (names as string[] | undefined) ?? [] };
}

function sourceError(sourceIndex: number, sourceName: string, code: string, message: string, error?: unknown) {
  const result: Record<string, unknown> = { source_index: sourceIndex, source_name: sourceName, code, message };
  if (error instanceof GherkinParseError) { result.line = error.line; result.column = error.column; }
  return result;
}

function hasEnumDirectives(source: string): boolean {
  return source.split(/\r\n|\r|\n/).some((line) => /^#\s*enum\.[^:\s]+\s*:\s*.*$/.test(line.trim()));
}

type ImportCase = { feature: ReturnType<typeof splitFeatureSource>[number]; sourceIndex: number; sourceName: string };

async function commitCases(parent: string[], cases: ImportCase[], names: string[]) {
  if (names.length !== cases.length) throw new Error(`Expected ${cases.length} file name(s) to match the ${cases.length} scenario(s); got ${names.length}.`);
  const root = resolveDataRoot(), target = resolve(root, ...parent);
  const entries = await readdir(target, { withFileTypes: true });
  const used = new Set(entries.map((entry) => entry.name.toLowerCase()));
  const existingScenarios = new Set<string>();
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.toLowerCase().endsWith(".feature")) continue;
    try { const feature = parseFeature(await readUtf8File(resolve(target, entry.name))); if (feature.scenario.name.trim()) existingScenarios.add(feature.scenario.name.trim().toLowerCase()); } catch { /* malformed siblings remain non-blocking, as in Python listing */ }
  }
  const normalizedNames: string[] = [], nameErrors: string[] = [], duplicateNames = new Set<string>(), importedScenarios = new Set<string>();
  for (const [index, item] of cases.entries()) {
    const label = item.feature.scenario.name.trim() || `scenario #${index + 1}`;
    let leaf: string;
    try { leaf = normalizeFeatureName(names[index]); }
    catch (error) { nameErrors.push(`${label}: ${(error as Error).message}`); continue; }
    const key = leaf.toLowerCase();
    if (used.has(key)) nameErrors.push(`${label}: a file named '${leaf}' already exists in the destination.`);
    else if (duplicateNames.has(key)) nameErrors.push(`${label}: duplicate file name '${leaf}' within this import.`);
    else duplicateNames.add(key);
    normalizedNames.push(leaf);
    const scenarioKey = item.feature.scenario.name.trim().toLowerCase();
    if (scenarioKey && existingScenarios.has(scenarioKey)) nameErrors.push(`${label}: a case with scenario name '${item.feature.scenario.name.trim()}' already exists in the destination.`);
    else if (scenarioKey && importedScenarios.has(scenarioKey)) nameErrors.push(`${label}: duplicate scenario name '${item.feature.scenario.name.trim()}' within this import.`);
    else if (scenarioKey) importedScenarios.add(scenarioKey);
  }
  if (nameErrors.length) return NextResponse.json({ error: { code: "import_validation_error", message: `Import aborted: ${nameErrors.length} problem(s) found.`, details: { reasons: nameErrors } } }, { status: 422 });
  const created: string[] = [];
  try { for (const [index, item] of cases.entries()) { await atomicCreateUtf8(resolve(target, normalizedNames[index]), serializeFeature(item.feature)); created.push(`${parent.join("/")}/${normalizedNames[index]}`); } }
  catch (error) { await Promise.all(created.map((path) => unlink(resolve(root, path)).catch(() => undefined))); throw error; }
  return NextResponse.json({ ok: true, created }, { status: 201 });
}

export async function POST(request: Request) {
  try {
    const isPreview = request.url.includes("/preview");
    const body = await request.json() as ImportBody;
    if (!("sources" in body)) {
      const source = requireLegacySource(body);
      const features = splitFeatureSource(source);
      if (isPreview) {
        return NextResponse.json({
          description: features[0]?.description ?? "",
          tags: features[0]?.tags ?? [],
          enums_present: hasEnumDirectives(source),
          scenarios: features.map((feature) => ({ scenario_name: feature.scenario.name, step_count: feature.scenario.steps.length, scenario_tags: feature.scenario.tags })),
        });
      }
      const parent = requireParent(body);
      validateProject(body, parent);
      const names = body.names;
      if (!Array.isArray(names) || names.some((value) => typeof value !== "string")) throw new Error("Body field 'names' must be a list of strings.");
      if (!features.length) return NextResponse.json({ error: { code: "import_validation_error", message: "Import validation failed.", details: { reasons: [{ code: "no_scenarios", message: "No scenarios to import." }] } } }, { status: 422 });
      if (names.length !== features.length) throw new Error(`Expected ${features.length} file name(s) to match the ${features.length} scenario(s); got ${names.length}.`);
      const validationReasons: string[] = [];
      for (const [index, feature] of features.entries()) {
        const label = feature.scenario.name.trim() || `scenario #${index + 1}`;
        if (!feature.scenario.name.trim()) validationReasons.push(`scenario #${index + 1}: scenario name is required.`);
        if (!feature.scenario.steps.length) validationReasons.push(`${label}: scenario must have at least one step.`);
        try { serializeFeature(feature); } catch (error) { validationReasons.push(`${label}: ${(error as Error).message}`); }
      }
      if (validationReasons.length) return NextResponse.json({ error: { code: "import_validation_error", message: `Import aborted: ${validationReasons.length} problem(s) found.`, details: { reasons: validationReasons } } }, { status: 422 });
      const cases = features.map((feature) => ({ feature, sourceIndex: 0, sourceName: "source" }));
      return await commitCases(parent, cases, names);
    }
    const { parent, sources, names } = await input(body, isPreview);
    const cases: ImportCase[] = [];
    const errors: Record<string, unknown>[] = [];
    const enumSources: Record<string, unknown>[] = [];
    for (const [sourceIndex, item] of sources.entries()) {
      if (!item.name.toLowerCase().endsWith(".feature")) {
        errors.push(sourceError(sourceIndex, item.name, "invalid_file_type", "Source file must end with .feature."));
        continue;
      }
      if (hasEnumDirectives(item.source)) enumSources.push({ source_index: sourceIndex, source_name: item.name });
      let split: ReturnType<typeof splitFeatureSource>;
      try { split = splitFeatureSource(item.source); }
      catch (error) { errors.push(sourceError(sourceIndex, item.name, "parse_error", (error as Error).message, error)); continue; }
      if (!split.length) { errors.push(sourceError(sourceIndex, item.name, "no_scenarios", "No scenarios found to import.")); continue; }
      for (const feature of split) {
        if (!feature.scenario.name.trim()) { errors.push(sourceError(sourceIndex, item.name, "validation_error", "Scenario name is required.")); continue; }
        if (!feature.scenario.steps.length) { errors.push(sourceError(sourceIndex, item.name, "validation_error", "Scenario must have at least one step.")); continue; }
        try { serializeFeature(feature); }
        catch (error) { errors.push(sourceError(sourceIndex, item.name, "validation_error", (error as Error).message)); continue; }
        cases.push({ feature, sourceIndex, sourceName: item.name });
      }
    }
    if (isPreview) return NextResponse.json({ errors, enum_sources: enumSources, enums_present: enumSources.length > 0, scenarios: cases.map((item) => ({ source_index: item.sourceIndex, source_name: item.sourceName, scenario_name: item.feature.scenario.name, step_count: item.feature.scenario.steps.length, feature_tags: item.feature.tags, scenario_tags: item.feature.scenario.tags })) });
    if (errors.length) return NextResponse.json({ error: { code: "import_validation_error", message: `Import aborted: ${errors.length} problem(s) found.`, details: { reasons: errors.map((error) => `${String(error.source_name)}: ${String(error.message)}`) } } }, { status: 422 });
    if (!cases.length) return NextResponse.json({ error: { code: "import_validation_error", message: "Import validation failed.", details: { reasons: [{ code: "no_scenarios", message: "No scenarios to import." }] } } }, { status: 422 });
    return await commitCases(parent, cases, names);
  } catch (error) {
    if (error instanceof PathValidationError) return bad(error.message);
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return NextResponse.json({ error: { code: "not_found", message: (error as Error).message } }, { status: 404 });
    if (error instanceof GherkinParseError) return NextResponse.json({ error: { code: "parse_error", message: error.message, details: { line: error.line, column: error.column } } }, { status: 422 });
    if (error instanceof FeatureValidationError) return NextResponse.json({ error: { code: "validation_error", message: error.message, details: { field: error.field } } }, { status: 422 });
    return bad((error as Error).message || "Invalid batch request.");
  }
}

export const GET = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
