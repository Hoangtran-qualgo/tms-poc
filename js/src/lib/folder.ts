import { readdir, stat } from "node:fs/promises";
import { resolve } from "node:path";

import { generateMessages } from "@cucumber/gherkin";
import { IdGenerator, SourceMediaType } from "@cucumber/messages";
import { parseEnumVocabulary, type EnumVocabulary } from "./enums";
import { PathValidationError, validateLogicalSegments } from "./path";
import { readUtf8File } from "./utf8";

const MAX_FOLDER_DEPTH = 10;
const TEMP_FILE_RE = /.+\.tmp\.\d+\.[0-9a-f]+$/;
const FEATURE_FILE_RE = /\.feature$/i;
const RESERVED_TYPED_AREAS = new Set(["test-run", "report"]);
const ENUM_KIND_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
const ENUM_KEY_RE = /^[A-Za-z_][A-Za-z0-9_-]*$/;
const ENUM_DIRECTIVE_RE = /^#\s*enum\.([^:\s]+)\s*:\s*(.*?)\s*$/;

export type FeatureSummary = {
  file_name: string;
  description: string;
  scenario_name: string;
  tags: string[];
  enums: Array<{ kind: string; key: string; label: string }>;
};

export type FolderListing =
  | { kind: "root"; projects: string[] }
  | { kind: "project"; modules: string[] }
  | { kind: "module" | "subfolder"; folders: string[]; features: FeatureSummary[] };

export { PathValidationError as FolderPathError } from "./path";
export class FolderNotFoundError extends Error {}

function parseDocument(source: string) {
  const messages = generateMessages(
    source.replace(/\r\n/g, "\n").replace(/\r/g, "\n"),
    "case.feature",
    SourceMediaType.TEXT_X_CUCUMBER_GHERKIN_PLAIN,
    {
      newId: IdGenerator.uuid(),
      includeSource: false,
      includeGherkinDocument: true,
      includePickles: false,
      defaultDialect: "en",
    },
  );
  const document = messages.find((message) => message.gherkinDocument)?.gherkinDocument;
  if (!document?.feature || messages.some((message) => message.parseError)) {
    throw new Error("Invalid Gherkin.");
  }
  return document;
}

function stripAt(tag: string): string {
  return tag.startsWith("@") ? tag.slice(1) : tag;
}

function enumSelections(document: ReturnType<typeof parseDocument>): Record<string, string> {
  const feature = document.feature;
  if (!feature) throw new Error("Invalid Gherkin.");
  const featureLine = feature.location.line;
  const firstTagLine = feature.tags[0]?.location.line ?? featureLine;
  const cutoff = Math.min(featureLine, firstTagLine);
  const selections: Record<string, string> = {};

  for (const comment of document.comments) {
    if (comment.location.line >= cutoff) continue;
    const match = ENUM_DIRECTIVE_RE.exec(comment.text.trim());
    if (!match) continue;
    const [, kind, key] = match;
    if (!ENUM_KIND_RE.test(kind) || !ENUM_KEY_RE.test(key) || kind in selections) {
      throw new Error("Invalid enum directive.");
    }
    selections[kind] = key;
  }
  return selections;
}

async function readEnumVocabulary(root: string, project: string): Promise<EnumVocabulary> {
  try {
    return parseEnumVocabulary(await readUtf8File(resolve(root, project, "enums.yaml")));
  } catch {
    return {};
  }
}

function parseFeatureSummary(
  fileName: string,
  source: string,
  vocabulary: Record<string, Record<string, string>>,
): FeatureSummary {
  const document = parseDocument(source);
  const feature = document.feature;
  if (!feature || feature.children.some((child) => child.rule)) throw new Error("Invalid Gherkin.");
  const scenarios = feature.children.flatMap((child) => (child.scenario ? [child.scenario] : []));
  if (scenarios.length > 1) throw new Error("Invalid Gherkin.");
  const scenario = scenarios[0];
  const tags = [...feature.tags, ...(scenario?.tags ?? [])].map((tag) => stripAt(tag.name));
  const selections = enumSelections(document);
  const enums = Object.entries(selections)
    .filter(([, key]) => key)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([kind, key]) => {
      const label = vocabulary[kind]?.[key] ?? "";
      return { kind, key, label: label === key ? "" : label };
    });

  return {
    file_name: fileName,
    description: (feature.description ? `${feature.name}\n${feature.description}` : feature.name).replace(/\\n/g, "\n"),
    scenario_name: scenario?.name ?? "",
    tags: [...new Set(tags)],
    enums,
  };
}

async function featureSummary(
  path: string,
  fileName: string,
  vocabulary: Record<string, Record<string, string>>,
): Promise<FeatureSummary> {
  try {
    return parseFeatureSummary(fileName, await readUtf8File(path), vocabulary);
  } catch {
    return { file_name: fileName, description: "", scenario_name: "", tags: [], enums: [] };
  }
}

export async function listFolder(root: string, segments: string[]): Promise<FolderListing> {
  validateLogicalSegments(segments);
  if (segments.length === 0) {
    try {
      const entries = await readdir(root, { withFileTypes: true });
      return {
        kind: "root",
        projects: entries.filter((entry) => entry.isDirectory() && !TEMP_FILE_RE.test(entry.name)).map((entry) => entry.name),
      };
    } catch (error: unknown) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return { kind: "root", projects: [] };
      throw error;
    }
  }
  if (segments.length > MAX_FOLDER_DEPTH) {
    throw new PathValidationError(`list_folder only supports paths up to depth ${MAX_FOLDER_DEPTH}; got depth ${segments.length}.`);
  }

  const target = resolve(root, ...segments);
  try {
    if (!(await stat(target)).isDirectory()) throw new FolderNotFoundError(`Folder not found: ${target}`);
  } catch (error: unknown) {
    if (error instanceof FolderNotFoundError) throw error;
    if ((error as NodeJS.ErrnoException).code === "ENOENT") throw new FolderNotFoundError(`Folder not found: ${target}`);
    throw error;
  }
  const entries = await readdir(target, { withFileTypes: true });

  if (segments.length === 1) {
    return {
      kind: "project",
      modules: entries
        .filter((entry) => entry.isDirectory() && !TEMP_FILE_RE.test(entry.name) && !RESERVED_TYPED_AREAS.has(entry.name))
        .map((entry) => entry.name),
    };
  }

  const vocabulary = await readEnumVocabulary(root, segments[0]);
  const folders: string[] = [];
  const features: FeatureSummary[] = [];
  for (const entry of entries) {
    if (TEMP_FILE_RE.test(entry.name)) continue;
    if (entry.isDirectory()) {
      folders.push(entry.name);
      continue;
    }
    if (entry.isFile() && FEATURE_FILE_RE.test(entry.name)) {
      features.push(await featureSummary(resolve(target, entry.name), entry.name, vocabulary));
    }
  }
  return { kind: segments.length === 2 ? "module" : "subfolder", folders, features };
}
