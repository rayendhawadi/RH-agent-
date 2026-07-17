"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

// Cible du endpoint backend existant POST /auth/change-password (§7),
// jusqu'ici jamais appelé depuis le frontend. Nécessaire pour tout compte
// créé par un admin avec password_reset_required=true (POST /users,
// POST /users/{id}/reset-password) — sans cette page, ces comptes
// n'avaient aucun moyen de sortir du mot de passe temporaire.
export default function ChangePasswordPage() {
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [error, setError] = useState("");
    const [done, setDone] = useState(false);
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        if (newPassword !== confirm) {
            setError("Les deux mots de passe ne correspondent pas.");
            return;
        }
        const token = localStorage.getItem("welyne_token");
        if (!token) {
            window.location.href = "/";
            return;
        }
        setLoading(true);
        try {
            await apiFetch("/auth/change-password", token, {
                method: "POST",
                body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
            });
            setDone(true);
            setTimeout(() => { window.location.href = "/jobs"; }, 1200);
        } catch {
            setError("Mot de passe actuel incorrect, ou nouveau mot de passe invalide (8 caractères minimum).");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div style={{ display: "flex", justifyContent: "center", paddingTop: "6vh" }}>
            <div style={{ width: 380 }}>
                <h1 style={{ fontSize: 22, marginBottom: 4 }}>Changer votre mot de passe</h1>
                <p style={{ fontSize: 14, color: "var(--ink-soft, #666)", marginBottom: 20 }}>
                    Requis avant de continuer — votre compte a été créé avec un mot de passe temporaire.
                </p>

                <form onSubmit={handleSubmit} className="card">
                    <label>Mot de passe actuel (temporaire)</label>
                    <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required />
                    <label>Nouveau mot de passe</label>
                    <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} />
                    <label>Confirmer le nouveau mot de passe</label>
                    <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} />
                    <p style={{ fontSize: 12, marginTop: 4, color: "var(--ink-soft, #666)" }}>8 caractères minimum.</p>

                    <button type="submit" disabled={loading} style={{ width: "100%", marginTop: 16 }}>
                        {loading ? "Enregistrement…" : "Changer le mot de passe"}
                    </button>
                    {error && <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 10, marginBottom: 0 }}>{error}</p>}
                    {done && <p style={{ color: "var(--accent, #0a7)", fontSize: 13, marginTop: 10, marginBottom: 0 }}>Mot de passe changé — redirection…</p>}
                </form>
            </div>
        </div>
    );
}