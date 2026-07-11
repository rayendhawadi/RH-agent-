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
            const latestRes = await fetch(apiUrl(`/chat/applications/${applicationId}/latest`));
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
        <div style={{ maxWidth: 560, margin: "40px auto", padding: "0 16px" }}>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 20, margin: 0 }}>Pré-qualification — Welyne</h1>
                <p style={{ color: "var(--ink-soft, #666)", fontSize: 13, marginTop: 4 }}>
                    Répondez aux questions ci-dessous. Vos réponses sont enregistrées pour
                    votre candidature ; un humain valide chaque décision.
                </p>
            </div>

            {loading && <p style={{ color: "var(--ink-soft, #666)" }}>Chargement…</p>}

            {error && (
                <div className="card" style={{ borderColor: "var(--coral-bg, #fddede)", marginBottom: 16 }}>
                    <p style={{ margin: 0, fontSize: 14 }}>{error}</p>
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
                        {conv.messages.map((m, i) => (
                            <div key={i} style={{ alignSelf: m.role === "candidate" ? "flex-end" : "flex-start", maxWidth: "80%" }}>
                                <span
                                    style={{
                                        display: "inline-block",
                                        padding: "8px 12px",
                                        borderRadius: 12,
                                        fontSize: 14,
                                        lineHeight: 1.4,
                                        background: m.role === "candidate" ? "#e8f0ff" : "#f2f2f2",
                                    }}
                                >
                                    {m.body}
                                </span>
                            </div>
                        ))}
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
                        <p style={{ fontSize: 13, color: "var(--ink-soft, #666)", margin: 0 }}>
                            Merci, cette étape est terminée. Statut : <strong>{conv.status}</strong>. Nous
                            revenons vers vous prochainement.
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}