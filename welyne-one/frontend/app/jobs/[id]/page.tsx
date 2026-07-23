"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { ONBOARDING_CATEGORY_LABELS } from "@/lib/onboardingCategories";

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
type Job = { id: string; title: string; status: string; job_spec: JobSpec; weights: Weights; onboarding_category?: string | null };

export default function JobDetailPage() {
    const { id } = useParams<{ id: string }>();
    const [token, setToken] = useState<string | null>(null);
    const [job, setJob] = useState<Job | null>(null);
    const [brief, setBrief] = useState("");
    const [loading, setLoading] = useState(false);
    const [msg, setMsg] = useState("");
    const [roleCategories, setRoleCategories] = useState<string[]>([]);
    const [categorySaving, setCategorySaving] = useState(false);
    const [categoryError, setCategoryError] = useState("");

    useEffect(() => {
        const t = localStorage.getItem("welyne_token");
        setToken(t);
        if (t) {
            load(t);
            apiFetch("/role-templates", t)
                .then((tpls: { role_category: string }[]) => setRoleCategories(tpls.map((x) => x.role_category)))
                .catch(() => setRoleCategories([]));
        }
    }, []);

    async function saveOnboardingCategory(value: string) {
        if (!token) return;
        setCategorySaving(true);
        setCategoryError("");
        try {
            const data = await apiFetch(`/jobs/${id}/onboarding-category`, token, {
                method: "PATCH",
                body: JSON.stringify({ onboarding_category: value || null }),
            });
            setJob(data);
        } catch (err: any) {
            setCategoryError(err?.message || "Impossible de changer la catégorie.");
        } finally {
            setCategorySaving(false);
        }
    }

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
            {/* ── En-tête ── */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 48, flexWrap: "wrap", gap: 24 }}>
                <div>
                    <div style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 12,
                        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
                        fontSize: 12,
                        textTransform: "uppercase",
                        letterSpacing: "0.24em",
                        color: "var(--accent)",
                        marginBottom: 16
                    }}>
                        <span style={{ display: "block", width: 32, height: 1, background: "var(--accent)" }}></span>
                        Agent A1 · Fiche de poste
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                        <h1 style={{
                            fontSize: "clamp(2rem, 5vw, 3.5rem)",
                            fontWeight: 800,
                            lineHeight: 1,
                            letterSpacing: "-0.04em",
                            margin: 0
                        }}>
                            {job.title}
                        </h1>
                        <span className={`badge ${job.status}`}>{job.status}</span>
                    </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <a
                        href={`/sourcing?job=${id}`}
                        style={{
                            fontSize: 13, fontWeight: 600, color: "var(--ink-soft)",
                            border: "1px solid var(--line)", borderRadius: 999, padding: "10px 18px",
                            textDecoration: "none",
                        }}
                    >
                        Sourcing (A2) →
                    </a>
                    {job.status !== "published" && (
                        <button onClick={publish} disabled={!hasSpec} style={{ fontSize: 13, padding: "12px 24px", background: "var(--accent)", color: "var(--surface)", border: "none" }}>
                            Publier l&apos;offre
                        </button>
                    )}
                </div>
            </div>

            {/* ── Catégorie d'onboarding (A8) — corrigeable tant qu'aucun candidat
                 de cette offre n'est encore HIRED/ONBOARDING (le backend renvoie
                 une 409 sinon, affichée telle quelle). ── */}
            <div className="card" style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap", padding: "18px 22px", marginBottom: 32 }}>
                <div>
                    <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-soft)", fontWeight: 600, marginBottom: 4 }}>
                        Catégorie d&apos;onboarding (A8)
                    </div>
                    <p style={{ margin: 0, fontSize: 12.5, color: "var(--ink-faint)" }}>
                        Détermine la checklist générée par l&apos;agent A8 une fois un candidat embauché sur cette offre.
                    </p>
                </div>
                <select
                    value={job.onboarding_category || ""}
                    onChange={(e) => saveOnboardingCategory(e.target.value)}
                    disabled={categorySaving}
                    style={{ background: "var(--paper)", border: "1px solid var(--line)", borderRadius: 10, padding: "8px 14px", fontSize: 14, color: "var(--ink)" }}
                >
                    <option value="">— Détection auto (par mot-clé) —</option>
                    {roleCategories.map((c) => (
                        <option key={c} value={c}>{ONBOARDING_CATEGORY_LABELS[c] || c}</option>
                    ))}
                </select>
                {categorySaving && <span style={{ fontSize: 12, color: "var(--ink-soft)" }}>Enregistrement…</span>}
                {categoryError && <span style={{ fontSize: 12, color: "var(--coral)" }}>{categoryError}</span>}
            </div>

            {!hasSpec && (
                <form onSubmit={generateSpec} className="card" style={{
                    border: "1px solid var(--line)",
                    borderRadius: 16,
                    background: "var(--surface)",
                    padding: 32,
                    boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
                    display: "flex", flexDirection: "column", gap: 16,
                    marginBottom: 32
                }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                        <span style={{ color: "var(--accent)", fontSize: 18 }}>♦</span>
                        <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Génération IA</h3>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        <label style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-soft)", fontWeight: 600 }}>Brief brut (collez la description du poste)</label>
                        <textarea
                            value={brief}
                            onChange={(e) => setBrief(e.target.value)}
                            required
                            rows={6}
                            style={{ background: "#0a0a0a", border: "1px solid var(--line)", padding: "12px 16px", borderRadius: 8, color: "var(--ink)", width: "100%", boxSizing: "border-box", fontFamily: "inherit", fontSize: 14 }}
                        />
                    </div>
                    <button type="submit" disabled={loading} style={{ alignSelf: "flex-start", marginTop: 8 }}>
                        {loading ? "Génération…" : "Générer la fiche (A1)"}
                    </button>
                    {msg && <p style={{ fontSize: 13, color: "var(--accent)", margin: 0 }}>{msg}</p>}
                </form>
            )}

            {hasSpec && (
                <>
                    <div className="card" style={{
                        border: "1px solid var(--line)",
                        borderRadius: 16,
                        background: "var(--surface)",
                        padding: 32,
                        boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
                        marginBottom: 32
                    }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                            <span style={{ color: "var(--accent)", fontSize: 18 }}>♦</span>
                            <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Fiche de poste structurée</h3>
                        </div>
                        <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
                            <span className="badge">Séniorité : {spec.seniority || "—"}</span>
                            <span className="badge">Lieu : {spec.location || "—"}</span>
                            <span className="badge">Langues : {spec.languages?.join(", ") || "—"}</span>
                        </div>

                        <SpecList label="Missions" items={spec.missions} />
                        <SpecList label="Indispensables" items={spec.must_have} />
                        <SpecList label="Atouts" items={spec.nice_to_have} />
                        <SpecList label="Critères éliminatoires (filtres durs A4)" items={spec.hard_filters} accent="var(--coral)" />
                    </div>

                    <div className="card" style={{
                        border: "1px solid var(--line)",
                        borderRadius: 16,
                        background: "var(--surface)",
                        padding: 32,
                        boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
                        marginBottom: 32
                    }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                            <span style={{ color: "var(--accent)", fontSize: 18 }}>♦</span>
                            <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Pondérations du scoring</h3>
                        </div>
                        <p style={{ fontSize: 13, color: "var(--ink-soft)", marginBottom: 24, lineHeight: 1.5 }}>
                            Total : <span style={{ color: weightTotal !== 100 ? "var(--coral)" : "var(--ink)", fontWeight: 700 }}>{weightTotal}/100</span>
                            {weightTotal !== 100 && <span style={{ color: "var(--coral)", marginLeft: 6 }}>(devrait faire 100)</span>}
                        </p>

                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 32 }}>
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
                    </div>
                </>
            )}
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