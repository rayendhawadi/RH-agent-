"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api";

// Cible du lien envoyé par email à la création d'un compte (POST /users).
// Combine vérification d'email + choix du VRAI premier mot de passe en un
// seul appel (POST /auth/set-password) : l'admin ne connaît/ne communique
// aucun mot de passe, donc pas de détour par /auth/login avec un mot de
// passe temporaire que personne ne connaît.
type Status = "form" | "done" | "error";

export default function VerifyEmailPage() {
    return (
        <Suspense fallback={null}>
            <VerifyEmailInner />
        </Suspense>
    );
}

function VerifyEmailInner() {
    const params = useSearchParams();
    const token = params.get("token");

    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [status, setStatus] = useState<Status>("form");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        if (!token) {
            setError("Lien invalide : jeton de vérification manquant.");
            return;
        }
        if (password.length < 8) {
            setError("8 caractères minimum.");
            return;
        }
        if (password !== confirm) {
            setError("Les deux mots de passe ne correspondent pas.");
            return;
        }
        setLoading(true);
        try {
            await apiFetch("/auth/set-password", null, {
                method: "POST",
                body: JSON.stringify({ token, new_password: password }),
            });
            setStatus("done");
        } catch (err: any) {
            setStatus("error");
            setError(
                err.message?.includes("404")
                    ? "Ce lien est invalide ou a déjà été utilisé."
                    : "Impossible de définir le mot de passe."
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <div style={{ display: "flex", justifyContent: "center", paddingTop: "8vh" }}>
            <div style={{ width: 380 }}>
                <div style={{ textAlign: "center", marginBottom: 20 }}>
                    <h1 style={{ fontSize: 22 }}>Bienvenue sur Welyne One</h1>
                    <p style={{ fontSize: 14, color: "var(--ink-soft, #666)", margin: "4px 0 0" }}>
                        Confirmez votre email et choisissez votre mot de passe.
                    </p>
                </div>

                {status === "form" && (
                    <form onSubmit={handleSubmit} className="card">
                        <label>Nouveau mot de passe</label>
                        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoFocus />
                        <label>Confirmer le mot de passe</label>
                        <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} />
                        <p style={{ fontSize: 12, marginTop: 4, color: "var(--ink-soft, #666)" }}>8 caractères minimum.</p>
                        <button type="submit" disabled={loading} style={{ width: "100%", marginTop: 16 }}>
                            {loading ? "Validation…" : "Confirmer et créer mon mot de passe"}
                        </button>
                        {error && <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 10, marginBottom: 0 }}>{error}</p>}
                    </form>
                )}

                {status === "done" && (
                    <div className="card" style={{ textAlign: "center" }}>
                        <p style={{ margin: "0 0 16px", color: "var(--accent, #0a7)" }}>
                            ✓ Email confirmé et mot de passe créé.
                        </p>
                        <a href="/">
                            <button type="button" style={{ width: "100%" }}>Se connecter</button>
                        </a>
                    </div>
                )}

                {status === "error" && (
                    <div className="card" style={{ textAlign: "center" }}>
                        <p style={{ margin: "0 0 16px", color: "var(--coral)" }}>{error}</p>
                        <a href="/" style={{ fontSize: 13 }}>Retour à la connexion</a>
                    </div>
                )}
            </div>
        </div>
    );
}