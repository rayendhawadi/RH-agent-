"use client";
import { useEffect, useState } from "react";
import { apiFetch, apiUrl } from "@/lib/api";

type Conv = { id: string; status: string };

// Ouvre la MÊME page que celle envoyée par email/WhatsApp au candidat
// (/chat/{applicationId}, cf. app/chat/[id]/page.tsx) — cette page gère déjà
// elle-même "reprendre si une conversation existe / démarrer sinon". Le
// dashboard n'a donc plus besoin de dupliquer le chat : on l'ouvre tel quel
// dans un nouvel onglet, pour que le recruteur voie exactement ce que voit
// le candidat.
export default function PrescreenPanel({ applicationId, token, canWrite = true }: { applicationId: string; token: string; canWrite?: boolean }) {
    const [conv, setConv] = useState<Conv | null>(null);
    const [checked, setChecked] = useState(false);
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        check();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [applicationId]);

    async function check() {
        setBusy(true);
        try {
            const data = await apiFetch(`/chat/applications/${applicationId}/latest`, token);
            setConv(data);
        } catch {
            setConv(null);
        } finally {
            setChecked(true);
            setBusy(false);
        }
    }

    function openCandidateView() {
        window.open(`/chat/${applicationId}`, "_blank", "noopener,noreferrer");
    }

    const secondaryBtn = {
        marginRight: 8, marginTop: 0, padding: "6px 12px", fontSize: 13,
        background: "transparent", color: "var(--ink-soft)", border: "1px solid var(--line)",
    };

    return (
        <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <button onClick={openCandidateView} disabled={busy || (!conv && !canWrite)} style={secondaryBtn}>
                {conv ? "Ouvrir la conversation A5" : "Démarrer le dialogue A5"}
            </button>

            {conv && (
                <>
                    <span className={`badge ${conv.status}`} style={{ fontSize: 11 }}>{conv.status}</span>
                    <a href={apiUrl(`/chat/${conv.id}/export.pdf`)} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12 }}>
                        Exporter en PDF
                    </a>
                </>
            )}

            {checked && !conv && !canWrite && (
                <p style={{ fontSize: 12, color: "var(--ink-soft)", margin: 0 }}>
                    Aucune conversation A5 pour l&apos;instant.
                </p>
            )}
        </div>
    );
}