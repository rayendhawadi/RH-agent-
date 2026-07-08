"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@welyne.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const data = await apiFetch("/auth/login", null, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("welyne_token", data.access_token);
      localStorage.setItem("welyne_role", data.role);
      window.location.href = "/jobs";
    } catch (err) {
      setError("Identifiants invalides.");
    }
  }

  return (
    <div style={{ maxWidth: 360 }}>
      <h2>Connexion</h2>
      <form onSubmit={handleLogin}>
        <label>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} />
        <label>Mot de passe</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button type="submit">Se connecter</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <p style={{ fontSize: 12, color: "#666" }}>
        Créez le premier compte avec <code>python scripts/seed_admin.py</code> côté backend.
      </p>
    </div>
  );
}
