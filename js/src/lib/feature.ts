import { generateMessages } from "@cucumber/gherkin";
import { IdGenerator, SourceMediaType } from "@cucumber/messages";

type Tag = { name: string; location: { line: number; column?: number } };
type Step = { keyword: string; text: string; data_table: string[][] | null };
type Examples = { tags: string[]; name: string; header: string[]; rows: string[][] };

export type FeaturePayload = {
  description: string;
  tags: string[];
  background: { steps: Step[] };
  scenario: { kind: "scenario" | "outline"; name: string; tags: string[]; steps: Step[]; examples: Examples[] };
  enums: Record<string, string>;
};
export type EnumVocabulary = Record<string, Record<string, string>>;

export class GherkinParseError extends Error {
  constructor(message: string, readonly line = 0, readonly column = 0) {
    super(message);
  }
}
export class FeatureValidationError extends Error { constructor(readonly field: string, message: string) { super(message); } }

export function validateEnumReferences(feature: FeaturePayload, vocabulary: EnumVocabulary): void {
  for (const [kind, key] of Object.entries(feature.enums)) {
    if (key && vocabulary[kind]?.[key] === undefined) {
      throw new FeatureValidationError(`enums[${kind}]`, `Unknown enum key '${key}' for kind '${kind}'.`);
    }
  }
}

export function validateFeature(feature: FeaturePayload): void {
  if (typeof feature.description !== "string") throw new FeatureValidationError("description", "Description must be a string.");
  for (const [field, values] of [["tags", feature.tags], ["scenario.tags", feature.scenario.tags]] as const) {
    if (!Array.isArray(values) || values.some((tag) => typeof tag !== "string" || !tag || /[\s@,]/.test(tag))) throw new FeatureValidationError(field, "Tags must be non-empty printable values without whitespace, @, or comma.");
  }
  for (const [field, stepsToCheck] of [["background.steps", feature.background.steps], ["scenario.steps", feature.scenario.steps]] as const) {
    if (!Array.isArray(stepsToCheck)) throw new FeatureValidationError(field, "Steps must be a list.");
    for (const [index, step] of stepsToCheck.entries()) {
      if (!CANONICAL_KEYWORDS.has(step.keyword) || !step.text.trim() || /[\r\n]/.test(step.text)) throw new FeatureValidationError(`${field}[${index}]`, "Step keyword or text is invalid.");
      if (step.data_table && (!step.data_table.length || step.data_table.some((row) => row.length !== step.data_table![0].length))) throw new FeatureValidationError(`${field}[${index}].data_table`, "Data tables must be rectangular and non-empty.");
    }
  }
  if (feature.scenario.kind !== "scenario" && feature.scenario.kind !== "outline") throw new FeatureValidationError("scenario.kind", "Scenario kind is invalid.");
  if (feature.scenario.kind === "scenario" && feature.scenario.examples.length) throw new FeatureValidationError("scenario.examples", "Scenario examples require outline kind.");
  if (feature.scenario.kind === "outline" && !feature.scenario.examples.length) throw new FeatureValidationError("scenario.examples", "Scenario outlines must have examples.");
}

const CANONICAL_KEYWORDS = new Set(["Given", "When", "Then", "And", "But"]);
const ENUM_KIND_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
const ENUM_KEY_RE = /^[A-Za-z_][A-Za-z0-9_-]*$/;
const ENUM_DIRECTIVE_RE = /^#\s*enum\.([^:\s]+)\s*:\s*(.*?)\s*$/;

function tags(items: readonly Tag[]): string[] {
  return items.map((tag) => (tag.name.startsWith("@") ? tag.name.slice(1) : tag.name));
}

function tableRows(table: { rows: readonly { cells: readonly { value: string }[] }[] } | undefined): string[][] | null {
  if (!table?.rows.length) return null;
  return table.rows.map((row) => row.cells.map((cell) => cell.value));
}

