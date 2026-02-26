const runtimeOrigin =
  typeof window !== "undefined" && window.location.origin && !window.location.origin.includes(":5173")
    ? window.location.origin
    : "";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || runtimeOrigin || "http://localhost:1453";

async function parseResponse<T>(res: Response): Promise<T> {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || body.error || `Request failed (${res.status})`);
  }
  return body as T;
}

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  return parseResponse<T>(res);
}

export async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<T>(res);
}

export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: form,
  });
  return parseResponse<T>(res);
}
