import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { describe, expect, it } from "vitest";

import { parseFeature } from "../src/lib/feature";

const repositoryRoot = resolve(process.cwd(), "..");
const python = resolve(repositoryRoot, ".venv/bin/python");

const source = [
  "# enum.component: web",
  "@smoke",
  "Feature: Login\\nflow",
  "  Background:",
  "    Given a configured browser",
  "",
  "  @critical",
  "  Scenario: valid credentials",
  "    When the user submits:",
  "      | username | password |",
  "      | alice    | secret   |",
  "    Then access is granted",
  "",
].join("\n");

describe("Python feature-model differential", () => {
  it.skipIf(!existsSync(python))("matches Python parse_feature wire shape for a representative feature", () => {
    const result = spawnSync(
      python,
      ["-c", "import json,sys; from app.gherkin_io import parse_feature; print(json.dumps(parse_feature(sys.stdin.read()).to_dict(), sort_keys=True))"],
      { cwd: repositoryRoot, env: { ...process.env, PYTHONPATH: repositoryRoot }, input: source, encoding: "utf8" },
    );
    expect(result.status, result.stderr).toBe(0);
    expect(JSON.parse(result.stdout)).toEqual(parseFeature(source));
  });
});
