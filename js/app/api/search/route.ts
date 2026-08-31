import { NextResponse } from "next/server";

import { resolveDataRoot } from "../../../src/lib/data-root";
import { PathValidationError } from "../../../src/lib/path";
import { searchFeatures } from "../../../src/lib/search";
import { defaultMethodNotAllowed } from "../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  try {
    const hits = await searchFeatures(
      resolveDataRoot(), searchParams.get("q") ?? "", searchParams.get("scope") ?? "all",
      searchParams.get("match") ?? "text", ["true", "1", "yes"].includes((searchParams.get("case") ?? "false").toLowerCase()),
    );
    return NextResponse.json({ hits });
  } catch (error) {
    if (error instanceof PathValidationError) {
      return NextResponse.json({ error: { code: "bad_request", message: error.message } }, { status: 400 });
    }
    console.error("Unexpected error in API handler", error);
    return NextResponse.json({ error: { code: "internal_error", message: "An unexpected error occurred." } }, { status: 500 });
  }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
