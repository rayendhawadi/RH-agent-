"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import SourcingPanel from "@/components/sourcingpanel";

type Job = { id: string; title: string; status: string };

export default function SourcingPage() {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = localStorage.getItem("welyne_token");
    const r = localStorage.getItem("welyne_role");
    setToken(t);
    setRole(r);
    if (t) {
      apiFetch("/jobs", t)
        .then((data: Job[]) => {
          const active = data.filter((j) => j.status !== "closed");
          setJobs(active);
          if (active.length > 0) setSelectedJobId(active[0].id);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  if (!token) return <p style={{ color: "var(--ink-soft)" }}>Connectez-vous d&apos;abord.</p>;

  const canWrite = role === "admin" || role === "recruteur";
  const selectedJob = jobs.find((j) => j.id === selectedJobId);

  return (
    <div>
      {/* ── En-tête ── */}
      <div style={{ marginBottom: 24 }}>
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
          Agent A2 · Sourcing
        </div>
        <h1 style={{ 
          fontSize: "clamp(2.5rem, 6vw, 4.5rem)", 
          fontWeight: 800, 
          lineHeight: 1, 
          letterSpacing: "-0.04em", 
          margin: 0 
        }}>
          Sourcing
        </h1>
        <p style={{ color: "var(--ink-soft)", fontSize: 15, margin: "12px 0 28px" }}>
          Génération de requêtes de recherche, messages d&apos;approche et import de profils externes.
        </p>
      </div>

      {loading && <p style={{ color: "var(--ink-soft)" }}>Chargement des offres…</p>}

      {!loading && jobs.length === 0 && (
        <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--ink-soft)" }}>
          Aucune offre active. Créez d&apos;abord une offre dans{" "}
          <a href="/jobs" style={{ color: "var(--accent)" }}>Offres</a>.
        </div>
      )}

      {!loading && jobs.length > 0 && (
        <>
          {/* ── Sélecteur d'offre ── */}
          <div className="card" style={{ maxWidth: 520, marginBottom: 28, padding: "18px 20px" }}>
            <label style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--ink-faint)", display: "block", marginBottom: 8 }}>
              Offre cible
            </label>
            <select
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              style={{
                width: "100%",
                background: "var(--surface)",
                border: "1px solid var(--line)",
                borderRadius: 8,
                padding: "10px 13px",
                fontSize: 14,
                color: "var(--ink)",
                cursor: "pointer",
                appearance: "none",
                backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E\")",
                backgroundRepeat: "no-repeat",
                backgroundPosition: "right 13px center",
                paddingRight: 36,
              }}
            >
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title} — {j.status}
                </option>
              ))}
            </select>
            {selectedJob && (
              <p style={{ fontSize: 12, color: "var(--ink-faint)", marginTop: 8, marginBottom: 0 }}>
                ID : <code style={{ fontFamily: "monospace", fontSize: 11 }}>{selectedJob.id}</code>
              </p>
            )}
          </div>

          {/* ── Panel sourcing ── */}
          {selectedJobId && token && (
            <SourcingPanel jobId={selectedJobId} token={token} canWrite={canWrite} />
          )}
        </>
      )}
    </div>
  );
}
