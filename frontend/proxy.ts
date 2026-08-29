import { NextRequest, NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  ACCESS_TOKEN_MAX_AGE,
  REFRESH_COOKIE,
  REFRESH_TOKEN_MAX_AGE,
  cookieOptions,
  isExpiringSoon,
} from "@/lib/session";

const PROTECTED_PREFIXES = ["/projects"];
const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

// UX fast path only -- see the comment on requireSession in src/lib/api.ts for why
// this isn't the actual security boundary.
export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  if (!isProtected) {
    return NextResponse.next();
  }

  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;

  if (!accessToken && !refreshToken) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (accessToken && !isExpiringSoon(accessToken)) {
    return NextResponse.next();
  }

  if (!refreshToken) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const refreshed = await refreshTokens(refreshToken);
  if (!refreshed) {
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete(ACCESS_COOKIE);
    response.cookies.delete(REFRESH_COOKIE);
    return response;
  }

  const response = NextResponse.next();
  response.cookies.set(ACCESS_COOKIE, refreshed.access_token, cookieOptions(ACCESS_TOKEN_MAX_AGE));
  response.cookies.set(REFRESH_COOKIE, refreshed.refresh_token, cookieOptions(REFRESH_TOKEN_MAX_AGE));
  return response;
}

async function refreshTokens(
  refreshToken: string,
): Promise<{ access_token: string; refresh_token: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export const config = {
  matcher: ["/projects/:path*"],
};
