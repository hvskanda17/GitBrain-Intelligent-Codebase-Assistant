import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import { ACCESS_COOKIE } from "@/lib/session";
import type { UserProfile } from "@/types/api";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export class ApiRequestError extends Error {
  constructor(
    public status: number,
    public apiError: ApiError,
  ) {
    super(apiError.message);
  }
}

/**
 * Server-side fetch against the FastAPI backend, authenticated with whatever access
 * token is in the request's cookies. Throws ApiRequestError on non-2xx so callers
 * (Server Components, Server Actions) can catch and render/redirect appropriately.
 * proxy.ts refreshes the access token before a request reaches here, but this
 * doesn't depend on that having happened -- a rejected/expired token just surfaces
 * as a normal ApiRequestError with status 401.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(ACCESS_COOKIE)?.value;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init.headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const apiError: ApiError = body?.error ?? {
      code: "unknown_error",
      message: `Request failed with status ${res.status}`,
      details: {},
    };
    throw new ApiRequestError(res.status, apiError);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

/**
 * The real auth boundary for every protected Server Component. proxy.ts redirects
 * unauthenticated requests before they get here as a UX fast path, but the actual
 * enforcement is this call: it hits FastAPI's own `get_current_user` dependency, so
 * even a bypassed or misconfigured proxy can't render protected data without a
 * token FastAPI itself considers valid. Wrapped in React's cache() so calling it
 * from both a layout and a page in the same request only hits the backend once.
 */
export const requireSession = cache(async (): Promise<UserProfile> => {
  try {
    return await apiFetch<UserProfile>("/api/v1/users/me");
  } catch (err) {
    if (err instanceof ApiRequestError && err.status === 401) {
      redirect("/login");
    }
    throw err;
  }
});
