import { NextResponse } from "next/server";
import { defaultMethodNotAllowed } from "../../../src/lib/http-errors";
import { renderUiFragment, uiErrorHtml, UI_HTML_HEADERS } from "../../../src/lib/ui-html";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function navigationTarget(request: Request, parts: string[]): URL {
  const target = new URL("/", request.url);
  const [route, ...rest] = parts;
  const activeTab = route === "run" || route === "test-run-tree" || (route === "folder" && rest[1] === "test-run") ? "runs" : route === "report" || route === "reports-tree" || (route === "folder" && rest[1] === "report") ? "reports" : route === "enums" || route === "enums-tree" ? "enums" : "directory";
  target.searchParams.set("tab", activeTab);
  if (activeTab === "directory" && route === "folder" && rest.length) target.searchParams.set("path", rest.join("/"));
  if (activeTab === "directory" && route === "file" && rest.length) target.searchParams.set("path", rest.join("/"));
  if (route === "search") {
    const source = new URL(request.url).searchParams;
    for (const key of ["q", "scope", "match", "case"]) {
      const value = source.get(key);
      if (value !== null) target.searchParams.set(key, value);
    }
  }
  if ((activeTab === "runs" || activeTab === "reports" || activeTab === "enums") && (route === "run" || route === "report" || route === "enums") && rest.length) target.searchParams.set("project", rest[0]);
  if (route === "run" && rest.length >= 3) target.searchParams.set("run", `${rest[1]}/${rest.slice(2).join("/")}`);
  if (route === "report" && rest.length >= 2) target.searchParams.set("report", rest.slice(1).join("/"));
  return target;
}

function shellResponse(request: Request, parts: string[]): Response {
  // Return a complete, valid HTML bridge instead of proxying a rendered Next
  // document. Re-serving Next's document at a different route confuses the
  // App Router bootstrap; the bridge transfers the browser to the real shell
  // URL with the view encoded in its query state.
  const target = navigationTarget(request, parts);
  const targetPath = `${target.pathname}${target.search}`;
  const scriptTarget = JSON.stringify(targetPath);
  return new NextResponse(`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>TMS</title><meta http-equiv="refresh" content="0;url=${targetPath}"></head><body><main><h1>TMS</h1><p>Opening workspace…</p><p><a href="${targetPath}">Continue to workspace</a></p></main><script>window.location.replace(${scriptTarget});</script></body></html>`, { status: 200, headers: UI_HTML_HEADERS });
}

export async function GET(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path = [] } = await context.params;
  if (!request.headers.get("HX-Request") && request.headers.get("Sec-Fetch-Mode") === "navigate") {
    try { return shellResponse(request, path); }
    catch (error) { const result = uiErrorHtml(error); return new NextResponse(result.body, { status: result.status, headers: UI_HTML_HEADERS }); }
  }
  try {
    return new NextResponse(await renderUiFragment(path, new URL(request.url).searchParams), { status: 200, headers: UI_HTML_HEADERS });
  } catch (error) {
    const result = uiErrorHtml(error);
    return new NextResponse(result.body, { status: result.status, headers: UI_HTML_HEADERS });
  }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
export const HEAD = defaultMethodNotAllowed;
