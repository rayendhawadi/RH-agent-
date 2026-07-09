"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type Job = { id: string; title: string; status: string };

export default function JobsPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [title, setTitle] = useState("");
    const [token, setToken] = useState<string | null>(null);

    useEffect(() => {
        const t = localStorage.getItem("welyne_token");
        setToken(t);
        if (t) load(t);
    }, []);

    async function load(t: string) {
        const data = await apiFetch("/jobs", t);
        setJobs(data);
    }

    async function createJob(e: React.FormEvent) {
        e.preventDefault();
        if (!token) return;
        await apiFetch("/jobs", token, { method: "POST", body: JSON.stringify({ title }) });
        setTitle("");
        load(token);
    }

    if (!token) return <p style={{ color: "var(--ink-soft)" }}>Connectez-vous d&apos;abord.</p>;

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24 }}>Offres</h1>
                    <p style={{ color: "var(--ink-soft)", fontSize: 14, margin: "4px 0 0" }}>
                        {jobs.length} offre{jobs.length !== 1 ? "s" : ""} publiée{jobs.length !== 1 ? "s" : ""} sur la plateforme
                    </p>
                </div>
            </div>

            <form onSubmit={createJob} className="card" style={{ maxWidth: 420, marginBottom: 28 }}>
                <label>Nouvelle offre — intitulé</label>
                <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="ex. Data Scientist Senior"
                    required
                />
                <button type="submit">Créer l&apos;offre</button>
            </form>

            <div className="card" style={{ padding: 0 }}>
                <table>
                    <thead>
                        <tr><th>Intitulé</th><th>Statut</th><th>ID</th></tr>
                    </thead>
                    <tbody>
                        {jobs.map((j) => (
                            <tr key={j.id}>
                                <td style={{ fontWeight: 500 }}><a href={`/jobs/${j.id}`} style={{ color: "var(--indigo)" }}>{j.title}</a></td>
                                <td><span className={`badge ${j.status}`}>{j.status}</span></td>
                                <td className="mono" style={{ fontSize: 12, color: "var(--ink-soft)" }}>{j.id}</td>
                            </tr>
                        ))}
                        {jobs.length === 0 && (
                            <tr><td colSpan={3} style={{ color: "var(--ink-soft)", textAlign: "center", padding: 32 }}>
                                Aucune offre pour le moment — créez-en une ci-dessus.
                            </td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}