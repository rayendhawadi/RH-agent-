"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import PrescreenPanel from "@/components/PrescreenPanel";
import InterviewPanel from "@/components/InterviewPanel";
import "./pipeline.css";

type App = { id: string; job_id: string; candidate_id: string; status: string; source: string; archived_at: string | null };

// State machine reelle du PDF S2.1 - sert a numeroter le rail de progression.
const STAGES = [
  "RECEIVED", "PARSED", "SCORED", "SHORTLISTED", "PRESCREENING", "PRESCREENED",
  "INTERVIEW_SCHEDULED", "INTERVIEWED", "OFFER", "HIRED", "ONBOARDING",
];
const OFF_TRACK = new Set(["DECLINED", "DECLINE_PENDING", "POOL"]);

// Regroupement en 4 phases narratives (au lieu d'un orange uniforme) : le
// traitement automatique, la décision en attente, le moment humain de
// l'entretien, puis la conclusion. Aide à lire d'un coup d'oeil où en est
// une candidature sans avoir à lire le libellé du statut.
function phaseOf(stage: string): "intake" | "selection" | "interview" | "closing" {
  if (["RECEIVED", "PARSED", "SCORED"].includes(stage)) return "intake";
  if (["SHORTLISTED", "PRESCREENING", "PRESCREENED"].includes(stage)) return "selection";
  if (["INTERVIEW_SCHEDULED", "INTERVIEWED"].includes(stage)) return "interview";
  return "closing"; // OFFER, HIRED, ONBOARDING
}

