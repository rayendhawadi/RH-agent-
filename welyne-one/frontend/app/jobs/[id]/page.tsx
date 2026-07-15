"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import SourcingPanel from "@/components/sourcingpanel";

type JobSpec = {
    title: string;
    missions: string[];
    must_have: string[];
    nice_to_have: string[];
    seniority: string;
    languages: string[];
    location: string;
    hard_filters: string[];
    channel_content?: { linkedin_post: string; job_board_text: string; careers_page_text: string; whatsapp_message: string };
};
type Weights = { experience_fit: number; skills_fit: number; education_fit: number; sector_context_fit: number };
type Job = { id: string; title: string; status: string; job_spec: JobSpec; weights: Weights };

export default function JobDetailPage() {
    const { id } = useParams<{ id: string }>();
    const [token, setToken] = useState<string | null>(null);
    const [job, setJob] = useState<Job | null>(null);
    const [brief, setBrief] = useState("");
    const [loading, setLoading] = useState(false);
    const [msg, setMsg] = useState("");

    useEffect(() => {
        const t = localStorage.getItem("welyne_token");
        setToken(t);
        if (t) load(t);
    }, []);

    async function load(t: string) {
        const data = await apiFetch(`/jobs/${id}`, t);
        setJob(data);
    }

    async function generateSpec(e: React.FormEvent) {
        e.preventDefault();
        if (!token) return;
        setLoading(true);
        setMsg("");
        try {
            const data = await apiFetch(`/jobs/${id}/generate-spec`, token, {
                method: "POST",
                body: JSON.stringify({ raw_brief: brief }),
            });
            setJob(data);
            setMsg("Fiche générée. Vérifiez les critères avant publication.");
        } catch {
            setMsg("Erreur lors de la génération — vérifiez la passerelle LLM.");
        } finally {
            setLoading(false);
        }
    }

    async function saveWeights(w: Weights) {
        if (!token) return;
        const data = await apiFetch(`/jobs/${id}/weights`, token, { method: "PATCH", body: JSON.stringify(w) });
        setJob(data);
    }

    async function publish() {
        if (!token) return;
        if (!confirm("Publier cette offre ? Cette action est une porte humaine (§7) — elle sera visible en externe.")) return;
        const data = await apiFetch(`/jobs/${id}/publish`, token, { method: "POST" });
        setJob(data);
    }

    if (!token) return <p style={{ color: "var(--ink-soft)" }}>Connectez-vous d&apos;abord.</p>;
    if (!job) return <p style={{ color: "var(--ink-soft)" }}>Chargement…</p>;

    const spec = job.job_spec;
    const hasSpec = spec?.missions?.length > 0 || spec?.must_have?.length > 0;
    const weightTotal = job.weights.experience_fit + job.weights.skills_fit + job.weights.education_fit + job.weights.sector_context_fit;

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24 }}>{job.title}</h1>
                    <span className={`badge ${job.status}`} style={{ marginTop: 8, display: "inline-flex" }}>{job.status}</span>
                </div>
                {job.status !== "published" && (
                    <button onClick={publish} disabled={!hasSpec}>Publier l&apos;offre</button>
                )}
            </div>

            {!hasSpec && (
                <form onSubmit={generateSpec} className="card" style={{ marginBottom: 24 }}>
                    <label>Brief brut (collez la description du poste)</label>
                    <textarea
                        value={brief}
                        onChange={(e) => setBrief(e.target.value)}
                        required
                        rows={6}
                        style={{ width: "100%", padding: 10, border: "1px solid var(--line)", borderRadius: 8, fontFamily: "inherit", fontSize: 14 }}
                    />
                    <button type="submit" disabled={loading}>{loading ? "Génération…" : "Générer la fiche (A1)"}</button>
                    {msg && <p style={{ fontSize: 13, color: "var(--ink-soft)", marginTop: 10 }}>{msg}</p>}
                </form>
            )}

            {hasSpec && (
                <>
                    <div className="card" style={{ marginBottom: 20 }}>
                        <h3 style={{ marginBottom: 12 }}>Fiche de poste structurée</h3>
                        <p style={{ fontSize: 13, color: "var(--ink-soft)" }}>Séniorité : {spec.seniority || "—"} · Lieu : {spec.location || "—"} · Langues : {spec.languages?.join(", ") || "—"}</p>

                        <SpecList label="Missions" items={spec.missions} />
                        <SpecList label="Indispensables" items={spec.must_have} />
                        <SpecList label="Atouts" items={spec.nice_to_have} />
                        <SpecList label="Critères éliminatoires (filtres durs A4)" items={spec.hard_filters} accent="var(--coral)" />
                    </div>

                    <div className="card">
                        <h3 style={{ marginBottom: 4 }}>Pondérations du scoring</h3>
                        <p style={{ fontSize: 13, color: "var(--ink-soft)", marginBottom: 16 }}>
                            Total : {weightTotal}/100 {weightTotal !== 100 && <span style={{ color: "var(--coral)" }}>(devrait faire 100)</span>}
                        </p>
                        {(["experience_fit", "skills_fit", "education_fit", "sector_context_fit"] as const).map((key) => (
                            <WeightSlider
                                key={key}
                                label={{ experience_fit: "Expérience", skills_fit: "Compétences", education_fit: "Formation", sector_context_fit: "Contexte secteur" }[key]}
                                value={job.weights[key]}
                                onChange={(v) => setJob({ ...job, weights: { ...job.weights, [key]: v } })}
                                onCommit={(v) => saveWeights({ ...job.weights, [key]: v })}
                            />
                        ))}
                    </div>
                </>
            )}

            <SourcingPanel jobId={id} token={token} />
        </div>
    );
}

function SpecList({ label, items, accent }: { label: string; items: string[]; accent?: string }) {
    if (!items?.length) return null;
    return (
        <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: accent || "var(--ink)", marginBottom: 6 }}>{label}</div>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14 }}>
                {items.map((it, i) => <li key={i} style={{ marginBottom: 3 }}>{it}</li>)}
            </ul>
        </div>
    );
}

function WeightSlider({ label, value, onChange, onCommit }: { label: string; value: number; onChange: (v: number) => void; onCommit: (v: number) => void }) {
    return (
        <div style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                <span>{label}</span>
                <span className="mono">{value}</span>
            </div>
            <input
                type="range"
                min={0}
                max={100}
                value={value}
                onChange={(e) => onChange(Number(e.target.value))}
                onMouseUp={(e) => onCommit(Number((e.target as HTMLInputElement).value))}
                onTouchEnd={(e) => onCommit(Number((e.target as HTMLInputElement).value))}
                style={{ width: "100%" }}
            />
        </div>
    );
}