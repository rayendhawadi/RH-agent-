"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

// Pas d'auto-inscription (§4/§7) : les comptes sont créés par un admin via
// /users (page /admin/users), avec email de vérification + mot de passe
// temporaire à changer à la première connexion. L'onglet "Créer un compte"
// appelait POST /auth/register, qui n'existe pas côté backend — retiré ici.
export default function AuthPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch("/auth/login", null, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("welyne_token", data.access_token);
      localStorage.setItem("welyne_role", data.role);
      if (data.password_reset_required) {
        window.location.href = "/change-password";
      } else {
        window.location.href = "/jobs";
      }
    } catch {
      setError("Identifiants invalides.");
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

        <form onSubmit={handleSubmit} className="card">
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required autoFocus />
          <label>Mot de passe</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" disabled={loading} style={{ width: "100%", marginTop: 16 }}>
            {loading ? "Connexion…" : "Se connecter"}
          </button>
          {error && (
            <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 10, marginBottom: 0 }}>{error}</p>
          )}
        </form>

        <p style={{ fontSize: 12, textAlign: "center", marginTop: 16, color: "var(--ink-soft, #666)" }}>
          Pas de compte ? Demandez à un administrateur de vous en créer un depuis
          la page « Utilisateurs ».
        </p>
      </div>
    </div>
  );
}