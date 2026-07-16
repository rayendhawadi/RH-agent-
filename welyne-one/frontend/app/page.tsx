"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@welyne.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
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
      window.location.href = "/jobs";
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
          <p style={{ fontSize: 14, margin: "4px 0 0" }}>Plateforme agent IA RH — accès équipe</p>
        </div>

        <form onSubmit={handleLogin} className="card">
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
          <label>Mot de passe</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button type="submit" disabled={loading} style={{ width: "100%", marginTop: 16 }}>
            {loading ? "Connexion…" : "Se connecter"}
          </button>
          {error && (
            <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 10, marginBottom: 0 }}>{error}</p>
          )}
        </form>

        <p style={{ fontSize: 12, textAlign: "center", marginTop: 16 }}>
          Premier compte : <code>python scripts/seed_admin.py</code> côté backend.
        </p>
      </div>
    </div>
  );
}