"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";

type JobSpec = { missions?: string[]; must_have?: string[]; seniority?: string; location?: string };
type Job = { id: string; title: string; status: string; job_spec: JobSpec; weights: Record<string, number> };
type App = { id: string; job_id: string };

type StatusFilter = "all" | "published" | "draft" | "closed";

function hasSpec(spec: JobSpec) {
  return (spec?.missions?.length ?? 0) > 0 || (spec?.must_have?.length ?? 0) > 0;
}

// Piste d'avancement par offre : reflète les deux vraies étapes que le
// pipeline traverse réellement (A1 génère la fiche, puis publication) —
// pas une décoration, chaque point correspond à un champ réel de l'offre.
function JobTrack({ job }: { job: Job }) {
  const specDone = hasSpec(job.job_spec);
  const published = job.status === "published" || job.status === "closed";
  return (
    <div className="job-card-track" aria-hidden>
      <span className="job-track-step">
        <span className={`job-track-dot${specDone ? " on" : " pulse"}`} />
        Fiche
      </span>
      <span className={`job-track-line${specDone ? " on" : ""}`} />
      <span className="job-track-step">
        <span className={`job-track-dot${published ? " on" : specDone ? " pulse" : ""}`} />
        Publiée
      </span>
    </div>
  );
}

function JobCardMenu({ job, canWrite, candidateCount, onAction }: {
  job: Job; canWrite: boolean; candidateCount: number;
  onAction: (action: "duplicate" | "close" | "reopen" | "delete") => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  if (!canWrite) return null;

  function stop(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
  }

  return (
    <div className="job-card-menu-wrap" ref={ref}>
      <button
        className="job-card-menu-btn"
        onClick={(e) => { stop(e); setOpen((o) => !o); }}
        aria-label="Actions sur l'offre"
      >
        ⋯
      </button>
      {open && (
        <div className="job-card-menu" onClick={stop}>
          <button onClick={() => { setOpen(false); onAction("duplicate"); }}>Dupliquer</button>
          {job.status === "closed" ? (
            <button onClick={() => { setOpen(false); onAction("reopen"); }}>Réactiver</button>
          ) : (
            <button onClick={() => { setOpen(false); onAction("close"); }}>Archiver</button>
          )}
          <button
            className="danger"
            disabled={candidateCount > 0}
            title={candidateCount > 0 ? "Offre avec candidatures — archivez-la plutôt" : undefined}
            onClick={() => { setOpen(false); onAction("delete"); }}
          >
            Supprimer
          </button>
        </div>
      )}
    </div>
  );
}

function JobCard({ job, candidateCount, canWrite, onAction }: {
  job: Job; candidateCount: number; canWrite: boolean;
  onAction: (job: Job, action: "duplicate" | "close" | "reopen" | "delete") => void;
}) {
  const spec = job.job_spec || {};
  return (
    <div
      className={`job-card${job.status === "closed" ? " closed" : ""}`}
      role="link"
      tabIndex={0}
      onClick={() => (window.location.href = `/jobs/${job.id}`)}
      onKeyDown={(e) => e.key === "Enter" && (window.location.href = `/jobs/${job.id}`)}
      style={{ cursor: "pointer" }}
    >
      <div className="job-card-top">
        <div className="job-card-title">{job.title}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span className={`badge ${job.status}`}>{job.status}</span>
          <JobCardMenu
            job={job}
            canWrite={canWrite}
            candidateCount={candidateCount}
            onAction={(action) => onAction(job, action)}
          />
        </div>
      </div>

      {(spec.seniority || spec.location) && (
        <div className="job-card-meta">
          {spec.seniority && <span className="job-chip">{spec.seniority}</span>}
          {spec.location && <span className="job-chip" title={spec.location}>{spec.location}</span>}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <JobTrack job={job} />
        {candidateCount > 0 && (
          <span className="job-card-candidates">
            {candidateCount} candidat{candidateCount !== 1 ? "s" : ""}
          </span>
        )}
      </div>
    </div>
  );
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [candidateCounts, setCandidateCounts] = useState<Record<string, number>>({});
  const [title, setTitle] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("welyne_token");
    setToken(t);
    setRole(localStorage.getItem("welyne_role"));
    if (t) load(t);
  }, []);

  async function load(t: string) {
    const [jobsData, appsData]: [Job[], App[]] = await Promise.all([
      apiFetch("/jobs", t),
      apiFetch("/applications", t).catch(() => []),
    ]);
    setJobs(jobsData);
    const counts: Record<string, number> = {};
    for (const a of appsData) counts[a.job_id] = (counts[a.job_id] || 0) + 1;
    setCandidateCounts(counts);
  }

  async function createJob(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setCreating(true);
    try {
      const job = await apiFetch("/jobs", token, { method: "POST", body: JSON.stringify({ title }) });
      setTitle("");
      window.location.href = `/jobs/${job.id}`;
    } catch (err: any) {
      setError(err?.message || "Une erreur est survenue.");
    } finally {
      setCreating(false);
    }
  }

  async function handleAction(job: Job, action: "duplicate" | "close" | "reopen" | "delete") {
    if (!token) return;
    setActionError(null);
    try {
      if (action === "duplicate") {
        const clone = await apiFetch(`/jobs/${job.id}/duplicate`, token, { method: "POST" });
        window.location.href = `/jobs/${clone.id}`;
        return;
      }
      if (action === "close") {
        await apiFetch(`/jobs/${job.id}/close`, token, { method: "POST" });
      }
      if (action === "reopen") {
        await apiFetch(`/jobs/${job.id}/reopen`, token, { method: "POST" });
      }
      if (action === "delete") {
        if (!confirm(`Supprimer définitivement "${job.title}" ? Cette action est irréversible.`)) return;
        await apiFetch(`/jobs/${job.id}`, token, { method: "DELETE" });
      }
      await load(token);
    } catch (err: any) {
      setActionError(err?.message || "Une erreur est survenue.");
    }
  }

  const filtered = useMemo(() => {
    return jobs.filter((j) => {
      if (statusFilter !== "all" && j.status !== statusFilter) return false;
      if (statusFilter === "all" && j.status === "closed") return false; // archivées masquées par défaut
      if (search.trim() && !j.title.toLowerCase().includes(search.trim().toLowerCase())) return false;
      return true;
    });
  }, [jobs, search, statusFilter]);

  const publishedCount = jobs.filter((j) => j.status === "published").length;
  const draftCount = jobs.filter((j) => j.status === "draft").length;
  const closedCount = jobs.filter((j) => j.status === "closed").length;

  if (!token) return <p style={{ color: "var(--ink-soft)" }}>Connectez-vous d'abord.</p>;

  const canCreate = role === "admin" || role === "recruteur";

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div>
          <span className="eyebrow">Agent A1 · Publication</span>
          <h1 style={{ fontSize: 24 }}>Offres</h1>
          <p style={{ color: "var(--ink-soft)", fontSize: 14, margin: "4px 0 0" }}>
            {jobs.length} offre{jobs.length !== 1 ? "s" : ""} · {publishedCount} publiée{publishedCount !== 1 ? "s" : ""} · {draftCount} brouillon{draftCount !== 1 ? "s" : ""}
            {closedCount > 0 ? ` · ${closedCount} archivée${closedCount !== 1 ? "s" : ""}` : ""}
          </p>
        </div>
      </div>

      {canCreate && (
        <form onSubmit={createJob} className="card" style={{ maxWidth: 460, marginBottom: 28 }}>
          <span className="eyebrow" style={{ marginBottom: 2 }}>Étape 1 / 2</span>
          <label>Nouvelle offre — intitulé</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="ex. Data Scientist Senior"
            required
          />
          <p style={{ color: "var(--ink-faint)", fontSize: 12.5, margin: "6px 0 0" }}>
            Sur la page suivante : collez le brief du poste, l'agent A1 en tire missions, critères et pondérations en quelques secondes.
          </p>
          <button type="submit" disabled={creating}>{creating ? "Création…" : "Créer l'offre"}</button>
          {error && <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 8 }}>{error}</p>}
        </form>
      )}
      {!canCreate && (
        <p style={{ color: "var(--ink-soft)", fontSize: 14, marginBottom: 28 }}>
          Votre rôle ({role ?? "inconnu"}) permet uniquement la consultation des offres.
        </p>
      )}

      {actionError && (
        <p style={{ color: "var(--coral)", fontSize: 13, marginBottom: 16, background: "var(--coral-soft)", padding: "8px 12px", borderRadius: 8 }}>
          {actionError}
        </p>
      )}

      {jobs.length > 0 && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button className={`filter-chip${statusFilter === "all" ? " active" : ""}`} onClick={() => setStatusFilter("all")}>Toutes</button>
            <button className={`filter-chip${statusFilter === "published" ? " active" : ""}`} onClick={() => setStatusFilter("published")}>Publiées ({publishedCount})</button>
            <button className={`filter-chip${statusFilter === "draft" ? " active" : ""}`} onClick={() => setStatusFilter("draft")}>Brouillons ({draftCount})</button>
            {closedCount > 0 && (
              <button className={`filter-chip${statusFilter === "closed" ? " active" : ""}`} onClick={() => setStatusFilter("closed")}>Archivées ({closedCount})</button>
            )}
          </div>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher un intitulé…"
            style={{ maxWidth: 240, margin: 0 }}
          />
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--ink-soft)" }}>
          {jobs.length === 0 ? "Aucune offre pour le moment — créez-en une ci-dessus." : "Aucune offre ne correspond à ce filtre."}
        </div>
      ) : (
        <div className="job-grid">
          {filtered.map((j) => (
            <JobCard
              key={j.id}
              job={j}
              candidateCount={candidateCounts[j.id] || 0}
              canWrite={canCreate}
              onAction={handleAction}
            />
          ))}
        </div>
      )}
    </div>
  );
}