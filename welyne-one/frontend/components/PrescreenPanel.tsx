"use client";
import { useState } from "react";
import { apiFetch, apiUrl } from "@/lib/api";

type Msg = { role: string; body: string };
type Conv = {
    id: string;
    status: string;
    extracted: Record<string, string>;
    flags: any[];
    messages: Msg[];
};

export default function PrescreenPanel({ applicationId, token }: { applicationId: string; token: string }) {
    const [conv, setConv] = useState<Conv | null>(null);
    const [text, setText] = useState("");
    const [busy, setBusy] = useState(false);

    async function load() {
        try {
            const data = await apiFetch(`/chat/applications/${applicationId}/latest`, token);
            setConv(data);
        } catch {
            setConv(null);
        }
    }

    async function start() {
        setBusy(true);
        try {
            const data = await apiFetch(`/chat/applications/${applicationId}/start`, token, { method: "POST" });
            setConv(data);
        } finally {
            setBusy(false);
        }
    }

    async function send() {
        if (!conv || !text.trim()) return;
        setBusy(true);
        try {
            const data = await apiFetch(`/chat/${conv.id}/message`, token, {
                method: "POST",
                body: JSON.stringify({ text }),
            });
            setConv(data);
            setText("");
        } finally {
            setBusy(false);
        }
    }

    if (!conv) {
        return (
            <div style={{ marginTop: 8 }}>
                <button onClick={load} style={{ marginRight: 8 }}>Voir la conversation A5</button>
                <button onClick={start} disabled={busy}>{busy ? "…" : "Démarrer le dialogue A5"}</button>
            </div>
        );
    }

    return (
        <div style={{ marginTop: 8, border: "1px solid var(--border, #ddd)", borderRadius: 8, padding: 12, maxWidth: 480 }}>
            <div style={{ fontSize: 12, marginBottom: 8, color: "var(--ink-soft)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span>Statut : <strong>{conv.status}</strong></span>
                <a
                    href={apiUrl(`/chat/${conv.id}/export.pdf`)}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: 12 }}
                >
                    Exporter en PDF
                </a>
            </div>
            <div style={{ maxHeight: 220, overflowY: "auto", marginBottom: 8 }}>
                {conv.messages.map((m, i) => (
                    <div key={i} style={{ margin: "4px 0", textAlign: m.role === "candidate" ? "right" : "left" }}>
                        <span style={{
                            display: "inline-block", padding: "6px 10px", borderRadius: 8,
                            background: m.role === "candidate" ? "var(--coral, #eee)" : "#f0f0f0", fontSize: 13,
                        }}>
                            {m.body}
                        </span>
                    </div>
                ))}
            </div>
            {conv.status === "OPEN" && (
                <div style={{ display: "flex", gap: 8 }}>
                    <input
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder="Répondre en tant que candidat (test)…"
                        style={{ flex: 1 }}
                        onKeyDown={(e) => e.key === "Enter" && send()}
                    />
                    <button onClick={send} disabled={busy}>{busy ? "…" : "Envoyer"}</button>
                </div>
            )}
            {Object.keys(conv.extracted).length > 0 && (
                <div style={{ marginTop: 8, fontSize: 12 }}>
                    <strong>Réponses collectées :</strong>
                    <ul>
                        {Object.entries(conv.extracted).map(([k, v]) => <li key={k}>{k}: {v}</li>)}
                    </ul>
                </div>
            )}
        </div>
    );
}