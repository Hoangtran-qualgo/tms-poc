import { resolve } from "node:path";

export function resolveDataRoot(
  workspaceRoot = process.cwd(),
  configuredRoot = process.env.TMS_DATA_ROOT,
): string {
  return configuredRoot
    ? resolve(workspaceRoot, configuredRoot)
    : resolve(workspaceRoot, "..", "project");
}
