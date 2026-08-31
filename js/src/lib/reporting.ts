import { readdir } from "node:fs/promises";
import { relative, resolve } from "node:path";
import { readProjectEnums, type EnumVocabulary } from "./enums";
import { parseFeature, type FeaturePayload } from "./feature";
import { resolveDataRoot } from "./data-root";
import { readRun, type TestRun } from "./run-storage";
import type { Report } from "./report";
import { readUtf8File } from "./utf8";
import { validateLogicalSegments } from "./path";

const UNSET = "(unset)", REMOVED = "(removed)", UNTAGGED = "(untagged)", ABSENT = "—";
type LoadedRun = { path: string; run: TestRun };

async function featureFiles(directory: string): Promise<string[]> {
  const out: string[] = [];
  const entries = await readdir(directory, { withFileTypes: true }).catch((error: unknown) => { if ((error as NodeJS.ErrnoException).code === "ENOENT") return []; throw error; });
  for (const entry of entries) { const path = resolve(directory, entry.name); if (entry.isDirectory()) out.push(...await featureFiles(path)); else if (entry.isFile() && entry.name.toLowerCase().endsWith(".feature")) out.push(path); }
  return out;
}

async function orderedRuns(report: Report): Promise<{ runs: LoadedRun[]; warnings: string[] }> {
  const runs: LoadedRun[] = [], warnings: string[] = [];
  for (const path of report.run_paths) {
    const parts = path.split("/");
    if (parts.length !== 4 || parts[1] !== "test-run") { warnings.push(`Ignored malformed run path: ${path}`); continue; }
    try { runs.push({ path, run: await readRun(parts[0], parts[2], parts[3]) }); } catch { warnings.push(`Run not found or unreadable: ${path}`); }
  }
  runs.sort((left, right) => left.run.created_at.localeCompare(right.run.created_at) || left.path.localeCompare(right.path));
  return { runs, warnings };
}

async function featureAt(path: string): Promise<FeaturePayload | undefined> { try { const parts = path.split("/"); validateLogicalSegments(parts); return parseFeature(await readUtf8File(resolve(resolveDataRoot(), ...parts))); } catch { return undefined; } }
function tags(feature: FeaturePayload): Set<string> { return new Set([...feature.tags, ...feature.scenario.tags]); }
function params(report: Report) { return { status: report.status, kind: report.kind, tag: report.tag, scope: report.scope, case_path: report.case_path }; }
function envelope(report: Report, total: number, extra: Record<string, unknown> = {}) { return { type: report.type, title: report.title, created_at: report.created_at, total, buckets: [], trend: [], warnings: [], params: params(report), ...extra }; }
type ReportGroup = { value: string; label: string; synthetic: boolean; cases: unknown[]; count?: number; pct?: number };
function finalize(groups: Map<string, ReportGroup>, total: number) {
  for (const group of groups.values()) { group.count = group.cases.length; group.pct = total ? group.count / total : 0; }
  const synthetic = new Map([[UNSET, 0], [UNTAGGED, 1], [REMOVED, 2]]);
  return [...groups.values()].sort((a, b) => (a.synthetic ? 1 : 0) - (b.synthetic ? 1 : 0) || (a.synthetic ? synthetic.get(a.value)! - synthetic.get(b.value)! : (b.count as number) - (a.count as number) || a.label.localeCompare(b.label)));
}

