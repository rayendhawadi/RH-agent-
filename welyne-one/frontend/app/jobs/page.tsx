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
        <div style={{ marginBottom: 16 }}>
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
            Agent A1 · Publication
          </div>
          <h1 style={{ 
            fontSize: "clamp(2.5rem, 6vw, 4.5rem)", 
            fontWeight: 800, 
            lineHeight: 1, 
            letterSpacing: "-0.04em", 
            margin: 0 
          }}>
            Offres
          </h1>
        </div>
      </div>

      {canCreate && (
        <form onSubmit={createJob} style={{ 
          maxWidth: 540, 
          marginBottom: 48,
          background: "var(--surface)",
          border: "1px solid var(--line)",
          borderRadius: 24,
          padding: "36px 42px",
          position: "relative",
          overflow: "hidden"
        }}>
          {/* Glow subtil d'accentuation */}
          <div style={{ position: "absolute", top: -60, right: -60, width: 180, height: 180, background: "var(--accent)", filter: "blur(90px)", opacity: 0.15, pointerEvents: "none" }} />
          
          <span style={{ 
            fontFamily: "'IBM Plex Mono', ui-monospace, monospace", 
            fontSize: 11, 
            letterSpacing: "0.22em", 
            textTransform: "uppercase", 
            color: "var(--accent)", 
            display: "block", 
            marginBottom: 12 
          }}>
            Étape 1 / 2
          </span>
          
          <h2 style={{ fontSize: 24, marginBottom: 28, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Nouvelle offre — Intitulé
          </h2>
          
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="ex. Data Scientist Senior"
            required
            style={{
              width: "100%",
              background: "var(--paper)",
              border: "1px solid var(--line)",
              borderRadius: 14,
              padding: "16px 20px",
              fontSize: 16,
              color: "var(--ink)",
              marginBottom: 12,
              transition: "border-color 0.2s, box-shadow 0.2s",
              outline: "none"
            }}
            onFocus={(e) => {
              e.target.style.borderColor = "var(--accent)";
              e.target.style.boxShadow = "0 0 0 3px rgba(255, 107, 0, 0.15)";
            }}
            onBlur={(e) => {
              e.target.style.borderColor = "var(--line)";
              e.target.style.boxShadow = "none";
            }}
          />
          
          <p style={{ color: "var(--ink-soft)", fontSize: 13.5, lineHeight: 1.6, margin: "0 0 32px 0" }}>
            Sur la page suivante : collez le brief du poste, l'agent A1 en tirera missions, critères et pondérations en quelques secondes.
          </p>
          
          <button type="submit" disabled={creating} style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--accent)",
            color: "#fff",
            border: "none",
            borderRadius: 999,
            padding: "16px 32px",
            fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
            fontSize: 13,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.14em",
            cursor: creating ? "not-allowed" : "pointer",
            opacity: creating ? 0.7 : 1,
            transition: "transform 0.2s ease, filter 0.2s ease",
            boxShadow: "0 4px 14px rgba(255, 107, 0, 0.25)"
          }}
          onMouseEnter={(e) => { if(!creating) { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.filter = "brightness(1.1)"; } }}
          onMouseLeave={(e) => { if(!creating) { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.filter = "brightness(1)"; } }}
          >
            {creating ? "Création…" : "Créer l'offre →"}
          </button>
          
          {error && <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 16 }}>{error}</p>}
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

      {/* ── Bloc stats welyne.com ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          borderTop: "1px solid var(--line)",
          marginTop: 48,
        }}
      >
        {[
          { value: jobs.length, suffix: "", label: "Offres total" },
          { value: publishedCount, suffix: "", label: "Publiées" },
          { value: draftCount, suffix: "", label: "Brouillons" },
          { value: closedCount, suffix: "", label: "Archivées" },
        ].map((stat, i) => (
          <div
            key={i}
            style={{
              padding: "32px 28px",
              borderRight: i < 3 ? "1px solid var(--line)" : "none",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center"
            }}
          >
            <div
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontSize: "clamp(2.4rem, 5vw, 3.6rem)",
                fontWeight: 800,
                lineHeight: 1,
                letterSpacing: "-0.03em",
                color: "#FF6B00",
                marginBottom: 10,
              }}
            >
              {stat.value}{stat.suffix}
            </div>
            <div
              style={{
                fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
                fontSize: 10,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.2em",
                color: "var(--ink-faint)",
              }}
            >
              {stat.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}