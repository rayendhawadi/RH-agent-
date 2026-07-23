"use client";
import { useState, useRef, useEffect } from "react";
import { apiUrl } from "@/lib/api";

type Message = { role: "user" | "assistant"; text: string };

export default function OnboardingChat({ applicationId }: { applicationId: string }) {
    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([
        { role: "assistant", text: "Bonjour ! 👋 Je suis l'assistant d'intégration. Posez-moi vos questions sur l'entreprise (congés, mutuelle, horaires…)." },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    async function send() {
        const q = input.trim();
        if (!q || loading) return;
        setMessages((prev) => [...prev, { role: "user", text: q }]);
        setInput("");
        setLoading(true);
        try {
            const res = await fetch(apiUrl(`/public/onboarding/${applicationId}/chat`), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: q }),
            });
            if (!res.ok) throw new Error("Erreur serveur");
            const data = await res.json();
            setMessages((prev) => [...prev, { role: "assistant", text: data.answer }]);
        } catch {
            setMessages((prev) => [...prev, { role: "assistant", text: "Désolé, une erreur est survenue. Réessayez dans un instant." }]);
        } finally {
            setLoading(false);
        }
    }

    if (!open) {
        return (
            <button
                onClick={() => setOpen(true)}
                aria-label="Ouvrir l'assistant"
                style={{
                    position: "fixed",
                    bottom: 24,
                    right: 24,
                    width: 56,
                    height: 56,
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #ff7a00 0%, #ff9d42 100%)",
                    color: "#fff",
                    border: "none",
                    fontSize: 26,
                    cursor: "pointer",
                    boxShadow: "0 6px 24px rgba(255,122,0,0.45)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "transform 0.2s",
                    zIndex: 1000,
                }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.1)")}
                onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
            >
                💬
            </button>
        );
    }

    return (
        <div
            style={{
                position: "fixed",
                bottom: 24,
                right: 24,
                width: 380,
                maxHeight: "70vh",
                borderRadius: 20,
                background: "#111",
                border: "1px solid rgba(255,255,255,0.08)",
                boxShadow: "0 16px 48px rgba(0,0,0,0.6)",
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
                zIndex: 1000,
                fontFamily: "'Inter', system-ui, sans-serif",
            }}
        >
            {/* Header */}
            <div
                style={{
                    padding: "14px 18px",
                    background: "linear-gradient(135deg, #ff7a00 0%, #ff9d42 100%)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                }}
            >
                <div>
                    <div style={{ fontWeight: 700, fontSize: 14, color: "#fff" }}>🤖 Assistant Onboarding</div>
                    <div style={{ fontSize: 11, color: "rgba(255,255,255,0.8)" }}>Agent A8 · Manuel d&apos;entreprise</div>
                </div>
                <button
                    onClick={() => setOpen(false)}
                    style={{
                        background: "rgba(255,255,255,0.2)",
                        border: "none",
                        borderRadius: "50%",
                        width: 28,
                        height: 28,
                        color: "#fff",
                        cursor: "pointer",
                        fontSize: 14,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                    }}
                >
                    ✕
                </button>
            </div>

            {/* Messages */}
            <div
                style={{
                    flex: 1,
                    overflowY: "auto",
                    padding: "16px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                    minHeight: 220,
                    maxHeight: "50vh",
                }}
            >
                {messages.map((m, i) => (
                    <div
                        key={i}
                        style={{
                            alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                            background: m.role === "user"
                                ? "linear-gradient(135deg, #ff7a00 0%, #ff9d42 100%)"
                                : "rgba(255,255,255,0.06)",
                            color: m.role === "user" ? "#fff" : "#ddd",
                            padding: "10px 14px",
                            borderRadius: m.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                            maxWidth: "85%",
                            fontSize: 13,
                            lineHeight: 1.5,
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                        }}
                    >
                        {m.text}
                    </div>
                ))}
                {loading && (
                    <div
                        style={{
                            alignSelf: "flex-start",
                            background: "rgba(255,255,255,0.06)",
                            color: "#999",
                            padding: "10px 14px",
                            borderRadius: "16px 16px 16px 4px",
                            fontSize: 13,
                        }}
                    >
                        <span className="typing-dots">●●●</span>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div
                style={{
                    padding: "12px 14px",
                    borderTop: "1px solid rgba(255,255,255,0.06)",
                    display: "flex",
                    gap: 8,
                }}
            >
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
                    placeholder="Posez votre question…"
                    disabled={loading}
                    style={{
                        flex: 1,
                        background: "rgba(255,255,255,0.06)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 12,
                        padding: "10px 14px",
                        color: "#fff",
                        fontSize: 13,
                        outline: "none",
                    }}
                />
                <button
                    onClick={send}
                    disabled={!input.trim() || loading}
                    style={{
                        background: "linear-gradient(135deg, #ff7a00 0%, #ff9d42 100%)",
                        border: "none",
                        borderRadius: 12,
                        width: 40,
                        cursor: "pointer",
                        color: "#fff",
                        fontSize: 16,
                        opacity: !input.trim() || loading ? 0.5 : 1,
                    }}
                >
                    ➤
                </button>
            </div>
        </div>
    );
}
