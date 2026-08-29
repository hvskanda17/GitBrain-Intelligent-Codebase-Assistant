const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * Get the fully qualified API URL for a given path.
 */
export function getApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

/**
 * Client-side fetch helper that automatically prepends the API_BASE_URL 
 * and adds the Authorization header if an accessToken is provided.
 */
export async function apiClientFetch(
  path: string,
  options: RequestInit = {},
  accessToken?: string
): Promise<Response> {
  const headers = new Headers(options.headers);
  
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return fetch(getApiUrl(path), {
    cache: "no-store",
    ...options,
    headers,
  });
}
