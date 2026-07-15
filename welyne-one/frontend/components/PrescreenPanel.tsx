"use client";
import { useEffect, useState } from "react";
import { apiFetch, apiUrl } from "@/lib/api";

type Interview = {
    id: string;
    application_id: string;
    status: string;
    proposed_slots: { start: string; end: string }[];
    slot_start: string | null;
    slot_end: string | null;
    candidate_tz: string;
    calendar_ref: string | null;
    reschedule_count: number;
};

function fmt(iso: string | null) {
    if (!iso) return "";
    return new Date(iso).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}

export default function InterviewPanel({ applicationId, token }: { applicationId: string; token: string }) {
    const [interviews, setInterviews] = useState<Interview[]>([]);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [reschedId, setReschedId] = useState<string | null>(null);
    const [newStart, setNewStart] = useState("");
    const [newEnd, setNewEnd] = useState("");

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [applicationId]);

    async function load() {
        try {
            const data = await apiFetch(`/applications/${applicationId}/interviews`, token);
            setInterviews(data);
        } catch {
            setInterviews([]);
        }
    }

    async function run(fn: () => Promise<any>) {
        setBusy(true);
        setError(null);
        try {
            await fn();
            await load();
        } catch (e: any) {
            setError(e.message || "Une erreur est survenue");
        } finally {
            setBusy(false);
        }
    }

    const proposeSlots = () =>
        run(() => apiFetch(`/applications/${applicationId}/propose-interview-slots`, token, { method: "POST", body: JSON.stringify({}) }));

    const markInterviewed = (interviewId: string) =>
        run(() => apiFetch(`/applications/${applicationId}/mark-interviewed?interview_id=${interviewId}`, token, { method: "POST" }));

    const cancel = (interviewId: string) => {
        if (!confirm("Annuler cet entretien ? Le candidat sera notifié.")) return;
        return run(() =>
            apiFetch(`/applications/${applicationId}/cancel-interview`, token, {
                method: "POST",
                body: JSON.stringify({ interview_id: interviewId, reason: "" }),
            })
        );
    };

    const noShow = (interviewId: string) => {
        if (!confirm("Marquer le candidat comme absent (no-show) ? La candidature partira en NEEDS_ATTENTION pour décision recruteur.")) return;
        return run(() => apiFetch(`/applications/${applicationId}/interviews/${interviewId}/no-show`, token, { method: "POST" }));
    };

    const submitReschedule = (interviewId: string) => {
        if (!newStart || !newEnd) return;
        return run(async () => {
            await apiFetch(`/applications/${applicationId}/reschedule-interview`, token, {
                method: "POST",
                body: JSON.stringify({
                    interview_id: interviewId,
                    start: new Date(newStart).toISOString(),
                    end: new Date(newEnd).toISOString(),
                    reason: "",
                }),
            });
            setReschedId(null);
            setNewStart("");
            setNewEnd("");
        });
    };

    const current = interviews[0]; // le plus récent (tri décroissant côté API)
    const bookingLink = current ? `${(process.env.NEXT_PUBLIC_APP_BASE_URL || "http://localhost:3000")}/interviews/${current.id}/book` : "";

    return (
        <div style={{ marginTop: 8, maxWidth: 480 }}>
            {error && <p style={{ color: "var(--coral, #c0392b)", fontSize: 12 }}>{error}</p>}

            {!current && (
                <button onClick={proposeSlots} disabled={busy}>
                    {busy ? "Envoi…" : "Proposer 3 créneaux (A6)"}
                </button>
            )}

            {current && current.status === "PROPOSED" && (
                <div className="card" style={{ padding: 12 }}>
                    <div style={{ fontSize: 12, color: "var(--ink-soft)", marginBottom: 6 }}>
                        En attente du choix du candidat — créneaux proposés :
                    </div>
                    <ul style={{ fontSize: 13, margin: "0 0 8px", paddingLeft: 18 }}>
                        {current.proposed_slots.map((s, i) => (
                            <li key={i}>{fmt(s.start)}</li>
                        ))}
                    </ul>
                    <div style={{ fontSize: 12 }}>
                        Lien candidat :{" "}
                        <a href={bookingLink} target="_blank" rel="noopener noreferrer">{bookingLink}</a>
                    </div>
                </div>
            )}

            {current && current.status === "BOOKED" && (
                <div className="card" style={{ padding: 12 }}>
                    <div style={{ fontSize: 13, marginBottom: 8 }}>
                        Entretien confirmé : <strong>{fmt(current.slot_start)}</strong> ({current.candidate_tz})
                        {current.reschedule_count > 0 && (
                            <span style={{ color: "var(--ink-soft)", fontSize: 12 }}> — replanifié {current.reschedule_count}×</span>
                        )}
                    </div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <button onClick={() => markInterviewed(current.id)} disabled={busy}>Marquer effectué</button>
                        <button onClick={() => setReschedId(reschedId === current.id ? null : current.id)} disabled={busy}>
                            Replanifier
                        </button>
                        <button onClick={() => noShow(current.id)} disabled={busy} style={{ background: "var(--coral)" }}>
                            No-show
                        </button>
                        <button onClick={() => cancel(current.id)} disabled={busy} style={{ background: "var(--coral)" }}>
                            Annuler
                        </button>
                    </div>

                    {reschedId === current.id && (
                        <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
                            <div>
                                <label style={{ fontSize: 11 }}>Nouveau début</label>
                                <input type="datetime-local" value={newStart} onChange={(e) => setNewStart(e.target.value)} />
                            </div>
                            <div>
                                <label style={{ fontSize: 11 }}>Nouvelle fin</label>
                                <input type="datetime-local" value={newEnd} onChange={(e) => setNewEnd(e.target.value)} />
                            </div>
                            <button onClick={() => submitReschedule(current.id)} disabled={busy || !newStart || !newEnd} style={{ marginTop: 0 }}>
                                Confirmer
                            </button>
                        </div>
                    )}
                </div>
            )}

            {current && ["CANCELLED", "NO_SHOW", "COMPLETED"].includes(current.status) && (
                <span className={`badge ${current.status}`}>{current.status}</span>
            )}
        </div>
    );
}