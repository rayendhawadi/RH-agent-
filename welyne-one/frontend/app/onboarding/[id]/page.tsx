"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiUrl } from "@/lib/api";

type Task = { id: string; task: string; kind: string; status: string; reject_reason: string | null };
type Portal = { application_id: string; candidate_name: string; job_title: string; tasks: Task[] };

const STATUS_LABEL: Record<string, string> = {
    PENDING: "À déposer", SUBMITTED: "En cours de vérification", DONE: "Validé", REJECTED: "À redéposer",
};

// Page candidat publique (pas de token JWT — même pattern que app/chat/[id] et
// app/interviews/[id]/book) : cible du lien envoyé par A8 dans l'email de
// bienvenue onboarding. Consomme /public/onboarding/* (app/api/onboarding.py,
// public_router), volontairement sans authentification.
export default function OnboardingPortalPage() {
    const params = useParams();
    const applicationId = params?.id as string;

    const [portal, setPortal] = useState<Portal | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [busyId, setBusyId] = useState<string | null>(null);
    const [files, setFiles] = useState<Record<string, File | null>>({});

    useEffect(() => {
        if (applicationId) load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [applicationId]);

    async function load() {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(apiUrl(`/public/onboarding/${applicationId}`));
            if (!res.ok) throw new Error("Lien invalide ou expiré.");
            setPortal(await res.json());
        } catch (e: any) {
            setError(e.message || "Une erreur est survenue.");
        } finally {
            setLoading(false);
        }
    }

    async function submit(taskId: string) {
        const file = files[taskId];
        if (!file) return;
        setBusyId(taskId);
        setError(null);
        try {
            const form = new FormData();
            form.append("file", file);
            const res = await fetch(apiUrl(`/public/onboarding/tasks/${taskId}/submit`), { method: "POST", body: form });
            if (!res.ok) throw new Error("Échec de l'envoi du document.");
            await load();
        } catch (e: any) {
            setError(e.message || "Une erreur est survenue.");
        } finally {
            setBusyId(null);
        }
    }

    if (loading) return <main style={{ maxWidth: 640, margin: "60px auto", padding: 24 }}>Chargement…</main>;
    if (error && !portal) return <main style={{ maxWidth: 640, margin: "60px auto", padding: 24, color: "#c0392b" }}>{error}</main>;
    if (!portal) return null;

    const documentTasks = portal.tasks.filter((t) => t.kind === "document");
    const doneCount = documentTasks.filter((t) => t.status === "DONE").length;

    return (
        <main style={{ maxWidth: 640, margin: "60px auto", padding: 24 }}>
            <h1 style={{ fontSize: 24, marginBottom: 4 }}>Bienvenue {portal.candidate_name} 👋</h1>
            <p style={{ color: "#666", marginBottom: 4 }}>
                Poste : <strong>{portal.job_title}</strong>
            </p>
            <p style={{ color: "#666", marginBottom: 28 }}>
                {doneCount}/{documentTasks.length} documents validés — déposez les documents ci-dessous pour compléter votre intégration.
            </p>

            {error && <p style={{ color: "#c0392b", marginBottom: 16 }}>{error}</p>}

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {documentTasks.map((t) => (
                    <div key={t.id} style={{ border: "1px solid #e2e2e2", borderRadius: 10, padding: 16 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                            <strong>{t.task}</strong>
                            <span style={{ fontSize: 12, color: t.status === "DONE" ? "#1a7f4e" : t.status === "REJECTED" ? "#c0392b" : "#666" }}>
                                {STATUS_LABEL[t.status] || t.status}
                            </span>
                        </div>

                        {t.status === "REJECTED" && t.reject_reason && (
                            <p style={{ fontSize: 13, color: "#c0392b", marginBottom: 8 }}>Motif du rejet : {t.reject_reason}</p>
                        )}

                        {(t.status === "PENDING" || t.status === "REJECTED") && (
                            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                                <input
                                    type="file"
                                    onChange={(e) => setFiles((f) => ({ ...f, [t.id]: e.target.files?.[0] || null }))}
                                />
                                <button
                                    onClick={() => submit(t.id)}
                                    disabled={busyId === t.id || !files[t.id]}
                                >
                                    {busyId === t.id ? "Envoi…" : "Déposer"}
                                </button>
                            </div>
                        )}

                        {t.status === "SUBMITTED" && (
                            <p style={{ fontSize: 13, color: "#666" }}>Document reçu, en attente de vérification par l'équipe RH.</p>
                        )}
                        {t.status === "DONE" && (
                            <p style={{ fontSize: 13, color: "#1a7f4e" }}>✓ Document validé.</p>
                        )}
                    </div>
                ))}
                {documentTasks.length === 0 && (
                    <p style={{ color: "#666" }}>Aucun document à déposer pour le moment.</p>
                )}
            </div>
        </main>
    );
}