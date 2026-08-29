import "server-only";

export const ACCESS_COOKIE = "gb_access_token";
export const REFRESH_COOKIE = "gb_refresh_token";
export const ACCESS_TOKEN_MAX_AGE = 15 * 60;
export const REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60;

export function cookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge: maxAgeSeconds,
  };
}

interface AccessClaims {
  sub: string;
  role: "admin" | "developer" | "viewer";
  exp: number;
}

/**
 * Decodes (does NOT verify) a JWT payload, purely to answer "is this about to
 * expire" in proxy.ts without an extra round trip. This is never the security
 * boundary -- FastAPI verifies the signature on every request that matters, and
 * requireSession() in lib/api.ts (which calls FastAPI's own /users/me) is the real
 * auth check standing in front of page data.
 */
export function isExpiringSoon(token: string, thresholdSeconds = 60): boolean {
  try {
    const payload = token.split(".")[1];
    if (!payload) return true;
    const json = Buffer.from(payload, "base64url").toString("utf-8");
    const claims = JSON.parse(json) as AccessClaims;
    return claims.exp * 1000 - Date.now() < thresholdSeconds * 1000;
  } catch {
    return true;
  }
}