function steps(items: readonly { keyword: string; text: string; dataTable?: { rows: readonly { cells: readonly { value: string }[] }[] } }[]): Step[] {
  return items.flatMap((step) => {
    const keyword = step.keyword.trim();
    return CANONICAL_KEYWORDS.has(keyword) ? [{ keyword, text: step.text, data_table: tableRows(step.dataTable) }] : [];
  });
}

function enumDirectives(document: {
  comments: readonly { text: string; location: { line: number; column?: number } }[];
  feature: NonNullable<unknown> & { location: { line: number }; tags: readonly Tag[] };
}): Record<string, string> {
  const cutoff = Math.min(document.feature.location.line, document.feature.tags[0]?.location.line ?? document.feature.location.line);
  const result: Record<string, string> = {};
  for (const comment of document.comments) {
    if (comment.location.line >= cutoff) continue;
    const match = ENUM_DIRECTIVE_RE.exec(comment.text.trim());
    if (!match) continue;
    const [, kind, key] = match;
    if (!ENUM_KIND_RE.test(kind) || !ENUM_KEY_RE.test(key) || kind in result) {
      throw new GherkinParseError("Invalid enum directive.", comment.location.line, comment.location.column ?? 0);
    }
    result[kind] = key;
  }
  return result;
}

export function parseFeature(source: string): FeaturePayload {
  const messages = generateMessages(
    source.replace(/\r\n/g, "\n").replace(/\r/g, "\n"),
    "case.feature",
    SourceMediaType.TEXT_X_CUCUMBER_GHERKIN_PLAIN,
    { newId: IdGenerator.uuid(), includeSource: false, includeGherkinDocument: true, includePickles: false, defaultDialect: "en" },
  );
  const parserError = messages.find((message) => message.parseError)?.parseError;
  if (parserError) {
    const location = parserError.source.location;
    throw new GherkinParseError(parserError.message, location?.line ?? 0, location?.column ?? 0);
  }
  const document = messages.find((message) => message.gherkinDocument)?.gherkinDocument;
  if (!document?.feature) throw new GherkinParseError("No 'Feature:' header found in the file.", 1, 1);
  const feature = document.feature;
  let background: { steps: Step[] } = { steps: [] };
  const scenarios = [] as NonNullable<typeof feature.children[number]["scenario"]>[];
  for (const child of feature.children) {
    if (child.rule) throw new GherkinParseError("'Rule:' blocks are not supported (one scenario per file).", child.rule.location.line, child.rule.location.column);
    if (child.background) background = { steps: steps(child.background.steps) };
    if (child.scenario) scenarios.push(child.scenario);
  }
  if (scenarios.length > 1) {
    throw new GherkinParseError("More than one scenario in the file. TMS requires exactly one scenario per .feature file.", scenarios[1].location.line, scenarios[1].location.column);
  }
  const scenario = scenarios[0];
  const isOutline = Boolean(scenario && (scenario.keyword.trim() === "Scenario Outline" || scenario.keyword.trim() === "Scenarios" || scenario.examples.length));
  return {
    description: (feature.description ? `${feature.name}\n${feature.description}` : feature.name).replace(/\\n/g, "\n"),
    tags: tags(feature.tags),
    background,
    scenario: scenario
      ? {
          kind: isOutline ? "outline" : "scenario",
          name: scenario.name,
          tags: tags(scenario.tags),
          steps: steps(scenario.steps),
          examples: isOutline
            ? scenario.examples.map((example) => ({
                tags: tags(example.tags),
                name: example.name,
                header: example.tableHeader?.cells.map((cell) => cell.value) ?? [],
                rows: example.tableBody.map((row) => row.cells.map((cell) => cell.value)),
              }))
            : [],
        }
      : { kind: "scenario", name: "", tags: [], steps: [], examples: [] },
    enums: enumDirectives({ comments: document.comments, feature }),
  };
}

