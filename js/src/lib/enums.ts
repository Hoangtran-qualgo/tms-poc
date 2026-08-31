import { readUtf8File } from "./utf8";

import { parse as parseYaml, stringify as stringifyYaml } from "yaml";

const ENUM_KIND_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
const ENUM_KEY_RE = /^[A-Za-z_][A-Za-z0-9_-]*$/;

export type EnumVocabulary = Record<string, Record<string, string>>;

export class EnumsParseError extends Error {
  constructor(
    message: string,
    readonly line = 0,
    readonly column = 0,
  ) {
    super(message);
  }
}

export class EnumInUseError extends Error {
  constructor(
    readonly kind: string,
    readonly key: string,
    readonly count: number,
    readonly sample: string[],
    message: string,
  ) {
    super(message);
  }
}

type YamlErrorWithPosition = Error & { linePos?: Array<{ line: number; col: number }> };

function parseError(error: unknown): EnumsParseError {
  const yamlError = error as YamlErrorWithPosition;
  const position = yamlError.linePos?.[0];
  return new EnumsParseError(yamlError.message || String(error), position?.line ?? 0, position?.col ?? 0);
}

export function parseEnumVocabulary(source: string): EnumVocabulary {
  let payload: unknown;
  try {
    payload = parseYaml(source);
  } catch (error) {
    throw parseError(error);
  }
  if (payload === null || payload === undefined) return {};
  if (typeof payload !== "object" || Array.isArray(payload)) {
    throw new EnumsParseError(`enums.yaml root must be a YAML mapping; got ${Array.isArray(payload) ? "list" : typeof payload}.`);
  }

  const vocabulary: EnumVocabulary = {};
  for (const [kind, entries] of Object.entries(payload)) {
    if (!ENUM_KIND_RE.test(kind)) {
      throw new EnumsParseError(`Invalid enum kind name '${kind}'; kinds must match ${ENUM_KIND_RE.source}.`);
    }
    if (entries === null) {
      vocabulary[kind] = {};
      continue;
    }
    if (!Array.isArray(entries)) {
      throw new EnumsParseError(`Value under kind '${kind}' must be a list of single-key mappings (- <key>: <label>); got ${typeof entries}.`);
    }
    const values: Record<string, string> = {};
    for (const [index, entry] of entries.entries()) {
      if (typeof entry !== "object" || entry === null || Array.isArray(entry)) {
        throw new EnumsParseError(`Element ${index} under kind '${kind}' must be a single-key mapping (- <key>: <label>).`);
      }
      const pairs = Object.entries(entry);
      if (pairs.length !== 1) {
        throw new EnumsParseError(`Element ${index} under kind '${kind}' must be a single-key mapping (- <key>: <label>).`);
      }
      const [key, label] = pairs[0];
      if (!ENUM_KEY_RE.test(key)) {
        throw new EnumsParseError(`Invalid enum key '${key}' under kind '${kind}'; keys must match ${ENUM_KEY_RE.source}.`);
      }
      if (key in values) throw new EnumsParseError(`Duplicate enum key '${key}' under kind '${kind}'.`);
      if (typeof label !== "string") {
        throw new EnumsParseError(`Label for key '${key}' under kind '${kind}' must be a string; got ${typeof label}.`);
      }
      if (!label) throw new EnumsParseError(`Label for key '${key}' under kind '${kind}' must be non-empty.`);
      if (label.includes("\n")) throw new EnumsParseError(`Label for key '${key}' under kind '${kind}' must be single-line.`);
      values[key] = label;
    }
    vocabulary[kind] = values;
  }
  return vocabulary;
}

export async function readProjectEnums(path: string): Promise<EnumVocabulary> {
  return parseEnumVocabulary(await readUtf8File(path));
}

export function serializeEnumVocabulary(vocabulary: EnumVocabulary): string {
  const document = Object.fromEntries(Object.entries(vocabulary).map(([kind, entries]) => [kind, Object.entries(entries).map(([key, label]) => ({ [key]: label }))]));
  const text = stringifyYaml(document);
  parseEnumVocabulary(text);
  return text;
}
