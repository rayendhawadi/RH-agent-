"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

type SourcingQueries = {
    title_synonyms: string[];
    boolean_queries: string[];
    xray_queries: string[];
};
type OutreachMessage = { tone: string; message: string };
type OutreachSet = { messages: OutreachMessage[] };

function CopyBtn({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);
    return (
        <button
            onClick={() => {
                navigator.clipboard.writeText(text);
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
            }}
            style={{ marginTop: 0, padding: "2px 8px", fontSize: 12 }}
        >
            {copied ? "Copié ✓" : "Copier"}
        </button>
    );
}

export default function SourcingPanel({ jobId, token }: { jobId: string; token: string }) {
    const [queries, setQueries] = useState<SourcingQueries | null>(null);
    const [queriesLoading, setQueriesLoading] = useState(false);

    const [candidateName, setCandidateName] = useState("");
    const [candidateHighlight, setCandidateHighlight] = useState("");
    const [outreach, setOutreach] = useState<OutreachSet | null>(null);
    const [outreachLoading, setOutreachLoading] = useState(false);

    const [importName, setImportName] = useState("");
    const [importEmail, setImportEmail] = useState("");
    const [importPhone, setImportPhone] = useState("");
    const [pastedText, setPastedText] = useState("");
    const [file, setFile] = useState<File | null>(null);
    const [importLoading, setImportLoading] = useState(false);
    const [importMsg, setImportMsg] = useState<{ ok: boolean; text: string } | null>(null);

    const [bulkFile, setBulkFile] = useState<File | null>(null);
    const [bulkLoading, setBulkLoading] = useState(false);
    const [bulkResult, setBulkResult] = useState<{ imported: number; errors: number; results: any[] } | null>(null);

    async function generateQueries() {
        setQueriesLoading(true);
        try {
            const data = await apiFetch(`/jobs/${jobId}/sourcing/queries`, token, { method: "POST", body: JSON.stringify({}) });
            setQueries(data);
        } catch (e: any) {
            setImportMsg({ ok: false, text: e.message || "Erreur lors de la génération des requêtes." });
        } finally {
            setQueriesLoading(false);
        }
    }

    async function generateOutreach(e: React.FormEvent) {
        e.preventDefault();
        setOutreachLoading(true);
        try {
            const data = await apiFetch(`/jobs/${jobId}/sourcing/outreach`, token, {
                method: "POST",
                body: JSON.stringify({ candidate_name: candidateName, candidate_highlight: candidateHighlight }),
            });
            setOutreach(data);
        } catch (e: any) {
            setImportMsg({ ok: false, text: e.message || "Erreur lors de la génération du message." });
        } finally {
            setOutreachLoading(false);
        }
    }

    async function importProfile(e: React.FormEvent) {
        e.preventDefault();
        if (!file && !pastedText) {
            setImportMsg({ ok: false, text: "Fournissez un fichier ou du texte collé." });
            return;
        }
        setImportLoading(true);
        setImportMsg(null);
        try {
            const form = new FormData();
            form.append("candidate_full_name", importName);
            if (importEmail) form.append("candidate_email", importEmail);
            if (importPhone) form.append("candidate_phone", importPhone);
            if (pastedText) form.append("pasted_text", pastedText);
            if (file) form.append("file", file);

            const data = await apiFetch(`/jobs/${jobId}/sourcing/import`, token, { method: "POST", body: form });
            setImportMsg({ ok: true, text: `Profil importé (candidature ${data.status}) — tagué source=linkedin_assist, parsing A3 lancé.` });
            setImportName("");
            setImportEmail("");
            setImportPhone("");
            setPastedText("");
            setFile(null);
        } catch (e: any) {
            setImportMsg({ ok: false, text: e.message || "Erreur lors de l'import." });
        } finally {
            setImportLoading(false);
        }
    }

    async function importBulk(e: React.FormEvent) {
        e.preventDefault();
        if (!bulkFile) return;
        setBulkLoading(true);
        setBulkResult(null);
        try {
            const form = new FormData();
            form.append("file", bulkFile);
            const data = await apiFetch(`/jobs/${jobId}/sourcing/import-bulk`, token, { method: "POST", body: form });
            setBulkResult(data);
            setBulkFile(null);
        } catch (e: any) {
            setImportMsg({ ok: false, text: e.message || "Erreur lors de l'import en masse." });
        } finally {
            setBulkLoading(false);
        }
    }

    return (
        <div className="card" style={{ marginTop: 20 }}>
            <h3 style={{ marginBottom: 4 }}>Sourcing (A2) — mode assistance</h3>
            <p style={{ fontSize: 12, color: "var(--ink-soft)", marginBottom: 16 }}>
                Pas de scraping automatisé (voir décision de conformité §6-A2) : ces requêtes sont à lancer
                vous-même sur LinkedIn/Google, et les messages d&apos;approche sont à copier-coller manuellement.
            </p>

            <div style={{ marginBottom: 20 }}>
                <button onClick={generateQueries} disabled={queriesLoading}>
                    {queriesLoading ? "Génération…" : "Générer les requêtes de recherche"}
                </button>

                {queries && (
                    <div style={{ marginTop: 12 }}>
                        <QueryGroup label="Synonymes de titre" items={queries.title_synonyms} />
                        <QueryGroup label="Requêtes booléennes" items={queries.boolean_queries} mono />
                        <QueryGroup label="Requêtes X-ray (Google)" items={queries.xray_queries} mono />
                    </div>
                )}
            </div>

            <hr style={{ border: "none", borderTop: "1px solid var(--line, #eee)", margin: "16px 0" }} />

            <form onSubmit={generateOutreach} style={{ marginBottom: 20 }}>
                <h4 style={{ marginBottom: 8, fontSize: 14 }}>Brouillon de message d&apos;approche</h4>
                <label style={{ fontSize: 12 }}>Prénom du candidat</label>
                <input value={candidateName} onChange={(e) => setCandidateName(e.target.value)} required />
                <label style={{ fontSize: 12 }}>Point marquant du profil (optionnel)</label>
                <input value={candidateHighlight} onChange={(e) => setCandidateHighlight(e.target.value)} placeholder="ex. 3 ans d'expérience FastAPI chez X" />
                <button type="submit" disabled={outreachLoading}>{outreachLoading ? "Génération…" : "Générer 3 brouillons"}</button>

                {outreach && (
                    <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 10 }}>
                        {outreach.messages.map((m, i) => (
                            <div key={i} style={{ border: "1px solid var(--line, #eee)", borderRadius: 8, padding: 10 }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                                    <span className="badge">{m.tone}</span>
                                    <CopyBtn text={m.message} />
                                </div>
                                <p style={{ fontSize: 13, whiteSpace: "pre-wrap", margin: 0 }}>{m.message}</p>
                            </div>
                        ))}
                    </div>
                )}
            </form>

            <hr style={{ border: "none", borderTop: "1px solid var(--line, #eee)", margin: "16px 0" }} />

            <form onSubmit={importProfile}>
                <h4 style={{ marginBottom: 8, fontSize: 14 }}>Importer un profil trouvé manuellement</h4>
                <p style={{ fontSize: 12, color: "var(--ink-soft)", marginBottom: 8 }}>
                    Collez un export PDF/DOCX du profil, ou son texte — même pipeline que les CV reçus par email
                    (parsing A3 puis scoring A4), tagué <code>source=linkedin_assist</code>.
                </p>
                <label style={{ fontSize: 12 }}>Nom complet</label>
                <input value={importName} onChange={(e) => setImportName(e.target.value)} required />
                <label style={{ fontSize: 12 }}>Email (optionnel)</label>
                <input value={importEmail} onChange={(e) => setImportEmail(e.target.value)} type="email" />
                <label style={{ fontSize: 12 }}>Téléphone (optionnel)</label>
                <input value={importPhone} onChange={(e) => setImportPhone(e.target.value)} />
                <label style={{ fontSize: 12 }}>Texte collé (profil/export)</label>
                <textarea
                    value={pastedText}
                    onChange={(e) => setPastedText(e.target.value)}
                    rows={5}
                    style={{ width: "100%", padding: 10, border: "1px solid var(--line, #eee)", borderRadius: 8, fontFamily: "inherit", fontSize: 13 }}
                    placeholder="Collez ici le texte du profil si vous n'avez pas de fichier…"
                />
                <label style={{ fontSize: 12, marginTop: 8, display: "block" }}>...ou fichier (PDF/DOCX)</label>
                <input type="file" accept=".pdf,.docx" onChange={(e) => setFile(e.target.files?.[0] || null)} />

                <button type="submit" disabled={importLoading}>{importLoading ? "Import…" : "Importer le profil"}</button>

                {importMsg && (
                    <p style={{ fontSize: 13, marginTop: 10, color: importMsg.ok ? "green" : "var(--coral, #c0392b)" }}>
                        {importMsg.text}
                    </p>
                )}
            </form>

            <hr style={{ border: "none", borderTop: "1px solid var(--line, #eee)", margin: "16px 0" }} />

            <form onSubmit={importBulk}>
                <h4 style={{ marginBottom: 8, fontSize: 14 }}>Import en masse (CSV)</h4>
                <p style={{ fontSize: 12, color: "var(--ink-soft)", marginBottom: 8 }}>
                    Colonnes requises : <code>full_name, profile_text</code> (<code>email, phone</code> optionnels).
                    Une ligne = un profil, même pipeline A3→A4, tagué <code>source=linkedin_assist</code>.
                    Une ligne en erreur n&apos;empêche pas les suivantes.
                </p>
                <input type="file" accept=".csv" onChange={(e) => setBulkFile(e.target.files?.[0] || null)} />
                <button type="submit" disabled={bulkLoading || !bulkFile}>
                    {bulkLoading ? "Import…" : "Importer le CSV"}
                </button>

                {bulkResult && (
                    <div style={{ marginTop: 10, fontSize: 13 }}>
                        <p style={{ margin: "0 0 6px" }}>
                            <strong style={{ color: "green" }}>{bulkResult.imported} importé(s)</strong>
                            {bulkResult.errors > 0 && (
                                <span style={{ color: "var(--coral, #c0392b)" }}> · {bulkResult.errors} en erreur</span>
                            )}
                        </p>
                        {bulkResult.errors > 0 && (
                            <ul style={{ margin: 0, paddingLeft: 18 }}>
                                {bulkResult.results.filter((r) => r.status === "error").map((r) => (
                                    <li key={r.row} style={{ color: "var(--coral, #c0392b)" }}>
                                        Ligne {r.row} : {r.detail}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                )}
            </form>
        </div>
    );
}

function QueryGroup({ label, items, mono }: { label: string; items: string[]; mono?: boolean }) {
    if (!items?.length) return null;
    return (
        <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>{label}</div>
            <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
                {items.map((q, i) => (
                    <li
                        key={i}
                        style={{
                            display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8,
                            fontSize: 13, padding: "4px 0", borderBottom: "1px solid var(--line, #f2f2f2)",
                            fontFamily: mono ? "monospace" : "inherit",
                        }}
                    >
                        <span style={{ wordBreak: "break-word" }}>{q}</span>
                        <CopyBtn text={q} />
                    </li>
                ))}
            </ul>
        </div>
    );
}