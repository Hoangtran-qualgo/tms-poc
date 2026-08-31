import { link, open, rename, unlink } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { markWrite } from "./events";

export async function atomicWriteUtf8(target: string, text: string): Promise<void> {
  const temporary = `${target}.tmp.${process.pid}.${randomUUID().replaceAll("-", "")}`;
  let handle;
  try {
    handle = await open(temporary, "wx");
    await handle.writeFile(text, "utf8");
    await handle.sync();
    await handle.close();
    handle = undefined;
    await rename(temporary, target);
    markWrite(target);
  } catch (error) {
    await handle?.close();
    await unlink(temporary).catch(() => undefined);
    throw error;
  }
}

export async function atomicCreateUtf8(target: string, text: string): Promise<void> {
  const temporary = `${target}.tmp.${process.pid}.${randomUUID().replaceAll("-", "")}`;
  let handle;
  try {
    handle = await open(temporary, "wx");
    await handle.writeFile(text, "utf8");
    await handle.sync();
    await handle.close();
    handle = undefined;
    await link(temporary, target);
    markWrite(target);
  } catch (error) {
    await handle?.close();
    throw error;
  } finally {
    await unlink(temporary).catch(() => undefined);
  }
}
