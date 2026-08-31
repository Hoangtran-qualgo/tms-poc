import { readFile } from "node:fs/promises";

const decoder = new TextDecoder("utf-8", { fatal: true });

export async function readUtf8File(path: string): Promise<string> {
  return decoder.decode(await readFile(path));
}
