"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import PrescreenPanel from "@/components/PrescreenPanel";
import InterviewPanel from "@/components/InterviewPanel";
import OnboardingPanel from "@/components/OnboardingPanel";
import "./pipeline.css";

type App = {
  id: string;
  job_id: string;
  candidate_id: string;
  candidate_name?: string | null;
  status: string;
  source: string;
  archived_at: string | null;
};

// State machine réelle du PDF §2.1
const STAGES = [
  "RECEIVED", "PARSED", "SCORED", "SHORTLISTED", "PRESCREENING", "PRESCREENED",
  "INTERVIEW_SCHEDULED", "INTERVIEWED", "OFFER", "HIRED", "ONBOARDING",
];
const OFF_TRACK = new Set(["DECLINED", "DECLINE_PENDING", "POOL"]);

function phaseOf(stage: string): "intake" | "selection" | "interview" | "closing" | "declined" {
  if (["RECEIVED", "PARSED", "SCORED"].includes(stage)) return "intake";
  if (["SHORTLISTED", "PRESCREENING", "PRESCREENED"].includes(stage)) return "selection";
  if (["INTERVIEW_SCHEDULED", "INTERVIEWED"].includes(stage)) return "interview";
  if (["DECLINED", "DECLINE_PENDING"].includes(stage)) return "declined";
  return "closing";
}

const PHASE_LABEL: Record<string, string> = {
  intake: "Traitement",
  selection: "Sélection",
  interview: "Entretien",
  closing: "Conclusion",
  declined: "Décliné",
};

const STATUS_LABEL: Record<string, string> = {
  RECEIVED: "Reçu",
  PARSED: "Analysé",
  SCORED: "Scoré",
  SHORTLISTED: "Shortlisté",
  PRESCREENING: "Pré-qualification",
  PRESCREENED: "Pré-qualifié",
  INTERVIEW_SCHEDULED: "Entretien planifié",
  INTERVIEWED: "Interviewé",
  OFFER: "Offre envoyée",
  HIRED: "Embauché",
  ONBOARDING: "Onboarding",
  DECLINED: "Décliné",
  DECLINE_PENDING: "Rejet en attente",
  POOL: "Vivier",
};

// Rail de progression horizontal compact
function StageRail({ status }: { status: string }) {
  const phase = phaseOf(status);

  if (OFF_TRACK.has(status)) {
    return (
      <div>
        <span className={`p-badge phase-${phase}`}>
          {STATUS_LABEL[status] ?? status}
        </span>
      </div>
    );
  }

  const idx = STAGES.indexOf(status);
  return (
    <div>
      {/* Rail */}
      <div className="p-rail">
        {STAGES.map((s, i) => (
          <span
            key={s}
            className={`p-seg${i <= idx ? ` done phase-${phaseOf(s)}` : ""}`}
            title={STATUS_LABEL[s] ?? s}
          />
        ))}
      </div>
      {/* Badge statut */}
      <span className={`p-badge phase-${phase}`}>
        <span className="p-idx" style={{ fontFamily: "IBM Plex Mono", fontSize: 9, opacity: 0.7, marginRight: 2 }}>
          {String(idx + 1).padStart(2, "0")}
        </span>
        {STATUS_LABEL[status] ?? status}
      </span>
    </div>
  );
}

