import { watch, type FSWatcher } from "node:fs";
import { dirname, resolve } from "node:path";
import { resolveDataRoot } from "./data-root";

type Listener = () => void;
const listeners = new Set<Listener>();
const recentWrites = new Map<string, number>();
const watchers = new Map<string, FSWatcher>();
const TTL_MS = 500;

export function markWrite(path: string): void {
  const now = Date.now();
  recentWrites.set(resolve(path), now);
  recentWrites.set(dirname(resolve(path)), now);
}

function wasRecent(path: string): boolean {
  const at = recentWrites.get(resolve(path));
  if (at === undefined) return false;
  if (Date.now() - at > TTL_MS) { recentWrites.delete(resolve(path)); return false; }
  return true;
}

export function subscribeChange(listener: Listener): () => void { listeners.add(listener); return () => listeners.delete(listener); }
export function publishChange(): void { for (const listener of listeners) listener(); }

export function ensureWatcher(): void {
  const root = resolveDataRoot();
  if (watchers.has(root)) return;
  try {
    const watcher = watch(root, { recursive: true }, (_event, filename) => { if (!filename || !wasRecent(resolve(root, filename.toString()))) publishChange(); });
    watcher.on("error", () => { /* best-effort live refresh, never request-fatal */ });
    watchers.set(root, watcher);
  } catch { /* unsupported recursive watchers are a live-refresh limitation */ }
}
