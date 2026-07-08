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

  if (!token) return <p>Connectez-vous d&apos;abord.</p>;

  return (
    <div>
      <h2>Offres</h2>
      <form onSubmit={createJob} style={{ maxWidth: 400 }}>
        <label>Nouvelle offre (intitulé)</label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        <button type="submit">Créer</button>
      </form>

      <table>
        <thead>
          <tr><th>Intitulé</th><th>Statut</th><th>ID</th></tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={j.id}>
              <td>{j.title}</td>
              <td><span className="badge">{j.status}</span></td>
              <td style={{ fontSize: 11, color: "#888" }}>{j.id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
