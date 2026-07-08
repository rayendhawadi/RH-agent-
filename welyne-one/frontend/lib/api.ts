const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function apiUrl(path: string) {
  return `${BASE}${path}`;
}

export async function apiFetch(path: string, token: string | null, options: RequestInit = {}) {
  const headers: Record<string, string> = { ...(options.headers as any) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const res = await fetch(apiUrl(path), { ...options, headers });
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json();
}
