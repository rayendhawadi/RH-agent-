"use client";
import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { apiUrl } from "@/lib/api";

type Msg = { role: string; body: string };
type Conv = {
    id: string;
    application_id: string;
    channel: string;
    status: string;
    extracted: Record<string, string>;
    flags: any[];
    messages: Msg[];
};

// Page candidat publique (pas de token JWT) — cible du lien "prescreen_link"
// envoyé par A7 (email/WhatsApp) : https://.../chat/{application_id}.
// Consomme l'API /chat/* (app/api/prescreen.py), volontairement sans
// authentification côté backend puisque c'est le widget "portail candidat"
// prévu par la spec (§6-A5 : "widget de chat web sur le portail").
export default function CandidatePrescreenChatPage() {
    const params = useParams();
    const applicationId = params?.id as string;

    const [conv, setConv] = useState<Conv | null>(null);
    const [text, setText] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (applicationId) init();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [applicationId]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [conv?.messages.length]);

    async function init() {
        setLoading(true);
        setError(null);
        try {
            // 1. Reprendre une conversation existante si le candidat revient sur le lien.
            // Utilise la route publique (sans JWT) car le candidat n'a pas de compte.
            const latestRes = await fetch(apiUrl(`/chat/public/applications/${applicationId}/latest`));
            if (latestRes.ok) {
                const data = await latestRes.json();
                if (data) {
                    setConv(data);
                    setLoading(false);
                    return;
                }
            }
            // 2. Sinon, démarrer le dialogue (consentement + première question, cf. A5).
            const startRes = await fetch(apiUrl(`/chat/applications/${applicationId}/start`), {
                method: "POST",
            });
            if (!startRes.ok) throw new Error(`start -> ${startRes.status}`);
            setConv(await startRes.json());
        } catch (e: any) {
            setError("Impossible de charger la conversation. Le lien est peut-être invalide ou expiré.");
        } finally {
            setLoading(false);
        }
    }

    async function send() {
        if (!conv || !text.trim() || busy) return;
        setBusy(true);
        setError(null);
        try {
            const res = await fetch(apiUrl(`/chat/${conv.id}/message`), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text }),
            });
            if (!res.ok) throw new Error(`message -> ${res.status}`);
            setConv(await res.json());
            setText("");
        } catch {
            setError("Le message n'a pas pu être envoyé. Réessayez.");
        } finally {
            setBusy(false);
        }
    }

    function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
        if (e.key === "Enter") {
            e.preventDefault();
            send();
        }
    }

    if (!applicationId) return null;

    return (
        <div style={{ display: "flex", gap: 40, alignItems: "flex-start", flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 680px", maxWidth: 680 }}>
                <div style={{ marginBottom: 20 }}>
                    <span className="eyebrow">Agent A5 · Pré-qualification</span>
                    <h1 style={{ fontSize: 24 }}>
                        Pré-qualification — <span style={{ color: "var(--accent)" }}>Welyne</span>
                    </h1>
                    <p style={{ fontSize: 13.5, marginTop: 4 }}>
                        Répondez aux questions ci-dessous. Vos réponses sont enregistrées pour
                        votre candidature ; un humain valide chaque décision.
                    </p>
                </div>

                {loading && <p style={{ color: "var(--ink-soft)" }}>Chargement…</p>}

                {error && (
                    <div className="card" style={{ borderColor: "var(--coral)", marginBottom: 16 }}>
                        <p style={{ margin: 0, fontSize: 14, color: "var(--coral)" }}>{error}</p>
                    </div>
                )}

                {conv && (
                    <div className="card" style={{ padding: 16 }}>
                        <div
                            style={{
                                maxHeight: 440,
                                overflowY: "auto",
                                marginBottom: 12,
                                display: "flex",
                                flexDirection: "column",
                                gap: 8,
                            }}
                        >
                            {conv.messages.map((m, i) => {
                                const isCandidate = m.role === "candidate";
                                return (
                                    <div key={i} style={{ alignSelf: isCandidate ? "flex-end" : "flex-start", maxWidth: "80%" }}>
                                        <span
                                            style={{
                                                display: "inline-block",
                                                padding: "9px 14px",
                                                borderRadius: 14,
                                                borderBottomRightRadius: isCandidate ? 4 : 14,
                                                borderBottomLeftRadius: isCandidate ? 14 : 4,
                                                fontSize: 14,
                                                lineHeight: 1.45,
                                                background: isCandidate ? "var(--accent)" : "var(--paper)",
                                                color: isCandidate ? "#fff" : "var(--ink)",
                                                border: isCandidate ? "none" : "1px solid var(--line)",
                                            }}
                                        >
                                            {m.body}
                                        </span>
                                    </div>
                                );
                            })}
                            <div ref={bottomRef} />
                        </div>

                        {conv.status === "OPEN" ? (
                            <div style={{ display: "flex", gap: 8 }}>
                                <input
                                    value={text}
                                    onChange={(e) => setText(e.target.value)}
                                    onKeyDown={onKeyDown}
                                    placeholder="Votre réponse…"
                                    disabled={busy}
                                    style={{ margin: 0 }}
                                />
                                <button onClick={send} disabled={busy || !text.trim()} style={{ marginTop: 0, whiteSpace: "nowrap" }}>
                                    {busy ? "…" : "Envoyer"}
                                </button>
                            </div>
                        ) : (
                            <p style={{ fontSize: 13, color: "var(--ink-soft)", margin: 0 }}>
                                Merci, cette étape est terminée. Statut : <strong style={{ color: "var(--ink)" }}>{conv.status}</strong>. Nous
                                revenons vers vous prochainement.
                            </p>
                        )}
                    </div>
                )}
            </div>

            {/* Colonne droite — réservée à l'illustration/avatar de l'agent */}
            <div style={{ flex: "1 1 260px", minWidth: 220, position: "sticky", top: 32 }} aria-hidden />
        </div>
    );
}