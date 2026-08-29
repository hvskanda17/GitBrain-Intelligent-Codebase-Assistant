"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import {
  ACCESS_COOKIE,
  ACCESS_TOKEN_MAX_AGE,
  REFRESH_COOKIE,
  REFRESH_TOKEN_MAX_AGE,
  cookieOptions,
} from "@/lib/session";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export interface AuthFormState {
  error?: string;
}

async function setSessionCookies(tokens: { access_token: string; refresh_token: string }) {
  const cookieStore = await cookies();
  cookieStore.set(ACCESS_COOKIE, tokens.access_token, cookieOptions(ACCESS_TOKEN_MAX_AGE));
  cookieStore.set(REFRESH_COOKIE, tokens.refresh_token, cookieOptions(REFRESH_TOKEN_MAX_AGE));
}

export async function loginAction(
  _prevState: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const email = formData.get("email");
  const password = formData.get("password");

  const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    return { error: body?.error?.message ?? "Couldn't sign in with those details." };
  }

  await setSessionCookies(await res.json());
  redirect("/projects");
}

export async function registerAction(
  _prevState: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const email = formData.get("email");
  const password = formData.get("password");
  const fullName = formData.get("fullName");

  const registerRes = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName || null }),
  });

  if (!registerRes.ok) {
    const body = await registerRes.json().catch(() => null);
    return { error: body?.error?.message ?? "Couldn't create that account." };
  }

  // Phase 2's /auth/register returns the created user, not tokens -- log in right
  // after so a new account lands straight in the dashboard.
  const loginRes = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!loginRes.ok) {
    redirect("/login");
  }

  await setSessionCookies(await loginRes.json());
  redirect("/projects");
}

export async function logoutAction(): Promise<void> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(REFRESH_COOKIE)?.value;

  if (refreshToken) {
    await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {
      // best-effort server-side revocation -- cookies get cleared either way below
    });
  }

  cookieStore.delete(ACCESS_COOKIE);
  cookieStore.delete(REFRESH_COOKIE);
  redirect("/login");
}
