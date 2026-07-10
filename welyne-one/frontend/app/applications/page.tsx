"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type App = { id: string; job_id: string; candidate_id: string; status: string; source: string };

export default function ApplicationsPage() {
  const [apps, setApps] = useState<App[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [jobId, setJobId] = useState("");
  const [candidateName, setCandidateName] = useState("");
  const [candidateEmail, setCandidateEmail] = useState("");
  const [candidatePhone, setCandidatePhone] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

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
    if (candidateEmail) form.append("candidate_email", candidateEmail);
    if (candidatePhone) form.append("candidate_phone", candidatePhone);
    form.append("file", file);
    await apiFetch("/applications/upload", token, { method: "POST", body: form });
    load(token);
  }

  async function validateDecline(id: string) {
    if (!token) return;
    if (!confirm("Confirmer le rejet ? L'email de rejet sera envoyé au candidat après validation.")) return;
    setBusyId(id);
    try {
      await apiFetch(`/applications/${id}/validate-decline`, token, {
        method: "POST",
        body: JSON.stringify({ reason: "" }),
      });
      await load(token);
    } finally {
      setBusyId(null);
    }
  }

  async function inviteInterview(id: string) {
    if (!token) return;
    setBusyId(id);
    try {
      await apiFetch(`/applications/${id}/invite-interview`, token, { method: "POST" });
      await load(token);
    } finally {
      setBusyId(null);
    }
  }

  async function markInterviewed(id: string) {
    if (!token) return;
    setBusyId(id);
    try {
      await apiFetch(`/applications/${id}/mark-interviewed`, token, { method: "POST" });
      await load(token);
    } finally {
      setBusyId(null);
    }
  }

  async function makeOffer(id: string) {
    if (!token) return;
    setBusyId(id);
    try {
      await apiFetch(`/applications/${id}/make-offer`, token, { method: "POST" });
      await load(token);
    } finally {
      setBusyId(null);
    }
  }

  async function confirmHire(id: string) {
    if (!token) return;
    if (!confirm("Confirmer l'embauche ? Ceci est une porte humaine explicite (§7).")) return;
    setBusyId(id);
    try {
      await apiFetch(`/applications/${id}/confirm-hire`, token, {
        method: "POST",
        body: JSON.stringify({ note: "" }),
      });
      await load(token);
    } finally {
      setBusyId(null);
    }
  }

  async function startOnboarding(id: string) {
    if (!token) return;
    setBusyId(id);
    try {
      await apiFetch(`/applications/${id}/start-onboarding`, token, { method: "POST" });
      await load(token);
    } finally {
      setBusyId(null);
    }
  }

  if (!token) return <p style={{ color: "var(--ink-soft)" }}>Connectez-vous d&apos;abord.</p>;

  const pendingDeclines = apps.filter((a) => a.status === "DECLINE_PENDING");
  const others = apps.filter((a) => a.status !== "DECLINE_PENDING");

  // Retourne le bouton d'action adapté au statut courant, ou null si aucune action n'est possible ici
  function actionFor(a: App) {
    switch (a.status) {
      case "PRESCREENED":
        return (
          <button onClick={() => inviteInterview(a.id)} disabled={busyId === a.id}>
            {busyId === a.id ? "Envoi…" : "Inviter à un entretien"}
          </button>
        );
      case "INTERVIEW_SCHEDULED":
        return (
          <button onClick={() => markInterviewed(a.id)} disabled={busyId === a.id}>
            {busyId === a.id ? "…" : "Marquer entretien effectué"}
          </button>
        );
      case "INTERVIEWED":
        return (
          <button onClick={() => makeOffer(a.id)} disabled={busyId === a.id}>
            {busyId === a.id ? "Envoi…" : "Faire une offre"}
          </button>
        );
      case "OFFER":
        return (
          <button
            onClick={() => confirmHire(a.id)}
            disabled={busyId === a.id}
            style={{ background: "var(--coral)" }}
          >
            {busyId === a.id ? "…" : "Confirmer l'embauche"}
          </button>
        );
      case "HIRED":
        return (
          <button onClick={() => startOnboarding(a.id)} disabled={busyId === a.id}>
            {busyId === a.id ? "Envoi…" : "Démarrer l'onboarding"}
          </button>
        );
      default:
        return null;
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24 }}>Candidatures</h1>
        <p style={{ color: "var(--ink-soft)", fontSize: 14, margin: "4px 0 0" }}>
          {apps.length} candidature{apps.length !== 1 ? "s" : ""} suivie{apps.length !== 1 ? "s" : ""} dans le pipeline
        </p>
      </div>

      <form onSubmit={upload} className="card" style={{ maxWidth: 420, marginBottom: 28 }}>
        <label>ID de l&apos;offre</label>
        <input value={jobId} onChange={(e) => setJobId(e.target.value)} placeholder="uuid de l'offre" required />
        <label>Nom du candidat</label>
        <input value={candidateName} onChange={(e) => setCandidateName(e.target.value)} required />
        <label>Email (optionnel — canal prioritaire si renseigné)</label>
        <input
          type="email"
          value={candidateEmail}
          onChange={(e) => setCandidateEmail(e.target.value)}
          placeholder="candidat@example.com"
        />
        <label>Téléphone (optionnel — repli WhatsApp si pas d&apos;email)</label>
        <input
          value={candidatePhone}
          onChange={(e) => setCandidatePhone(e.target.value)}
          placeholder="21612345678 (format international, sans +)"
        />
        <label>CV (PDF/DOCX)</label>
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
        <button type="submit">Téléverser &amp; lancer l&apos;analyse</button>
      </form>

      {pendingDeclines.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <h3 style={{ fontSize: 15, marginBottom: 10, color: "var(--coral)" }}>
            ⚠ En attente de validation — rejet ({pendingDeclines.length})
          </h3>
          <p style={{ fontSize: 13, color: "var(--ink-soft)", marginBottom: 12 }}>
            Aucun email de rejet n&apos;est envoyé automatiquement (§7). Validez ou laissez en attente.
          </p>
          {pendingDeclines.map((a) => (
            <div
              key={a.id}
              className="card"
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, borderColor: "var(--coral-bg)" }}
            >
              <div>
                <span className={`badge ${a.status}`}>{a.status}</span>
                <div className="mono" style={{ fontSize: 11, color: "var(--ink-soft)", marginTop: 6 }}>{a.id}</div>
              </div>
              <button
                onClick={() => validateDecline(a.id)}
                disabled={busyId === a.id}
                style={{ background: "var(--coral)", marginTop: 0 }}
              >
                {busyId === a.id ? "Envoi…" : "Valider le rejet"}
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr><th>Statut</th><th>Source</th><th>ID candidature</th><th>Action</th></tr>
          </thead>
          <tbody>
            {others.map((a) => (
              <tr key={a.id}>
                <td><span className={`badge ${a.status}`}>{a.status}</span></td>
                <td style={{ color: "var(--ink-soft)" }}>{a.source}</td>
                <td className="mono" style={{ fontSize: 12, color: "var(--ink-soft)" }}>{a.id}</td>
                <td>{actionFor(a)}</td>
              </tr>
            ))}
            {apps.length === 0 && (
              <tr><td colSpan={4} style={{ color: "var(--ink-soft)", textAlign: "center", padding: 32 }}>
                Aucune candidature — téléversez un CV ci-dessus.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      <p style={{ fontSize: 12, color: "var(--ink-soft)", marginTop: 16 }}>
        Le parsing (A3) puis le scoring (A4) tournent en tâche de fond — actualisez la page après quelques secondes.
      </p>
    </div>
  );
}