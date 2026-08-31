import { NextResponse } from "next/server";

import { resolveDataRoot } from "../../../src/lib/data-root";
import { listTree } from "../../../src/lib/tree";
import { defaultMethodNotAllowed } from "../../../src/lib/http-errors";

export const runtime = "nodejs";

export async function GET() {
  try {
    return NextResponse.json(await listTree(resolveDataRoot()));
  } catch (error) {
    console.error("Unexpected error in API handler", error);
    return NextResponse.json(
      { error: { code: "internal_error", message: "An unexpected error occurred." } },
      { status: 500 },
    );
  }
}

export const POST = defaultMethodNotAllowed;
export const PUT = defaultMethodNotAllowed;
export const PATCH = defaultMethodNotAllowed;
export const DELETE = defaultMethodNotAllowed;
