"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiUrl } from "@/lib/api";

type Slot = { start: string; end: string };
type Interview = {
    id: string;
    application_id: string;
    status: string;
    proposed_slots: Slot[];
    slot_start: string | null;
    slot_end: string | null;
    candidate_tz: string;
};

function fmt(iso: string) {
    return new Date(iso).toLocaleString("fr-FR", {
        weekday: "long", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
    });
}

// Page candidat publique (pas de token) — cible du lien "booking_link" envoyé
// par A7 dans l'email invite_interview : {FRONTEND_BASE_URL}/interviews/{id}/book.
// Consomme /public/interviews/* (app/api/interviews.py, public_router),
// volontairement sans authentification, même logique que la page /chat/[id].
export default function BookInterviewPage() {
    const params = useParams();
    const interviewId = params?.id as string;

    const [interview, setInterview] = useState<Interview | null>(null);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [tz, setTz] = useState("Africa/Tunis");

    useEffect(() => {
        if (interviewId) load();
        try {
            setTz(Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Tunis");
        } catch {
            // repli déjà en place (Africa/Tunis)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [interviewId]);

    async function load() {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(apiUrl(`/public/interviews/${interviewId}`));
            if (!res.ok) throw new Error(`-> ${res.status}`);
            setInterview(await res.json());
        } catch {
            setError("Lien invalide ou entretien introuvable.");
        } finally {
            setLoading(false);
        }
    }

    async function choose(index: number) {
        setBusy(true);
        setError(null);
        try {
            const res = await fetch(apiUrl(`/public/interviews/${interviewId}/choose-slot`), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ interview_id: interviewId, slot_index: index, candidate_tz: tz }),
            });
            if (!res.ok) {
                const body = await res.json().catch(() => null);
                throw new Error(body?.detail || `-> ${res.status}`);
            }
            setInterview(await res.json());
        } catch (e: any) {
            setError(e.message || "Impossible de réserver ce créneau. Il a peut-être déjà été pris — actualisez la page.");
        } finally {
            setBusy(false);
        }
    }

    if (!interviewId) return null;

    return (
        <div style={{ maxWidth: 480, margin: "40px auto", padding: "0 16px" }}>
            <h1 style={{ fontSize: 20, margin: "0 0 4px" }}>Choisir un créneau d&apos;entretien</h1>
            <p style={{ color: "var(--ink-soft, #666)", fontSize: 13, marginBottom: 20 }}>
                Fuseau horaire détecté : {tz}
            </p>

            {loading && <p style={{ color: "var(--ink-soft, #666)" }}>Chargement…</p>}

            {error && (
                <div className="card" style={{ borderColor: "var(--coral-bg, #fddede)", marginBottom: 16 }}>
                    <p style={{ margin: 0, fontSize: 14 }}>{error}</p>
                </div>
            )}

            {interview && interview.status === "PROPOSED" && (
                <div className="card" style={{ padding: 16 }}>
                    <p style={{ fontSize: 13, marginTop: 0 }}>Sélectionnez le créneau qui vous convient :</p>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {interview.proposed_slots.map((s, i) => (
                            <button key={i} onClick={() => choose(i)} disabled={busy} style={{ marginTop: 0, textAlign: "left" }}>
                                {fmt(s.start)}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {interview && interview.status === "BOOKED" && (
                <div className="card" style={{ padding: 16 }}>
                    <p style={{ margin: 0, fontSize: 14 }}>
                        ✓ Entretien confirmé pour <strong>{interview.slot_start && fmt(interview.slot_start)}</strong>.
                        Un email de confirmation avec invitation calendrier vous a été envoyé.
                    </p>
                </div>
            )}

            {interview && !["PROPOSED", "BOOKED"].includes(interview.status) && (
                <div className="card" style={{ padding: 16 }}>
                    <p style={{ margin: 0, fontSize: 14 }}>
                        Cet entretien n&apos;est plus disponible à la réservation (statut : {interview.status}).
                        Contactez le recruteur si besoin.
                    </p>
                </div>
            )}
        </div>
    );
}