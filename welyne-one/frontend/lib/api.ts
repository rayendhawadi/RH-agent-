const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function apiUrl(path: string) {
  return `${BASE}${path}`;
}

export async function apiFetch(path: string, token: string | null, options: RequestInit = {}) {
  const headers: Record<string, string> = { ...(options.headers as any) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const res = await fetch(apiUrl(path), { ...options, headers });
  if (!res.ok) {
    // Remonte le vrai message backend (ex. "Token invalide ou expiré",
    // "Utilisateur introuvable", "Rôle insuffisant") au lieu du seul code
    // HTTP — indispensable pour diagnostiquer un 401/403 sans avoir à
    // inspecter le terminal uvicorn à chaque fois.
    let detail = "";
    try {
      const body = await res.json();
<<<<<<< HEAD
      detail = body?.detail ? ` — ${body.detail}` : "";
=======
      if (Array.isArray(body?.detail)) {
        // Erreurs de validation FastAPI/Pydantic (422) : liste d'objets
        // {loc, msg, type} — on les rend lisibles au lieu de "[object Object]".
        detail = ` — ${body.detail
          .map((e: any) => `${(e.loc || []).join(".")}: ${e.msg}`)
          .join(" | ")}`;
      } else if (body?.detail) {
        detail = ` — ${body.detail}`;
      }
>>>>>>> c5302d4 (last)
    } catch {
      // réponse non-JSON (ex. 502 d'un proxy) : on garde juste le statut
    }
    throw new Error(`API ${path} -> ${res.status}${detail}`);
  }
  return res.json();
}