import { ensureWatcher, subscribeChange } from "../../../src/lib/events";
import { defaultMethodNotAllowed } from "../../../src/lib/http-errors";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  ensureWatcher();
  let cleanup: (() => void) | undefined;
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const encoder = new TextEncoder();
      const send = (value: string) => { try { controller.enqueue(encoder.encode(value)); } catch { /* client disconnected */ } };
      send(": connected\n\n");
      const unsubscribe = subscribeChange(() => send("event: change\ndata:\n\n"));
      const heartbeat = setInterval(() => send(": heartbeat\n\n"), 15_000);
      cleanup = () => { unsubscribe(); clearInterval(heartbeat); };
    },
    cancel() { cleanup?.(); },
  });
  return new Response(stream, { headers: { "content-type": "text/event-stream", "cache-control": "no-cache", connection: "keep-alive" } });
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
