import { readdir } from "node:fs/promises";
import { relative, sep } from "node:path";

import {
  generateMessages,
} from "@cucumber/gherkin";
import { IdGenerator, SourceMediaType } from "@cucumber/messages";

import { readUtf8File } from "./utf8";

export type CaseCounts = {
  total: number;
  auto: number;
  non_auto: number;
};

type FolderNode = {
  type: "folder";
  name: string;
  depth: number;
  path: string;
  children: TreeNode[];
  counts: CaseCounts;
};

type FileNode = {
  type: "feature" | "other";
  name: string;
  path: string;
};

export type TreeNode = FolderNode | FileNode;

export type Tree = {
  name: "";
  children: TreeNode[];
};

const TEMP_FILE_RE = /.+\.tmp\.\d+\.[0-9a-f]+$/;
const FEATURE_FILE_RE = /\.feature$/i;
const RESERVED_TYPED_AREAS = new Set(["test-run", "report"]);

function emptyCounts(): CaseCounts {
  return { total: 0, auto: 0, non_auto: 0 };
}

function mergeCounts(target: CaseCounts, source: CaseCounts): void {
  target.total += source.total;
  target.auto += source.auto;
  target.non_auto += source.non_auto;
}

function isFeatureName(name: string): boolean {
  return FEATURE_FILE_RE.test(name);
}

function isAuto(tags: readonly { name: string }[]): boolean {
  return tags.some((tag) => tag.name.slice(1).toLocaleLowerCase() === "auto");
}

function featureCounts(source: string): CaseCounts {
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
    return { total: 1, auto: 0, non_auto: 1 };
  }

  if (document.feature.children.some((child) => child.rule)) {
    return { total: 1, auto: 0, non_auto: 1 };
  }

  const scenarios = document.feature.children.flatMap((child) =>
    child.scenario ? [child.scenario] : [],
  );
  if (scenarios.length === 0) {
    return { total: 1, auto: 0, non_auto: 1 };
  }

  const auto = isAuto(document.feature.tags)
    ? scenarios.length
    : scenarios.filter((scenario) => isAuto(scenario.tags)).length;
  return { total: scenarios.length, auto, non_auto: scenarios.length - auto };
}

function relativePosix(root: string, target: string): string {
  return relative(root, target).split(sep).join("/");
}

async function countFeature(path: string): Promise<CaseCounts> {
  try {
    return featureCounts(await readUtf8File(path));
  } catch {
    return { total: 1, auto: 0, non_auto: 1 };
  }
}

async function walk(
  root: string,
  directory: string,
  depth: number,
): Promise<{ children: TreeNode[]; counts: CaseCounts }> {
  const counts = emptyCounts();
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error: unknown) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return { children: [], counts };
    }
    throw error;
  }

  const children: TreeNode[] = [];
  for (const entry of entries) {
    if (TEMP_FILE_RE.test(entry.name)) {
      continue;
    }
    if (depth === 1 && RESERVED_TYPED_AREAS.has(entry.name)) {
      continue;
    }
    if (depth === 1 && entry.isFile() && entry.name === "enums.yaml") {
      continue;
    }

    const fullPath = `${directory}/${entry.name}`;
    const path = relativePosix(root, fullPath);
    if (entry.isDirectory()) {
      const nested = await walk(root, fullPath, depth + 1);
      children.push({
        type: "folder",
        name: entry.name,
        depth,
        path,
        children: nested.children,
        counts: nested.counts,
      });
      mergeCounts(counts, nested.counts);
      continue;
    }
    if (!entry.isFile()) {
      continue;
    }

    const type = isFeatureName(entry.name) ? "feature" : "other";
    children.push({ type, name: entry.name, path });
    if (type === "feature") {
      mergeCounts(counts, await countFeature(fullPath));
    }
  }

  children.sort((left, right) => Number(left.type !== "folder") - Number(right.type !== "folder"));
  return { children, counts };
}

export async function listTree(root: string): Promise<Tree> {
  const tree = await walk(root, root, 0);
  return { name: "", children: tree.children };
}