export async function computeReport(project: string, report: Report): Promise<Record<string, unknown>> {
  const { runs, warnings } = await orderedRuns(report);
  const qualifying: string[] = [], seen = new Set<string>();
  for (const { run } of runs) for (const result of run.results) if ((report.type === "enum_ranking" || report.type === "tag_ranking") && result.result === report.status && !seen.has(result.file_path)) { seen.add(result.file_path); qualifying.push(result.file_path); }
  const total = report.type === "enum_ranking" || report.type === "tag_ranking" ? qualifying.length : 0;
  if (report.type === "case_trend") {
    const trend = runs.map(({ path, run }) => ({ run: path.split("/").at(-1), run_name: run.name, run_path: path, created_at: run.created_at, result: run.results.find((item) => item.file_path === report.case_path)?.result ?? ABSENT }));
    const feature = await featureAt(report.case_path);
    return envelope(report, trend.length, { trend, warnings, tombstoned: !feature, current_enums: feature?.enums ?? {}, current_tags: feature ? [...tags(feature)].sort() : [] });
  }
  if (report.type === "tag_inventory") {
    const carrying: unknown[] = [], missing: unknown[] = [];
    let scopePaths: string[] = [];
    try { const scope = report.scope.split("/").filter(Boolean); validateLogicalSegments(scope); scopePaths = await featureFiles(resolve(resolveDataRoot(), ...scope)); } catch { warnings.push(`Scope folder not found: ${report.scope}`); }
    let vocabulary: EnumVocabulary = {}; try { vocabulary = await readProjectEnums(resolve(resolveDataRoot(), project, "enums.yaml")); } catch { /* display keys when enum storage is unavailable */ }
    for (const absolute of scopePaths) { const path = relative(resolveDataRoot(), absolute).split("\\").join("/"); const feature = await featureAt(path); if (!feature) { warnings.push(`Unreadable feature skipped: ${path}`); continue; } const item = { file_path: path, scenario_name: feature.scenario.name, enums: Object.entries(feature.enums).filter(([, key]) => key).map(([kind, key]) => ({ kind, key, label: vocabulary[kind]?.[key] === key ? "" : vocabulary[kind]?.[key] ?? "" })) }; (tags(feature).has(report.tag) ? carrying : missing).push(item); }
    const inventoryTotal = carrying.length + missing.length;
    return envelope(report, inventoryTotal, { buckets: [{ value: "carrying", label: `carrying @${report.tag}`, synthetic: false, count: carrying.length, pct: inventoryTotal ? carrying.length / inventoryTotal : 0, cases: carrying }, { value: "not_carrying", label: "not carrying", synthetic: false, count: missing.length, pct: inventoryTotal ? missing.length / inventoryTotal : 0, cases: missing }], warnings });
  }
  let vocabulary: EnumVocabulary = {}; try { vocabulary = await readProjectEnums(resolve(resolveDataRoot(), project, "enums.yaml")); } catch { warnings.push("Project enums.yaml is missing or unreadable."); }
  const groups = new Map<string, ReportGroup>();
  for (const path of qualifying) {
    const feature = await featureAt(path);
    if (!feature) { const group = groups.get(REMOVED) ?? { value: REMOVED, label: REMOVED, synthetic: true, cases: [] }; group.cases.push({ file_path: path, scenario_name: "", ...(report.type === "tag_ranking" ? { enums: [] } : { tags: [] }) }); groups.set(REMOVED, group); continue; }
    const detail = { file_path: path, scenario_name: feature.scenario.name, ...(report.type === "tag_ranking" ? { enums: Object.entries(feature.enums).filter(([, key]) => key).map(([kind, key]) => ({ kind, key, label: vocabulary[kind]?.[key] === key ? "" : vocabulary[kind]?.[key] ?? "" })) } : { tags: [...tags(feature)].sort() }) };
    const values = report.type === "enum_ranking" ? [feature.enums[report.kind] || UNSET] : [...tags(feature)];
    if (!values.length) values.push(UNTAGGED);
    for (const value of values) { const synthetic = value === UNSET || value === UNTAGGED; const group = groups.get(value) ?? { value, label: report.type === "enum_ranking" ? vocabulary[report.kind]?.[value] ?? value : value, synthetic, cases: [] }; group.cases.push(detail); groups.set(value, group); }
  }
  return envelope(report, total, { buckets: finalize(groups, total), warnings });
}
