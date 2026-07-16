"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

type Mode = "login" | "register";

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const body =
        mode === "login"
          ? { email, password }
          : { email, password, full_name: fullName };
      const data = await apiFetch(path, null, { method: "POST", body: JSON.stringify(body) });
      localStorage.setItem("welyne_token", data.access_token);
      localStorage.setItem("welyne_role", data.role);
      window.location.href = "/jobs";
    } catch (err: any) {
      setError(
        mode === "login"
          ? "Identifiants invalides."
          : err.message?.includes("existe déjà")
            ? "Un compte existe déjà avec cet email."
            : "Impossible de créer le compte."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: "6vh" }}>
      <div style={{ width: 380 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            aria-hidden
            style={{
              width: 44, height: 44, borderRadius: 12, margin: "0 auto 16px",
              background: "linear-gradient(135deg, var(--accent), #14b8a6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 20, color: "#fff",
            }}
          >
            W
          </div>
          <h1 style={{ fontSize: 22 }}>Welyne One</h1>
          <p style={{ fontSize: 14, margin: "4px 0 0" }}>Plateforme agent IA RH</p>
        </div>

        {/* Bascule connexion / inscription — onglets segmentés */}
        <div
          role="tablist"
          aria-label="Mode d'authentification"
          style={{
            display: "flex", marginBottom: 20, background: "var(--surface-2, #f1f3f5)",
            borderRadius: 10, padding: 4, gap: 4,
          }}
        >
          {(["login", "register"] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => { setMode(m); setError(""); }}
              style={{
                flex: 1, margin: 0, padding: "8px 0", borderRadius: 7, border: "none",
                background: mode === m ? "#fff" : "transparent",
                color: mode === m ? "var(--ink, #111)" : "var(--ink-soft, #666)",
                fontWeight: mode === m ? 600 : 500,
                boxShadow: mode === m ? "0 1px 3px rgba(0,0,0,0.12)" : "none",
                cursor: "pointer",
              }}
            >
              {m === "login" ? "Se connecter" : "Créer un compte"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="card">
          {mode === "register" && (
            <>
              <label>Nom complet</label>
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Votre nom" />
            </>
          )}
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          <label>Mot de passe</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={mode === "register" ? 8 : undefined}
          />
          {mode === "register" && (
            <p style={{ fontSize: 12, marginTop: 4, color: "var(--ink-soft, #666)" }}>
              8 caractères minimum.
            </p>
          )}
          <button type="submit" disabled={loading} style={{ width: "100%", marginTop: 16 }}>
            {loading
              ? mode === "login" ? "Connexion…" : "Création…"
              : mode === "login" ? "Se connecter" : "Créer le compte"}
          </button>
          {error && (
            <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 10, marginBottom: 0 }}>{error}</p>
          )}
        </form>

        <p style={{ fontSize: 12, textAlign: "center", marginTop: 16, color: "var(--ink-soft, #666)" }}>
          {mode === "login" ? (
            <>Pas encore de compte ? <a onClick={() => setMode("register")} style={{ cursor: "pointer", fontWeight: 600 }}>Créer un compte</a></>
          ) : (
            <>Déjà inscrit ? <a onClick={() => setMode("login")} style={{ cursor: "pointer", fontWeight: 600 }}>Se connecter</a></>
          )}
        </p>
      </div>
    </div>
  );
}