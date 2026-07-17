"use client";
import { useEffect, useState } from "react";
import { apiFetch, apiUrl } from "@/lib/api";

type SourceStat = { source: string; total: number; converted: number; conversion_rate: number; by_status: Record<string, number> };
type Funnel = { total: number; by_status: Record<string, number>; by_source: Record<string, number> };
type StageTiming = { stage: string; avg_hours: number; n: number };
type SlaSummary = { avg_min: number; p95_min: number; n: number };
type Sla = { parsing: SlaSummary; scoring: SlaSummary };
type ScoreBucket = { range: string; count: number };
type Cost = {
    window_days: number; total_tokens: number; total_cost_usd_estimate: number;
    hires: number; tokens_per_hire: number | null; cost_usd_per_hire_estimate: number | null;
};

function Bar({ label, value, max, suffix = "" }: { label: string; value: number; max: number; suffix?: string }) {
    const pct = max > 0 ? Math.max(2, (value / max) * 100) : 0;
    return (
        <div style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 3 }}>
                <span>{label}</span>
                <span className="mono">{value}{suffix}</span>
            </div>
            <div style={{ background: "var(--paper)", borderRadius: 4, height: 8, overflow: "hidden" }}>
                <div style={{ width: `${pct}%`, height: "100%", background: "var(--accent)", borderRadius: 4 }} />
            </div>
        </div>
    );
}

async function downloadFile(path: string, token: string, filename: string) {
    const res = await fetch(apiUrl(path), { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

export default function ReportsPage() {
    const [token, setToken] = useState<string | null>(null);
    const [sources, setSources] = useState<SourceStat[]>([]);
    const [funnel, setFunnel] = useState<Funnel | null>(null);
    const [timing, setTiming] = useState<StageTiming[]>([]);
    const [sla, setSla] = useState<Sla | null>(null);
    const [buckets, setBuckets] = useState<ScoreBucket[]>([]);
    const [cost, setCost] = useState<Cost | null>(null);

    useEffect(() => {
        const t = localStorage.getItem("welyne_token");
        setToken(t);
        if (t) load(t);
    }, []);

    async function load(t: string) {
        const [s, f, ti, sl, sc, co] = await Promise.all([
            apiFetch("/reports/sources", t),
            apiFetch("/reports/funnel", t),
            apiFetch("/reports/timing", t),
            apiFetch("/reports/sla", t),
            apiFetch("/reports/score-distribution", t),
            apiFetch("/reports/cost", t),
        ]);
        setSources(s.sources); setFunnel(f); setTiming(ti.stages);
        setSla(sl); setBuckets(sc.buckets); setCost(co);
    }

    if (!token) return <p style={{ color: "var(--ink-soft)" }}>Connectez-vous d&apos;abord.</p>;

    const maxBucket = Math.max(1, ...buckets.map((b) => b.count));
    const maxTiming = Math.max(1, ...timing.map((s) => s.avg_hours));

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                <h1 style={{ fontSize: 24 }}>Reporting (A9)</h1>
                <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => downloadFile("/reports/export.csv", token, "welyne-applications.csv")} style={{ fontSize: 13 }}>
                        Export CSV
                    </button>
                    <button onClick={() => downloadFile("/reports/export.pdf", token, "welyne-reporting.pdf")} style={{ fontSize: 13 }}>
                        Export PDF
                    </button>
                </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                {/* 1. Funnel */}
                {funnel && (
                    <div className="card">
                        <h3 style={{ marginBottom: 8 }}>Funnel ({funnel.total} candidatures)</h3>
                        <table>
                            <thead><tr><th>Statut</th><th>Nombre</th></tr></thead>
                            <tbody>
                                {Object.entries(funnel.by_status).map(([status, count]) => (
                                    <tr key={status}><td><span className={`badge ${status}`}>{status}</span></td><td>{count}</td></tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* 2. Efficacité par source */}
                <div className="card">
                    <h3 style={{ marginBottom: 8 }}>Efficacité par source</h3>
                    <table>
                        <thead><tr><th>Source</th><th>Total</th><th>Convertis</th><th>Taux</th></tr></thead>
                        <tbody>
                            {sources.map((s) => (
                                <tr key={s.source}>
                                    <td>{s.source}</td><td>{s.total}</td><td>{s.converted}</td>
                                    <td>{(s.conversion_rate * 100).toFixed(1)}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* 3. Délais moyens par étape */}
                <div className="card">
                    <h3 style={{ marginBottom: 4 }}>Délais moyens par étape</h3>
                    <p style={{ fontSize: 12, marginBottom: 12 }}>Temps moyen (heures) pour franchir chaque étape du funnel.</p>
                    {timing.length === 0 && <p style={{ fontSize: 13 }}>Pas encore assez de données.</p>}
                    {timing.map((s) => <Bar key={s.stage} label={s.stage} value={s.avg_hours} max={maxTiming} suffix="h" />)}
                </div>

                {/* 4. SLA parsing/scoring */}
                {sla && (
                    <div className="card">
                        <h3 style={{ marginBottom: 8 }}>SLA parsing / scoring (A3/A4)</h3>
                        <table>
                            <thead><tr><th>Étape</th><th>Moyenne</th><th>P95</th><th>n</th></tr></thead>
                            <tbody>
                                <tr><td>Parsing</td><td>{sla.parsing.avg_min} min</td><td>{sla.parsing.p95_min} min</td><td>{sla.parsing.n}</td></tr>
                                <tr><td>Scoring</td><td>{sla.scoring.avg_min} min</td><td>{sla.scoring.p95_min} min</td><td>{sla.scoring.n}</td></tr>
                            </tbody>
                        </table>
                    </div>
                )}

                {/* 5. Distribution des scores */}
                <div className="card">
                    <h3 style={{ marginBottom: 12 }}>Distribution des scores</h3>
                    {buckets.map((b) => <Bar key={b.range} label={b.range} value={b.count} max={maxBucket} />)}
                </div>

                {/* 6. Coût tokens estimé */}
                {cost && (
                    <div className="card">
                        <h3 style={{ marginBottom: 4 }}>Coût tokens estimé</h3>
                        <p style={{ fontSize: 12, marginBottom: 12 }}>
                            Fenêtre de {cost.window_days} jours — estimation globale, pas un ledger exact par candidat.
                        </p>
                        <table>
                            <tbody>
                                <tr><td>Tokens totaux</td><td className="mono">{cost.total_tokens.toLocaleString()}</td></tr>
                                <tr><td>Coût estimé</td><td className="mono">${cost.total_cost_usd_estimate}</td></tr>
                                <tr><td>Embauches (fenêtre)</td><td className="mono">{cost.hires}</td></tr>
                                <tr><td>Coût estimé / embauche</td><td className="mono">{cost.cost_usd_per_hire_estimate != null ? `$${cost.cost_usd_per_hire_estimate}` : "—"}</td></tr>
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <p style={{ fontSize: 12, marginTop: 20 }}>
                Un digest de ce rapport est envoyé automatiquement chaque lundi aux comptes admin (§6-A9).
            </p>
        </div>
    );
}