function StageRail({ status }: { status: string }) {
  if (OFF_TRACK.has(status)) {
    return (
      <div>
        <div className="p-rail"><span className="p-dot declined" /></div>
        <div className="p-stage-label">{status === "DECLINE_PENDING" ? "En attente de validation" : status}</div>
      </div>
    );
  }
  const idx = STAGES.indexOf(status);
  return (
    <div>
      <div className="p-rail">
        {STAGES.map((s, i) => (
          <span
            key={s}
            className={`p-seg ${i < idx ? `done phase-${phaseOf(s)}` : ""} ${i === idx ? "current done phase-" + phaseOf(s) : ""}`}
            title={s}
          />
        ))}
      </div>
      <div className={`p-stage-label phase-${phaseOf(status)}`}>
        <span className="p-idx">{String(idx + 1).padStart(2, "0")}</span>{status}
      </div>
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
      setN(Math.round(target * (1 - Math.pow(1 - t, 3)))); // ease-out
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
    try {
      await apiFetch(`/applications/${id}/archive`, token, { method: "POST" });
      await load(token);
    } finally {
      setBusyId(null);
    }
  }

  async function unarchiveApp(id: string) {
    if (!token) return;
    setBusyId(id);
    try {
      await apiFetch(`/applications/${id}/unarchive`, token, { method: "POST" });
      await load(token);
    } finally {
      setBusyId(null);
    }
  }

  async function deleteApp(id: string) {
    if (!token) return;
    if (!confirm("Supprimer définitivement cette candidature ? Cette action efface aussi son historique, ses scores et ses conversations, et ne peut pas être annulée.")) return;
    setBusyId(id);
    try {
      await apiFetch(`/applications/${id}`, token, { method: "DELETE" });
      await load(token);
    } finally {
      setBusyId(null);
    }
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

  // Ticker : compte réel par statut clé, pas décoratif.
  const tickerCounts = [
    ["Shortlistés", apps.filter((a) => a.status === "SHORTLISTED").length],
    ["En pré-qualification", apps.filter((a) => a.status === "PRESCREENING").length],
    ["Entretiens planifiés", apps.filter((a) => a.status === "INTERVIEW_SCHEDULED").length],
    ["Offres en attente", apps.filter((a) => a.status === "OFFER").length],
    ["Embauchés", apps.filter((a) => a.status === "HIRED").length],
    ["Rejets à valider", pendingDeclines.length],
  ] as const;

  function actionFor(a: App) {
    if (!canWrite) return null;
    switch (a.status) {
      case "SHORTLISTED":
        return <button onClick={() => invitePrescreen(a.id)} disabled={busyId === a.id}>{busyId === a.id ? "Envoi…" : "Inviter (A5)"}</button>;
      case "PRESCREENING":
        return <PrescreenPanel applicationId={a.id} token={token!} />;
      case "PRESCREENED":
      case "INTERVIEW_SCHEDULED":
        return <InterviewPanel applicationId={a.id} token={token!} />;
      case "INTERVIEWED":
        return <button onClick={() => makeOffer(a.id)} disabled={busyId === a.id}>{busyId === a.id ? "Envoi…" : "Faire une offre"}</button>;
      case "OFFER":
        return <button className="p-danger" onClick={() => confirmHire(a.id)} disabled={busyId === a.id}>{busyId === a.id ? "…" : "Confirmer l'embauche"}</button>;
      case "HIRED":
        return <button onClick={() => startOnboarding(a.id)} disabled={busyId === a.id}>{busyId === a.id ? "Envoi…" : "Démarrer l'onboarding"}</button>;
      default:
        return null;
    }
  }

  return (
    <div className="pipeline">
      <h1>Candidatures</h1>
      <p style={{ color: "var(--p-muted)", fontSize: 14, margin: "6px 0 0" }}>
        <span className="p-count">{displayedCount}</span> candidature{apps.length !== 1 ? "s" : ""} suivie{apps.length !== 1 ? "s" : ""} dans le pipeline
      </p>

      <div className="p-ticker">
        <div className="p-ticker-track">
          {[...tickerCounts, ...tickerCounts].map(([label, n], i) => (
            <span className="p-ticker-item" key={i}><b>{n}</b> {label}</span>
          ))}
        </div>
      </div>

      <label style={{ display: "flex", alignItems: "center", gap: 8, margin: "0 0 20px", cursor: "pointer", width: "fit-content" }}>
        <input
          type="checkbox"
          checked={showArchived}
          onChange={(e) => setShowArchived(e.target.checked)}
          style={{ width: "auto", margin: 0 }}
        />
        <span style={{ fontSize: 13, color: "var(--p-muted)", textTransform: "none", letterSpacing: 0 }}>
          Afficher les candidatures archivées
        </span>
      </label>

      {canWrite && (
        <form onSubmit={upload} className="p-card" style={{ maxWidth: 440, marginBottom: 28 }}>
          <label>ID de l&apos;offre</label>
          <input value={jobId} onChange={(e) => setJobId(e.target.value)} placeholder="uuid de l'offre" required />
          <label>Nom du candidat</label>
          <input value={candidateName} onChange={(e) => setCandidateName(e.target.value)} required />
          <label>Email (canal prioritaire si renseigné)</label>
          <input type="email" value={candidateEmail} onChange={(e) => setCandidateEmail(e.target.value)} placeholder="candidat@example.com" />
          <label>Téléphone (repli WhatsApp)</label>
          <input value={candidatePhone} onChange={(e) => setCandidatePhone(e.target.value)} placeholder="21612345678" />
          <label>CV (PDF/DOCX)</label>
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
          <button type="submit">Téléverser &amp; lancer l&apos;analyse</button>
          <div className="p-chevrons" style={{ marginTop: 12 }}>
            <span className="p-chevron">Parsing A3</span>
            <span className="p-chevron">Scoring A4</span>
            <span className="p-chevron">Dédoublonnage auto</span>
          </div>
          {uploadError && <p style={{ color: "var(--p-danger)", fontSize: 13, marginTop: 10 }}>{uploadError}</p>}
        </form>
      )}
      {!canWrite && (
        <p style={{ color: "var(--p-muted)", fontSize: 14, marginBottom: 28 }}>
          Votre rôle ({role ?? "inconnu"}) permet uniquement la consultation des candidatures.
        </p>
      )}

      {pendingDeclines.length > 0 && canWrite && (
        <div style={{ marginBottom: 28 }}>
          <h3 style={{ fontSize: 14, marginBottom: 10, color: "var(--p-danger)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            ⚠ En attente de validation — rejet ({pendingDeclines.length})
          </h3>
          <p style={{ fontSize: 13, color: "var(--p-muted)", marginBottom: 12 }}>
            Aucun email de rejet n&apos;est envoyé automatiquement (§7). Validez ou laissez en attente.
          </p>
          {pendingDeclines.map((a) => (
            <div key={a.id} className="p-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <div>
                <StageRail status={a.status} />
                <div className="p-mono" style={{ marginTop: 8 }}>{a.id}</div>
              </div>
              <button className="p-danger" onClick={() => validateDecline(a.id)} disabled={busyId === a.id} style={{ marginTop: 0 }}>
                {busyId === a.id ? "Envoi…" : "Valider le rejet"}
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="p-card" style={{ padding: 0 }}>
        <table className="p-table">
          <thead>
            <tr><th>Progression</th><th>Source</th><th>ID candidature</th><th>Action</th>{canWrite && <th>Gestion</th>}</tr>
          </thead>
          <tbody>
            {others.map((a) => (
              <tr key={a.id} style={a.archived_at ? { opacity: 0.55 } : undefined}>
                <td><StageRail status={a.status} /></td>
                <td className="p-mono">{a.source}</td>
                <td className="p-mono">{a.id}</td>
                <td>{actionFor(a)}</td>
                {canWrite && (
                  <td>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {a.archived_at ? (
                        <button onClick={() => unarchiveApp(a.id)} disabled={busyId === a.id} style={{ marginTop: 0, background: "var(--p-panel-2)", color: "var(--p-text)" }}>
                          Désarchiver
                        </button>
                      ) : (
                        <button onClick={() => archiveApp(a.id)} disabled={busyId === a.id} style={{ marginTop: 0, background: "var(--p-panel-2)", color: "var(--p-text)" }}>
                          Archiver
                        </button>
                      )}
                      {role === "admin" && (
                        <button onClick={() => deleteApp(a.id)} disabled={busyId === a.id} className="p-danger" style={{ marginTop: 0 }}>
                          Supprimer
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {apps.length === 0 && (
              <tr><td colSpan={canWrite ? 5 : 4} style={{ color: "var(--p-muted)", textAlign: "center", padding: 32 }}>
                Aucune candidature — téléversez un CV ci-dessus.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      <p style={{ fontSize: 12, color: "var(--p-muted)", marginTop: 16 }}>
        Le parsing (A3) puis le scoring (A4) tournent en tâche de fond — actualisez la page après quelques secondes.
      </p>
    </div>
  );
}