function useCountUp(target: number, ms = 600) {
  const [n, setN] = useState(0);
  useEffect(() => {
    let raf: number;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      setN(Math.round(target * (1 - Math.pow(1 - t, 3))));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return n;
}

export default function ApplicationsPage() {
  const [apps, setApps] = useState<App[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [jobId, setJobId] = useState("");
  const [candidateName, setCandidateName] = useState("");
  const [candidateEmail, setCandidateEmail] = useState("");
  const [candidatePhone, setCandidatePhone] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);

  useEffect(() => {
    const t = localStorage.getItem("welyne_token");
    setToken(t);
    setRole(localStorage.getItem("welyne_role"));
    if (t) load(t);
  }, []);

  useEffect(() => {
    if (token) load(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showArchived]);

  async function load(t: string) {
    const data = await apiFetch(`/applications${showArchived ? "?include_archived=true" : ""}`, t);
    setApps(data);
  }

  async function archiveApp(id: string) {
    if (!token) return;
    setBusyId(id);
    try { await apiFetch(`/applications/${id}/archive`, token, { method: "POST" }); await load(token); }
    finally { setBusyId(null); }
  }

  async function unarchiveApp(id: string) {
    if (!token) return;
    setBusyId(id);
    try { await apiFetch(`/applications/${id}/unarchive`, token, { method: "POST" }); await load(token); }
    finally { setBusyId(null); }
  }

  async function deleteApp(id: string) {
    if (!token) return;
    if (!confirm("Supprimer définitivement cette candidature ? Cette action efface aussi son historique, ses scores et ses conversations, et ne peut pas être annulée.")) return;
    setBusyId(id);
    try { await apiFetch(`/applications/${id}`, token, { method: "DELETE" }); await load(token); }
    finally { setBusyId(null); }
  }

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !file) return;
    setUploadError(null);
    const form = new FormData();
    form.append("job_id", jobId.trim());
    form.append("candidate_full_name", candidateName.trim());
    if (candidateEmail) form.append("candidate_email", candidateEmail);
    if (candidatePhone) form.append("candidate_phone", candidatePhone);
    form.append("file", file);
    try {
      await apiFetch("/applications/upload", token, { method: "POST", body: form });
      load(token);
    } catch (err: any) {
      setUploadError(err?.message || "Une erreur est survenue.");
    }
  }

  async function validateDecline(id: string) {
    if (!token) return;
    if (!confirm("Confirmer le rejet ? L'email de rejet sera envoyé au candidat après validation.")) return;
    setBusyId(id);
    try {
      await apiFetch(`/applications/${id}/validate-decline`, token, { method: "POST", body: JSON.stringify({ reason: "" }) });
      await load(token);
    } finally { setBusyId(null); }
  }

  async function invitePrescreen(id: string) {
    if (!token) return;
    setBusyId(id);
    try { await apiFetch(`/applications/${id}/invite-prescreen`, token, { method: "POST" }); await load(token); }
    finally { setBusyId(null); }
  }

  async function makeOffer(id: string) {
    if (!token) return;
    setBusyId(id);
    try { await apiFetch(`/applications/${id}/make-offer`, token, { method: "POST" }); await load(token); }
    finally { setBusyId(null); }
  }

  async function confirmHire(id: string) {
    if (!token) return;
    if (!confirm("Confirmer l'embauche ? Ceci est une porte humaine explicite (§7).")) return;
    setBusyId(id);
    try {
      await apiFetch(`/applications/${id}/confirm-hire`, token, { method: "POST", body: JSON.stringify({ note: "" }) });
      await load(token);
    } finally { setBusyId(null); }
  }

  async function startOnboarding(id: string) {
    if (!token) return;
    setBusyId(id);
    try { await apiFetch(`/applications/${id}/start-onboarding`, token, { method: "POST" }); await load(token); }
    finally { setBusyId(null); }
  }

  const displayedCount = useCountUp(apps.length);

  if (!token) return <p style={{ color: "var(--ink-soft)" }}>Connectez-vous d&apos;abord.</p>;

  const canWrite = role === "admin" || role === "recruteur";
  const pendingDeclines = apps.filter((a) => a.status === "DECLINE_PENDING");
  const others = apps.filter((a) => a.status !== "DECLINE_PENDING");

  const tickerCounts = [
    ["Shortlistés", apps.filter((a) => a.status === "SHORTLISTED").length],
    ["Pré-qualification", apps.filter((a) => a.status === "PRESCREENING").length],
    ["Entretiens planifiés", apps.filter((a) => a.status === "INTERVIEW_SCHEDULED").length],
    ["Offres en attente", apps.filter((a) => a.status === "OFFER").length],
    ["Embauchés", apps.filter((a) => a.status === "HIRED").length],
    ["Rejets à valider", pendingDeclines.length],
  ] as const;

  function actionFor(a: App) {
    if (!canWrite) return null;
    const busy = busyId === a.id;
    switch (a.status) {
      case "SHORTLISTED":
        return (
          <button className="p-action-btn primary" onClick={() => invitePrescreen(a.id)} disabled={busy}>
            {busy ? "Envoi…" : "✉ Inviter (A5)"}
          </button>
        );
      case "PRESCREENING":
        return <PrescreenPanel applicationId={a.id} token={token!} />;
      case "PRESCREENED":
      case "INTERVIEW_SCHEDULED":
        return <InterviewPanel applicationId={a.id} token={token!} />;
      case "INTERVIEWED":
        return (
          <button className="p-action-btn primary" onClick={() => makeOffer(a.id)} disabled={busy}>
            {busy ? "Envoi…" : "📋 Faire une offre"}
          </button>
        );
      case "OFFER":
        return (
          <button className="p-action-btn danger" onClick={() => confirmHire(a.id)} disabled={busy}>
            {busy ? "…" : "✓ Confirmer l'embauche"}
          </button>
        );
      case "HIRED":
        return (
          <button className="p-action-btn primary" onClick={() => startOnboarding(a.id)} disabled={busy}>
            {busy ? "Envoi…" : "🚀 Démarrer l'onboarding"}
          </button>
        );
      case "ONBOARDING":
        return <OnboardingPanel applicationId={a.id} token={token!} canWrite={canWrite} />;
      default:
        return <span style={{ color: "var(--p-text-faint)", fontSize: 12 }}>—</span>;
    }
  }

  return (
    <div className="pipeline">
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
          Agent A3 · A4 · Pipeline
        </div>
        <h1 style={{
          fontSize: "clamp(2.5rem, 6vw, 4.5rem)",
          fontWeight: 800,
          lineHeight: 1,
          letterSpacing: "-0.04em",
          margin: 0
        }}>
          Candidatures
        </h1>
        <p style={{ color: "var(--p-text-soft)", fontSize: 15, margin: "12px 0 0" }}>
          <span className="p-count" style={{ color: "var(--accent)", fontWeight: 700 }}>{displayedCount}</span>{" "}
          candidature{apps.length !== 1 ? "s" : ""} suivie{apps.length !== 1 ? "s" : ""} dans le pipeline
        </p>
      </div>

      {/* ── Ticker ── */}
      <div className="p-ticker" style={{
        marginTop: 32,
        marginBottom: 32,
        padding: "16px 0",
        background: "var(--surface)",
        borderTop: "1px solid var(--line)",
        borderBottom: "1px solid var(--line)",
        display: "flex",
        alignItems: "center",
      }}>
        <div className="p-ticker-track" style={{ display: "inline-flex", alignItems: "center" }}>
          {[...tickerCounts, ...tickerCounts, ...tickerCounts, ...tickerCounts].map(([label, n], i) => (
            <span key={i} style={{
              display: "inline-flex",
              alignItems: "center",
              fontSize: 16,
              fontWeight: 600,
              color: "var(--ink)",
              whiteSpace: "nowrap"
            }}>
              <span style={{ color: "var(--accent)", marginRight: 8, fontWeight: 700 }}>{n}</span>
              {label}
              <span style={{
                color: "var(--accent)",
                margin: "0 24px",
                fontSize: "0.5em",
                transform: "translateY(-1px)"
              }}>♦</span>
            </span>
          ))}
        </div>
      </div>

      {/* ── Toggle archivées ── */}
      <label className="p-toggle-label">
        <input
          type="checkbox"
          checked={showArchived}
          onChange={(e) => setShowArchived(e.target.checked)}
        />
        Afficher les candidatures archivées
      </label>

      {/* ── Formulaire upload ── */}
      {canWrite && (
        <form onSubmit={upload} style={{
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
            marginBottom: 28
          }}>
            Nouvelle candidature
          </span>

          {/* Champs de saisie stylisés Welyne */}
          {[
            { label: "ID de l'offre", type: "text", value: jobId, setter: setJobId, placeholder: "uuid de l'offre", required: true },
            { label: "Nom du candidat", type: "text", value: candidateName, setter: setCandidateName, placeholder: "ex. Jean Dupont", required: true },
            { label: "Email (canal prioritaire)", type: "email", value: candidateEmail, setter: setCandidateEmail, placeholder: "candidat@example.com", required: false },
            { label: "Téléphone (repli WhatsApp)", type: "text", value: candidatePhone, setter: setCandidatePhone, placeholder: "21612345678", required: false }
          ].map((field, i) => (
            <div key={i} style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--ink-soft)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                {field.label}
              </label>
              <input
                type={field.type}
                value={field.value}
                onChange={(e) => field.setter(e.target.value)}
                placeholder={field.placeholder}
                required={field.required}
                style={{
                  width: "100%",
                  background: "var(--paper)",
                  border: "1px solid var(--line)",
                  borderRadius: 12,
                  padding: "14px 16px",
                  fontSize: 15,
                  color: "var(--ink)",
                  transition: "border-color 0.2s, box-shadow 0.2s",
                  outline: "none",
                  margin: 0
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
            </div>
          ))}

          <div style={{ marginBottom: 32 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--ink-soft)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              CV (PDF / DOCX)
            </label>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
              style={{
                width: "100%",
                background: "var(--paper)",
                border: "1px dashed var(--line)",
                borderRadius: 12,
                padding: "14px 16px",
                fontSize: 14,
                color: "var(--ink)",
                cursor: "pointer",
                outline: "none",
                margin: 0
              }}
            />
          </div>

          <button type="submit" style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
            background: "var(--accent)",
            color: "#fff",
            border: "none",
            borderRadius: 999,
            padding: "16px 24px",
            fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
            fontSize: 13,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.14em",
            cursor: "pointer",
            transition: "transform 0.2s ease, filter 0.2s ease",
            boxShadow: "0 4px 14px rgba(255, 107, 0, 0.25)"
          }}
            onMouseEnter={(e) => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.filter = "brightness(1.1)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.filter = "brightness(1)"; }}
          >
            Téléverser & lancer l'analyse →
          </button>

          <div style={{ display: "flex", gap: 16, marginTop: 24, flexWrap: "wrap", justifyContent: "center" }}>
            <span style={{ fontSize: 11, color: "var(--ink-faint)", display: "flex", alignItems: "center", gap: 6, fontFamily: "monospace", textTransform: "uppercase" }}>
              <span style={{ color: "var(--accent)" }}>▸</span> Parsing A3
            </span>
            <span style={{ fontSize: 11, color: "var(--ink-faint)", display: "flex", alignItems: "center", gap: 6, fontFamily: "monospace", textTransform: "uppercase" }}>
              <span style={{ color: "var(--accent)" }}>▸</span> Scoring A4
            </span>
            <span style={{ fontSize: 11, color: "var(--ink-faint)", display: "flex", alignItems: "center", gap: 6, fontFamily: "monospace", textTransform: "uppercase" }}>
              <span style={{ color: "var(--accent)" }}>▸</span> Dédoublonnage auto
            </span>
          </div>

          {uploadError && <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 16, textAlign: "center", padding: "8px", background: "var(--coral-soft)", borderRadius: 8 }}>{uploadError}</p>}
        </form>
      )}
      {!canWrite && (
        <p style={{ color: "var(--p-text-soft)", fontSize: 14, marginBottom: 28 }}>
          Votre rôle ({role ?? "inconnu"}) permet uniquement la consultation des candidatures.
        </p>
      )}

      {/* ── Section rejets en attente ── */}
      {pendingDeclines.length > 0 && canWrite && (
        <div style={{ marginBottom: 24 }}>
          <h3>⚠ Rejets en attente de validation ({pendingDeclines.length})</h3>
          <p style={{ fontSize: 13, color: "var(--p-text-soft)", marginBottom: 12 }}>
            Aucun email de rejet n&apos;est envoyé automatiquement (§7). Validez ou laissez en attente.
          </p>
          {pendingDeclines.map((a) => (
            <div
              key={a.id}
              className="p-card"
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, padding: "14px 18px" }}
            >
              <div>
                <StageRail status={a.status} />
                <div className="p-mono" style={{ marginTop: 6, fontSize: 12 }}>{a.candidate_name || a.id}</div>
              </div>
              <button
                className="p-action-btn danger"
                onClick={() => validateDecline(a.id)}
                disabled={busyId === a.id}
              >
                {busyId === a.id ? "Envoi…" : "Valider le rejet"}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ── Tableau principal ── */}
      <div className="p-table-wrap" style={{ border: "1px solid var(--line)", borderRadius: 16, overflow: "hidden", background: "var(--surface)" }}>
        <table className="p-table" style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead style={{ background: "rgba(0,0,0,0.2)", borderBottom: "1px solid var(--line)" }}>
            <tr>
              <th style={{ width: 220, fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-soft)", padding: "16px 20px", textAlign: "left" }}>Statut &amp; Progression</th>
              <th style={{ width: 90, fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-soft)", padding: "16px 20px", textAlign: "left" }}>Source</th>
              <th style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-soft)", padding: "16px 20px", textAlign: "left" }}>Candidat</th>
              <th style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-soft)", padding: "16px 20px", textAlign: "left" }}>Action</th>
              {canWrite && <th style={{ width: 180, fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-soft)", padding: "16px 20px", textAlign: "left" }}>Gestion</th>}
            </tr>
          </thead>
          <tbody>
            {others.length === 0 && (
              <tr className="p-empty-row">
                <td colSpan={canWrite ? 5 : 4} style={{ padding: "80px 20px", textAlign: "center" }}>
                  <div style={{ fontSize: 48, marginBottom: 20, opacity: 0.9, filter: "drop-shadow(0 8px 16px rgba(255,107,0,0.15))" }}>📂</div>
                  <div style={{
                    fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
                    fontSize: 13,
                    color: "var(--ink-soft)",
                    letterSpacing: "0.02em"
                  }}>
                    Aucune candidature — téléversez un CV ci-dessus.
                  </div>
                </td>
              </tr>
            )}
            {others.map((a) => (
              <tr key={a.id} className={a.archived_at ? "is-archived" : ""}>
                {/* Statut */}
                <td>
                  <StageRail status={a.status} />
                </td>

                {/* Source */}
                <td>
                  <span className="p-source-chip">{a.source}</span>
                </td>

                {/* Candidat (nom, avec l'ID en infobulle pour référence) */}
                <td>
                  <span className="p-id-cell" title={a.id}>
                    {a.candidate_name || "—"}
                  </span>
                </td>

                {/* Action */}
                <td>
                  <div className="p-actions-cell">
                    {actionFor(a)}
                  </div>
                </td>

                {/* Gestion (admin/recruteur) */}
                {canWrite && (
                  <td className="p-manage-cell">
                    <div className="p-actions-cell">
                      {a.archived_at ? (
                        <button
                          className="p-action-btn ghost"
                          onClick={() => unarchiveApp(a.id)}
                          disabled={busyId === a.id}
                        >
                          Désarchiver
                        </button>
                      ) : (
                        <button
                          className="p-action-btn ghost"
                          onClick={() => archiveApp(a.id)}
                          disabled={busyId === a.id}
                        >
                          Archiver
                        </button>
                      )}
                      {role === "admin" && (
                        <button
                          className="p-action-btn danger"
                          onClick={() => deleteApp(a.id)}
                          disabled={busyId === a.id}
                        >
                          Supprimer
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        marginTop: 32,
        padding: "16px 24px",
        background: "var(--surface)",
        border: "1px solid var(--line)",
        borderRadius: 16
      }}>
        <span style={{ fontSize: 18, filter: "drop-shadow(0 0 8px rgba(255,107,0,0.4))" }}>⚡</span>
        <p style={{ fontSize: 13, color: "var(--ink-soft)", margin: 0 }}>
          Le parsing (A3) puis le scoring (A4) tournent en tâche de fond — actualisez après quelques secondes.
        </p>
      </div>
    </div>
  );
}