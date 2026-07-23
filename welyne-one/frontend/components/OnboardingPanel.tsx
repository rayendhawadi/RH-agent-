"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type Task = {
    id: string;
    task: string;
    kind: string;          // document | account | equipment | agenda
    owner: string;         // candidate | rh
    status: string;        // PENDING | SUBMITTED | DONE | REJECTED
    document_id: string | null;
    reject_reason: string | null;
};

const STATUS_LABEL: Record<string, string> = {
    PENDING: "En attente", SUBMITTED: "À valider", DONE: "Fait", REJECTED: "Rejeté",
};

// Panneau recruteur (dashboard, dans la colonne Action de la table candidatures
// quand status=ONBOARDING) — vue miroir du portail candidat public
// (app/onboarding/[id]/page.tsx) : ici le RH coche ses propres tâches et
// valide/rejette les documents déposés par le candidat.
export default function OnboardingPanel({ applicationId, token, canWrite = true }: { applicationId: string; token: string; canWrite?: boolean }) {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [busyId, setBusyId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [rejectingId, setRejectingId] = useState<string | null>(null);
    const [reason, setReason] = useState("");

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [applicationId]);

    async function load() {
        try {
            const data = await apiFetch(`/applications/${applicationId}/onboarding-tasks`, token);
            setTasks(data);
        } catch {
            setTasks([]);
        }
    }

    async function run(id: string, fn: () => Promise<any>) {
        setBusyId(id);
        setError(null);
        try {
            await fn();
            await load();
        } catch (e: any) {
            setError(e.message || "Une erreur est survenue");
        } finally {
            setBusyId(null);
        }
    }

    const complete = (t: Task) =>
        run(t.id, () => apiFetch(`/applications/${applicationId}/onboarding-tasks/${t.id}/complete`, token, { method: "POST" }));

    const validate = (t: Task) =>
        run(t.id, () => apiFetch(`/applications/${applicationId}/onboarding-tasks/${t.id}/validate`, token, { method: "POST" }));

    const reject = (t: Task) => {
        if (!reason.trim()) return;
        return run(t.id, async () => {
            await apiFetch(`/applications/${applicationId}/onboarding-tasks/${t.id}/reject`, token, {
                method: "POST", body: JSON.stringify({ reason: reason.trim() }),
            });
            setRejectingId(null);
            setReason("");
        });
    };

    if (tasks.length === 0) {
        return <span style={{ fontSize: 12, color: "var(--p-muted, var(--ink-soft))" }}>Checklist en cours de génération…</span>;
    }

    const done = tasks.filter((t) => t.status === "DONE").length;

    return (
        <div style={{ marginTop: 8, maxWidth: 480 }}>
            {error && <p style={{ color: "var(--p-danger, #c0392b)", fontSize: 12 }}>{error}</p>}

            <div style={{ fontSize: 12, color: "var(--p-muted, var(--ink-soft))", marginBottom: 8 }}>
                {done}/{tasks.length} tâches complétées
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {tasks.map((t) => (
                    <div
                        key={t.id}
                        style={{
                            display: "flex", justifyContent: "space-between", alignItems: "center",
                            gap: 10, padding: "12px 16px", borderRadius: 12,
                            background: "var(--surface)", border: "1px solid var(--border)", fontSize: 13,
                        }}
                    >
                        <div>
                            <div>{t.task}</div>
                            <div style={{ color: "var(--p-muted, var(--ink-soft))", marginTop: 2 }}>
                                {t.owner === "rh" ? "RH" : "Candidat"} · {STATUS_LABEL[t.status] || t.status}
                                {t.status === "REJECTED" && t.reject_reason ? ` — ${t.reject_reason}` : ""}
                            </div>
                        </div>

                        {canWrite && t.owner === "rh" && t.status !== "DONE" && (
                            <button onClick={() => complete(t)} disabled={busyId === t.id} style={{ 
                                marginTop: 0, padding: "8px 16px", fontSize: 12, fontWeight: 600,
                                background: "var(--accent)", color: "#fff", border: "none", borderRadius: 99
                            }}>
                                {busyId === t.id ? "…" : "Marquer fait"}
                            </button>
                        )}

                        {canWrite && t.owner === "candidate" && t.status === "SUBMITTED" && (
                            <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-end" }}>
                                <div style={{ display: "flex", gap: 6 }}>
                                    <button onClick={() => validate(t)} disabled={busyId === t.id} style={{ marginTop: 0, padding: "6px 12px", fontSize: 12 }}>
                                        Valider
                                    </button>
                                    <button
                                        onClick={() => setRejectingId(rejectingId === t.id ? null : t.id)}
                                        disabled={busyId === t.id}
                                        className="p-danger"
                                        style={{ marginTop: 0, padding: "6px 12px", fontSize: 12, background: "var(--p-danger, #c0392b)", color: "#fff" }}
                                    >
                                        Rejeter
                                    </button>
                                </div>
                                {rejectingId === t.id && (
                                    <div style={{ display: "flex", gap: 6 }}>
                                        <input
                                            value={reason}
                                            onChange={(e) => setReason(e.target.value)}
                                            placeholder="Motif du rejet"
                                            style={{ fontSize: 12, padding: "6px 8px", width: 160 }}
                                        />
                                        <button onClick={() => reject(t)} disabled={busyId === t.id || !reason.trim()} style={{ marginTop: 0, padding: "6px 10px", fontSize: 12 }}>
                                            OK
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}