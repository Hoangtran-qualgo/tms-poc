const CALL_RE = /d\(\s*'([^']+)'\s*,\s*'([^']*)'\s*\)/g;

export type ParsedScenario = { name: string; result: string };
export type ParsedReport = { report_name: string; created_at: string; scenarios: ParsedScenario[] };

export class AllureParseError extends Error {}

function decodeJson(blobs: Map<string, string>, key: string, required: boolean): unknown {
  const encoded = blobs.get(key);
  if (!encoded) { if (required) throw new AllureParseError(`Unsupported report format: missing '${key}'.`); return undefined; }
  if (!/^[A-Za-z0-9+/]*={0,2}$/.test(encoded) || encoded.length % 4 === 1) { if (required) throw new AllureParseError(`Malformed report: could not decode '${key}'.`); return undefined; }
  try { return JSON.parse(Buffer.from(encoded, "base64").toString("utf8")); }
  catch (error) { if (required) throw new AllureParseError(`Malformed report: could not decode '${key}': ${(error as Error).message}`); return undefined; }
}

function leaves(node: unknown): Array<Record<string, unknown>> {
  const out: Array<Record<string, unknown>> = [];
  const walk = (value: unknown) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return;
    const record = value as Record<string, unknown>;
    if (!("children" in record)) { if (typeof record.name === "string" && record.name) out.push(record); return; }
    if (Array.isArray(record.children)) for (const child of record.children) walk(child);
  };
  walk(node);
  return out;
}

function timeValue(leaf: Record<string, unknown>, key: string): number | undefined {
  const time = leaf.time;
  if (!time || typeof time !== "object" || Array.isArray(time)) return undefined;
  const value = (time as Record<string, unknown>)[key];
  return typeof value === "number" ? value : undefined;
}

function isoFromEpochMs(value: number): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new AllureParseError("Malformed report: invalid created time.");
  return date.toISOString().replace(/\.\d{3}Z$/, "+00:00");
}

export function parseAllureReport(html: string): ParsedReport {
  if (typeof html !== "string") throw new AllureParseError("Report must be a string.");
  const blobs = new Map<string, string>();
  for (const match of html.matchAll(CALL_RE)) blobs.set(match[1], match[2]);
  if (!blobs.size) throw new AllureParseError("Unsupported report format: no Allure embedded-data calls found.");
  const suiteData = decodeJson(blobs, "data/suites.json", true);
  const reportLeaves = leaves(suiteData);
  const summary = decodeJson(blobs, "widgets/summary.json", false);
  let start: number | undefined;
  if (summary && typeof summary === "object" && !Array.isArray(summary)) {
    const time = (summary as Record<string, unknown>).time;
    if (time && typeof time === "object" && !Array.isArray(time) && typeof (time as Record<string, unknown>).start === "number") start = (time as Record<string, number>).start;
  }
  if (start === undefined) {
    const starts = reportLeaves.map((leaf) => timeValue(leaf, "start")).filter((value): value is number => value !== undefined);
    if (starts.length) start = Math.min(...starts);
  }
  if (start === undefined) throw new AllureParseError("Malformed report: no created time (summary.time.start or leaf time.start).");
  const name = summary && typeof summary === "object" && !Array.isArray(summary) && typeof (summary as Record<string, unknown>).reportName === "string" && String((summary as Record<string, unknown>).reportName).trim() ? String((summary as Record<string, unknown>).reportName) : "Allure Report";
  const firstIndex = new Map<string, number>();
  const chosen = new Map<string, { stopPresent: boolean; stop: number; index: number; leaf: Record<string, unknown> }>();
  for (const [index, leaf] of reportLeaves.entries()) {
    const scenarioName = String(leaf.name);
    const key = scenarioName.toLowerCase();
    if (!firstIndex.has(key)) firstIndex.set(key, index);
    const stop = timeValue(leaf, "stop");
    const candidate = { stopPresent: stop !== undefined, stop: stop ?? 0, index, leaf };
    const previous = chosen.get(key);
    if (!previous || Number(candidate.stopPresent) > Number(previous.stopPresent) || (candidate.stopPresent === previous.stopPresent && (candidate.stop > previous.stop || (candidate.stop === previous.stop && candidate.index >= previous.index)))) chosen.set(key, candidate);
  }
  const status = (value: unknown) => ({ passed: "PASSED", failed: "FAILED", broken: "FAILED", skipped: "SKIPPED", unknown: "SKIPPED" }[typeof value === "string" ? value.toLowerCase() : ""] ?? "SKIPPED");
  const scenarios = [...chosen.entries()].sort((a, b) => firstIndex.get(a[0])! - firstIndex.get(b[0])!).map(([, entry]) => ({ name: String(entry.leaf.name), result: status(entry.leaf.status) }));
  return { report_name: name, created_at: isoFromEpochMs(start), scenarios };
}

const EXAMPLE_SUFFIX_RE = /\s+--\s+@(\d+)\.(\d+)\s*$/;
export function splitExampleSuffix(name: string): [string, { table: number; row: number } | undefined] {
  const match = EXAMPLE_SUFFIX_RE.exec(name);
  if (!match) return [name.trim(), undefined];
  return [name.slice(0, match.index).trim(), { table: Number(match[1]), row: Number(match[2]) }];
}
