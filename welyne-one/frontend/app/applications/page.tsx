"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type App = { id: string; job_id: string; candidate_id: string; status: string; source: string };

export default function ApplicationsPage() {
  const [apps, setApps] = useState<App[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [jobId, setJobId] = useState("");
  const [candidateName, setCandidateName] = useState("");
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("welyne_token");
    setToken(t);
    if (t) load(t);
  }, []);

  async function load(t: string) {
    const data = await apiFetch("/applications", t);
    setApps(data);
  }

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !file) return;
    const form = new FormData();
    form.append("job_id", jobId);
    form.append("candidate_full_name", candidateName);
    form.append("file", file);
    await apiFetch("/applications/upload", token, { method: "POST", body: form });
    load(token);
  }

  if (!token) return <p>Connectez-vous d&apos;abord.</p>;

  return (
    <div>
      <h2>Candidatures</h2>
      <form onSubmit={upload} style={{ maxWidth: 420 }}>
        <label>ID de l&apos;offre</label>
        <input value={jobId} onChange={(e) => setJobId(e.target.value)} required />
        <label>Nom du candidat</label>
        <input value={candidateName} onChange={(e) => setCandidateName(e.target.value)} required />
        <label>CV (PDF/DOCX)</label>
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
        <button type="submit">Téléverser (lance A3 → A4)</button>
      </form>

      <table>
        <thead>
          <tr><th>Statut</th><th>Source</th><th>ID candidature</th></tr>
        </thead>
        <tbody>
          {apps.map((a) => (
            <tr key={a.id}>
              <td><span className={`badge ${a.status}`}>{a.status}</span></td>
              <td>{a.source}</td>
              <td style={{ fontSize: 11, color: "#888" }}>{a.id}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p style={{ fontSize: 12, color: "#666" }}>
        Le parsing (A3) puis le scoring (A4) tournent en tâche de fond (Celery) — actualisez la page après quelques secondes.
      </p>
    </div>
  );
}
