"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

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
      window.location.href = data.password_reset_required ? "/change_password" : "/jobs";
    } catch {
      setError("Identifiants invalides.");
    } finally {
      setLoading(false);
    }
  }

  const AGENTS = ["A1 Publication", "A2 Sourcing", "A3 Parsing", "A4 Scoring", "A5 Pré-qualification",
    "A6 Entretiens", "A7 Communications", "A8 Onboarding", "A9 Reporting"];

  return (
    <div
      style={{
        position: "relative", left: "50%", right: "50%",
        marginLeft: "-50vw", marginRight: "-50vw", width: "100vw",
        marginTop: -32, marginBottom: -32, minHeight: "calc(100vh - 61px)",
      }}
    >
      {/* bandeau défilant — motif signature repris de welyne.com */}
      <div className="ticker">
        <div className="ticker__track">
          {[...AGENTS, ...AGENTS].map((a, i) => (
            <span key={i} className="ticker__item">
              <b>◆</b> {a}
            </span>
          ))}
        </div>
      </div>

      <div style={{ maxWidth: 480, margin: "0 auto", padding: "80px 24px 60px", textAlign: "center" }}>
        <p className="mono" style={{ color: "var(--accent)", fontSize: 12, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 18 }}>
          Plateforme agent IA RH
        </p>
        <h1 style={{ fontSize: 44, lineHeight: 1.05, marginBottom: 16 }}>
          WE hire, <span style={{ color: "var(--accent)" }}>together.</span>
        </h1>
        <p style={{ fontSize: 15, marginBottom: 40 }}>
          Neuf agents IA orchestrent le recrutement de bout en bout — un humain valide chaque décision sensible.
        </p>

        <form onSubmit={handleSubmit} className="card" style={{ textAlign: "left" }}>
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required autoFocus />
          <label>Mot de passe</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <button type="submit" disabled={loading} style={{ width: "100%", marginTop: 16 }}>
            {loading ? "Connexion…" : "Se connecter →"}
          </button>
          {error && <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 10, marginBottom: 0 }}>{error}</p>}
        </form>

        <p style={{ fontSize: 12, marginTop: 20 }}>
          Pas de compte ? Demandez à un administrateur de vous en créer un.
        </p>
      </div>
    </div>
  );
}