export function splitFeatureSource(source: string): FeaturePayload[] {
  let normalized = source.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const significant = normalized.split("\n").find((line) => {
    const value = line.trim();
    return value && !value.startsWith("#") && !value.startsWith("@");
  });
  if (significant && !/^\s*Feature\s*:/.test(significant)) normalized = `Feature:\n${normalized}`;
  const lines = normalized.split("\n");
  const starts: number[] = [];
  for (let index = 0; index < lines.length; index += 1) {
    if (/^\s*Scenario(?: Outline)?\s*:/.test(lines[index]) || /^\s*Scenarios\s*:/.test(lines[index])) {
      let start = index;
      while (start > 0 && /^\s*@/.test(lines[start - 1])) start -= 1;
      starts.push(start);
    }
  }
  if (!starts.length) return [];
  const prefix = lines.slice(0, starts[0]).join("\n");
  return starts.map((start, index) => {
    const end = starts[index + 1] ?? lines.length;
    const payload = parseFeature(`${prefix}\n${lines.slice(start, end).join("\n")}`);
    return { ...payload, enums: {} };
  });
}

export function serializeFeature(feature: FeaturePayload): string {
  validateFeature(feature);
  if (!feature.scenario.name.trim()) throw new FeatureValidationError("scenario.name", "Scenario name must not be empty.");
  for (const [index, step] of feature.background.steps.concat(feature.scenario.steps).entries()) {
    if (!CANONICAL_KEYWORDS.has(step.keyword) || !step.text.trim()) throw new FeatureValidationError(`steps[${index}]`, "Step keyword or text is invalid.");
  }
  if (feature.scenario.kind === "outline" && !feature.scenario.examples.length) throw new FeatureValidationError("scenario.examples", "Scenario outlines must have examples.");
  const lines: string[] = [];
  const emitSteps = (stepsToEmit: Step[], indent: string) => {
    for (const step of stepsToEmit) {
      lines.push(`${indent}${step.keyword} ${step.text.trim()}`);
      lines.push(...renderTable(step.data_table ?? [], indent.length + 2));
    }
  };
  for (const [kind, key] of Object.entries(feature.enums).sort(([left], [right]) => left.localeCompare(right))) {
    if (key) lines.push(`# enum.${kind}: ${key}`);
  }
  const featureTags = dedupeTags(feature.tags);
  if (featureTags.length) lines.push(featureTags.map((tag) => `@${tag}`).join(" "));
  lines.push(`Feature: ${feature.description.replace(/\n/g, "\\n")}`, "");
  if (feature.background.steps.length) {
    lines.push("  Background:");
    emitSteps(feature.background.steps, "    ");
    lines.push("");
  }
  const scenarioTags = dedupeTags(feature.scenario.tags);
  if (scenarioTags.length) lines.push(`  ${scenarioTags.map((tag) => `@${tag}`).join(" ")}`);
  lines.push(`  ${feature.scenario.kind === "outline" ? "Scenario Outline" : "Scenario"}:${feature.scenario.name ? ` ${feature.scenario.name}` : ""}`);
  emitSteps(feature.scenario.steps, "    ");
  if (feature.scenario.kind === "outline") {
    for (const example of feature.scenario.examples) {
      const exampleTags = dedupeTags(example.tags);
      if (exampleTags.length) lines.push(`    ${exampleTags.map((tag) => `@${tag}`).join(" ")}`);
      lines.push(`    Examples:${example.name ? ` ${example.name}` : ""}`);
      lines.push(...renderTable([example.header, ...example.rows], 6));
    }
  }
  return `${lines.join("\n")}\n`;
}

function dedupeTags(tags: string[]): string[] {
  return [...new Set(tags)];
}

function renderTable(rows: string[][], indent: number): string[] {
  if (!rows.length) return [];
  const processed = rows.map((row) => row.map((cell) => {
    const trimmed = cell.trim();
    if (!trimmed) return " ";
    return trimmed.replaceAll("\\", "\\\\").replaceAll("|", "\\|");
  }));
  const widths = Array.from({ length: processed[0].length }, (_, index) => Math.max(...processed.map((row) => row[index]?.length ?? 0)));
  return processed.map((row) => `${" ".repeat(indent)}| ${row.map((cell, index) => cell.padEnd(widths[index])).join(" | ")} |`);
}
