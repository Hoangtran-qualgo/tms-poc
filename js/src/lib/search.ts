import { readdir } from "node:fs/promises";
import { relative, resolve, sep } from "node:path";

import { parseFeature } from "./feature";
import { PathValidationError, validateLogicalSegments } from "./path";
import { readUtf8File } from "./utf8";

const TEMP_FILE_RE = /.+\.tmp\.\d+\.[0-9a-f]+$/;
const FEATURE_FILE_RE = /\.feature$/i;

export type SearchHit = {
  file_path: string;
  description: string;
  scenario_name: string;
  matched_field: "description" | "tag";
  match_value: string;
};

function scopeSegments(scope: string): string[] {
  if (scope === "" || scope === "all") return [];
  if (scope.startsWith("project:")) {
    const name = scope.slice("project:".length);
    if (!name || name.includes("/")) throw new PathValidationError(`project scope must be 'project:<name>', got '${scope}'`);
    return [name];
  }
  if (scope.startsWith("module:")) {
    const parts = scope.slice("module:".length).split("/").filter(Boolean);
    if (parts.length !== 2) throw new PathValidationError(`module scope must be 'module:<proj>/<mod>', got '${scope}'`);
    return parts;
  }
  throw new PathValidationError(`Invalid scope: '${scope}'. Must be 'all', 'project:<name>', or 'module:<proj>/<mod>'.`);
}

async function featurePaths(root: string, directory: string): Promise<string[]> {
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error: unknown) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw error;
  }
  const paths: string[] = [];
  for (const entry of entries) {
    if (TEMP_FILE_RE.test(entry.name)) continue;
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) paths.push(...await featurePaths(root, path));
    else if (entry.isFile() && FEATURE_FILE_RE.test(entry.name)) paths.push(path);
  }
  return paths;
}

export async function searchFeatures(root: string, query: string, scope = "all", match = "text", caseSensitive = false): Promise<SearchHit[]> {
  if (!query || !query.trim()) return [];
  if (match !== "text" && match !== "tag") throw new PathValidationError(`Invalid match mode: ${match}. Must be 'text' or 'tag'.`);
  const segments = scopeSegments(scope);
  validateLogicalSegments(segments);
  const base = resolve(root, ...segments);
  const needle = caseSensitive ? query : query.toLowerCase();
  const hits: SearchHit[] = [];
  for (const path of await featurePaths(root, base)) {
    try {
      const feature = parseFeature(await readUtf8File(path));
      const file_path = relative(root, path).split(sep).join("/");
      if (match === "text") {
        const description = caseSensitive ? feature.description : feature.description.toLowerCase();
        const name = caseSensitive ? feature.scenario.name : feature.scenario.name.toLowerCase();
        if (description.includes(needle) || name.includes(needle)) {
          hits.push({ file_path, description: feature.description, scenario_name: feature.scenario.name, matched_field: "description", match_value: query });
        }
      } else {
        for (const tag of [...new Set([...feature.tags, ...feature.scenario.tags])]) {
          if ((caseSensitive ? tag : tag.toLowerCase()).includes(needle)) {
            hits.push({ file_path, description: feature.description, scenario_name: feature.scenario.name, matched_field: "tag", match_value: tag });
          }
        }
      }
    } catch {
      // Best-effort search intentionally skips malformed, non-UTF-8, and unreadable features.
    }
  }
  return hits;
}
