"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type SourceStat = {
    source: string;
    total: number;
    converted: number;
    conversion_rate: number;
    by_status: Record<string, number>;
};

export default function ReportsPage() {
    const [token, setToken] = useState<string | null>(null);
    const [sources, setSources] = useState<SourceStat[]>([]);
    const [funnel, setFunnel] = useState<{ total: number; by_status: Record<string, number> } | null>(null);

    useEffect(() => {
        const t = localStorage.getItem("welyne_token");
        setToken(t);
        if (t) load(t);
    }, []);

    async function load(t: string) {
        const [s, f] = await Promise.all([
            apiFetch("/reports/sources", t),
            apiFetch("/reports/funnel", t),
        ]);
        setSources(s.sources);
        setFunnel(f);
    }

    if (!token) return <p style={{ color: "var(--ink-soft)" }}>Connectez-vous d&apos;abord.</p>;

    return (
        <div>
            <h1 style={{ fontSize: 24, marginBottom: 20 }}>Reporting (A9)</h1>

            <div className="card" style={{ marginBottom: 20 }}>
                <h3 style={{ marginBottom: 8 }}>Efficacité par source</h3>
                <p style={{ fontSize: 12, color: "var(--ink-soft)", marginBottom: 12 }}>
                    Taux de conversion = candidatures ayant dépassé le premier tri (SHORTLISTED et au-delà) / total par source.
                    Permet de comparer le sourcing manuel LinkedIn (<code>linkedin_assist</code>) aux autres canaux.
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>Source</th>
                            <th>Total</th>
                            <th>Convertis</th>
                            <th>Taux</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sources.map((s) => (
                            <tr key={s.source}>
                                <td>{s.source}</td>
                                <td>{s.total}</td>
                                <td>{s.converted}</td>
                                <td>{(s.conversion_rate * 100).toFixed(1)}%</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {funnel && (
                <div className="card">
                    <h3 style={{ marginBottom: 8 }}>Funnel global ({funnel.total} candidatures)</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Statut</th>
                                <th>Nombre</th>
                            </tr>
                        </thead>
                        <tbody>
                            {Object.entries(funnel.by_status).map(([status, count]) => (
                                <tr key={status}>
                                    <td><span className={`badge ${status}`}>{status}</span></td>
                                    <td>{count}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}