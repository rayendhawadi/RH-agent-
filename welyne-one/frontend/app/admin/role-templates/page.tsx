"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { ONBOARDING_CATEGORY_LABELS } from "@/lib/onboardingCategories";

type RoleTemplate = {
    id: string;
    role_category: string;
    required_documents: string[];
    equipment: string[];
    accounts_to_create: string[];
    week_one_agenda: string[];
};

type DraftFields = {
    role_category: string;
    required_documents: string;
    equipment: string;
    accounts_to_create: string;
    week_one_agenda: string;
};

const EMPTY_DRAFT: DraftFields = {
    role_category: "",
    required_documents: "",
    equipment: "",
    accounts_to_create: "",
    week_one_agenda: "",
};

function toLines(items: string[]): string {
    return items.join("\n");
}

function fromLines(text: string): string[] {
    return text
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean);
}

function toDraft(t: RoleTemplate): DraftFields {
    return {
        role_category: t.role_category,
        required_documents: toLines(t.required_documents),
        equipment: toLines(t.equipment),
        accounts_to_create: toLines(t.accounts_to_create),
        week_one_agenda: toLines(t.week_one_agenda),
    };
}

const fieldLabel: Record<keyof Omit<DraftFields, "role_category">, string> = {
    required_documents: "Documents à demander",
    accounts_to_create: "Comptes à créer",
    equipment: "Équipement",
    week_one_agenda: "Agenda semaine 1",
};

const textareaStyle: React.CSSProperties = {
    background: "#0a0a0a",
    border: "1px solid var(--line)",
    padding: "10px 14px",
    borderRadius: 8,
    color: "var(--ink)",
    width: "100%",
    boxSizing: "border-box",
    fontFamily: "inherit",
    fontSize: 13.5,
    resize: "vertical",
};

export default function RoleTemplatesAdminPage() {
    const [token, setToken] = useState<string | null>(null);
    const [role, setRole] = useState<string | null>(null);
    const [templates, setTemplates] = useState<RoleTemplate[]>([]);
    const [error, setError] = useState("");
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editDraft, setEditDraft] = useState<DraftFields>(EMPTY_DRAFT);
    const [saving, setSaving] = useState(false);

    const [creating, setCreating] = useState(false);
    const [createDraft, setCreateDraft] = useState<DraftFields>(EMPTY_DRAFT);
    const [showCreate, setShowCreate] = useState(false);

    useEffect(() => {
        const t = localStorage.getItem("welyne_token");
        const r = localStorage.getItem("welyne_role");
        setToken(t);
        setRole(r);
        if (t && r === "admin") load(t);
    }, []);

    async function load(t: string) {
        try {
            setTemplates(await apiFetch("/role-templates", t));
        } catch (e: any) {
            setError(e.message || "Erreur de chargement.");
        }
    }

    function startEdit(t: RoleTemplate) {
        setEditingId(t.id);
        setEditDraft(toDraft(t));
    }

    async function saveEdit(id: string) {
        if (!token) return;
        setSaving(true);
        setError("");
        try {
            await apiFetch(`/role-templates/${id}`, token, {
                method: "PATCH",
                body: JSON.stringify({
                    role_category: editDraft.role_category,
                    required_documents: fromLines(editDraft.required_documents),
                    equipment: fromLines(editDraft.equipment),
                    accounts_to_create: fromLines(editDraft.accounts_to_create),
                    week_one_agenda: fromLines(editDraft.week_one_agenda),
                }),
            });
            setEditingId(null);
            await load(token);
        } catch (e: any) {
            setError(e.message || "Erreur lors de l'enregistrement.");
        } finally {
            setSaving(false);
        }
    }

    async function deleteTemplate(t: RoleTemplate) {
        if (!token) return;
        if (!confirm(`Supprimer le gabarit "${ONBOARDING_CATEGORY_LABELS[t.role_category] || t.role_category}" ? Les offres qui pointent dessus retomberont sur la détection automatique.`)) return;
        try {
            await apiFetch(`/role-templates/${t.id}`, token, { method: "DELETE" });
            await load(token);
        } catch (e: any) {
            setError(e.message || "Erreur lors de la suppression.");
        }
    }

    async function createTemplate(e: React.FormEvent) {
        e.preventDefault();
        if (!token) return;
        setCreating(true);
        setError("");
        try {
            await apiFetch("/role-templates", token, {
                method: "POST",
                body: JSON.stringify({
                    role_category: createDraft.role_category.trim(),
                    required_documents: fromLines(createDraft.required_documents),
                    equipment: fromLines(createDraft.equipment),
                    accounts_to_create: fromLines(createDraft.accounts_to_create),
                    week_one_agenda: fromLines(createDraft.week_one_agenda),
                }),
            });
            setCreateDraft(EMPTY_DRAFT);
            setShowCreate(false);
            await load(token);
        } catch (e: any) {
            setError(e.message || "Erreur lors de la création — la catégorie existe peut-être déjà.");
        } finally {
            setCreating(false);
        }
    }

    if (!token) return <p style={{ color: "var(--ink-soft)" }}>Connectez-vous d&apos;abord.</p>;
    if (role !== "admin") return <p style={{ color: "var(--coral)" }}>Accès réservé au rôle admin.</p>;

    return (
        <div>
            {/* ── En-tête ── */}
            <div style={{ marginBottom: 48 }}>
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
                    Agent A8 · Onboarding
                </div>
                <h1 style={{
                    fontSize: "clamp(2.5rem, 6vw, 4.5rem)",
                    fontWeight: 800,
                    lineHeight: 1,
                    letterSpacing: "-0.04em",
                    margin: 0
                }}>
                    Gabarits d&apos;onboarding
                </h1>
                <p style={{ color: "var(--ink-soft)", fontSize: 14, marginTop: 12, maxWidth: 640 }}>
                    Un gabarit par catégorie de poste — l&apos;agent A8 y pioche pour générer la checklist d&apos;un
                    candidat dès qu&apos;il passe HIRED. Modifier un gabarit ne touche que les <em>futures</em> checklists ;
                    celles déjà générées pour des candidatures en cours restent inchangées.
                </p>
            </div>

            {error && (
                <p style={{ color: "var(--coral)", fontSize: 13, marginBottom: 20, background: "var(--coral-soft)", padding: "10px 14px", borderRadius: 8 }}>
                    {error}
                </p>
            )}

            {/* ── Liste des gabarits ── */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16, marginBottom: 32 }}>
                {templates.map((t) => {
                    const isEditing = editingId === t.id;
                    return (
                        <div
                            key={t.id}
                            className="card"
                            style={{
                                border: "1px solid var(--line)",
                                borderRadius: 16,
                                background: "var(--surface)",
                                padding: 24,
                                boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
                            }}
                        >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
                                <div>
                                    <div style={{ fontSize: 18, fontWeight: 700 }}>
                                        {ONBOARDING_CATEGORY_LABELS[t.role_category] || t.role_category}
                                        <span style={{ fontSize: 12, color: "var(--ink-faint)", fontWeight: 500, marginLeft: 8 }}>
                                            ({t.role_category})
                                        </span>
                                    </div>
                                    {!isEditing && (
                                        <p style={{ fontSize: 13, color: "var(--ink-soft)", margin: "6px 0 0" }}>
                                            {t.required_documents.length} document{t.required_documents.length !== 1 ? "s" : ""} ·{" "}
                                            {t.accounts_to_create.length} compte{t.accounts_to_create.length !== 1 ? "s" : ""} ·{" "}
                                            {t.equipment.length} équipement{t.equipment.length !== 1 ? "s" : ""} ·{" "}
                                            {t.week_one_agenda.length} item{t.week_one_agenda.length !== 1 ? "s" : ""} agenda
                                        </p>
                                    )}
                                </div>
                                {!isEditing && (
                                    <div style={{ display: "flex", gap: 8 }}>
                                        <button onClick={() => startEdit(t)} style={{ fontSize: 12, padding: "6px 14px", marginTop: 0 }}>
                                            Modifier
                                        </button>
                                        <button
                                            onClick={() => deleteTemplate(t)}
                                            style={{ fontSize: 12, padding: "6px 14px", marginTop: 0, background: "transparent", color: "var(--coral)", border: "1px solid var(--coral)" }}
                                        >
                                            Supprimer
                                        </button>
                                    </div>
                                )}
                            </div>

                            {isEditing && (
                                <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 14 }}>
                                    {(Object.keys(fieldLabel) as (keyof typeof fieldLabel)[]).map((field) => (
                                        <div key={field} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                            <label style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-soft)", fontWeight: 600 }}>
                                                {fieldLabel[field]} <span style={{ textTransform: "none", fontWeight: 400 }}>(une ligne par élément)</span>
                                            </label>
                                            <textarea
                                                value={editDraft[field]}
                                                onChange={(e) => setEditDraft({ ...editDraft, [field]: e.target.value })}
                                                rows={3}
                                                style={textareaStyle}
                                            />
                                        </div>
                                    ))}
                                    <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                                        <button onClick={() => saveEdit(t.id)} disabled={saving} style={{ marginTop: 0 }}>
                                            {saving ? "Enregistrement…" : "Enregistrer"}
                                        </button>
                                        <button
                                            onClick={() => setEditingId(null)}
                                            disabled={saving}
                                            style={{ marginTop: 0, background: "transparent", color: "var(--ink-soft)", border: "1px solid var(--line)" }}
                                        >
                                            Annuler
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}

                {templates.length === 0 && (
                    <p style={{ color: "var(--ink-soft)", fontSize: 14 }}>
                        Aucun gabarit en base — lancez <code>scripts/seed_role_templates.py</code> côté serveur, ou créez-en un ci-dessous.
                    </p>
                )}
            </div>

            {/* ── Créer une nouvelle catégorie ── */}
            {!showCreate ? (
                <button onClick={() => setShowCreate(true)} style={{ fontSize: 13 }}>
                    + Ajouter une catégorie
                </button>
            ) : (
                <form
                    onSubmit={createTemplate}
                    className="card"
                    style={{
                        border: "1px solid var(--line)",
                        borderRadius: 16,
                        background: "var(--surface)",
                        padding: 32,
                        boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
                        display: "flex", flexDirection: "column", gap: 16,
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                        <span style={{ color: "var(--accent)", fontSize: 18 }}>♦</span>
                        <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Nouvelle catégorie</h3>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        <label style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-soft)", fontWeight: 600 }}>
                            Clé de catégorie <span style={{ textTransform: "none", fontWeight: 400 }}>(identifiant technique, ex. legal, product)</span>
                        </label>
                        <input
                            value={createDraft.role_category}
                            onChange={(e) => setCreateDraft({ ...createDraft, role_category: e.target.value })}
                            placeholder="ex. product"
                            required
                            style={{ background: "#0a0a0a", border: "1px solid var(--line)", padding: "12px 16px", borderRadius: 8, color: "var(--ink)", width: "100%", boxSizing: "border-box" }}
                        />
                    </div>

                    {(Object.keys(fieldLabel) as (keyof typeof fieldLabel)[]).map((field) => (
                        <div key={field} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                            <label style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--ink-soft)", fontWeight: 600 }}>
                                {fieldLabel[field]} <span style={{ textTransform: "none", fontWeight: 400 }}>(une ligne par élément)</span>
                            </label>
                            <textarea
                                value={createDraft[field]}
                                onChange={(e) => setCreateDraft({ ...createDraft, [field]: e.target.value })}
                                rows={3}
                                style={textareaStyle}
                            />
                        </div>
                    ))}

                    <div style={{ display: "flex", gap: 8 }}>
                        <button type="submit" disabled={creating} style={{ marginTop: 0 }}>
                            {creating ? "Création…" : "Créer le gabarit"}
                        </button>
                        <button
                            type="button"
                            onClick={() => { setShowCreate(false); setCreateDraft(EMPTY_DRAFT); }}
                            style={{ marginTop: 0, background: "transparent", color: "var(--ink-soft)", border: "1px solid var(--line)" }}
                        >
                            Annuler
                        </button>
                    </div>
                </form>
            )}

            {/* ── Manuel d'entreprise (RAG Assistant A8) ── */}
            <div
                className="card"
                style={{
                    border: "1px solid var(--line)",
                    borderRadius: 16,
                    background: "var(--surface)",
                    padding: 32,
                    marginTop: 48,
                    boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                    <span style={{ fontSize: 22 }}>📖</span>
                    <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Manuel d&apos;entreprise</h3>
                </div>
                <p style={{ color: "var(--ink-soft)", fontSize: 13, marginBottom: 20, maxWidth: 600 }}>
                    Importez le PDF du manuel de votre entreprise. L&apos;agent A8 l&apos;utilisera pour répondre
                    aux questions des candidats pendant leur onboarding via un assistant IA (RAG).
                </p>
                <ManualUpload token={token} />
            </div>
        </div>
    );
}

/* ── Sous-composant upload du manuel ── */
function ManualUpload({ token }: { token: string | null }) {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState<string | null>(null);
    const [err, setErr] = useState<string | null>(null);

    async function handleUpload() {
        if (!file || !token) return;
        setUploading(true);
        setResult(null);
        setErr(null);
        try {
            const form = new FormData();
            form.append("file", file);
            await apiFetch("/applications/manual/upload", token, { method: "POST", body: form });
            setResult("Manuel importé et vectorisé avec succès !");
            setFile(null);
        } catch (e: any) {
            setErr(e.message || "Erreur lors de l'import du manuel.");
        } finally {
            setUploading(false);
        }
    }

    return (
        <div>
            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                <label
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "10px 18px",
                        borderRadius: 10,
                        border: "1px dashed var(--accent)",
                        cursor: "pointer",
                        fontSize: 13,
                        color: "var(--accent)",
                        transition: "background 0.2s",
                    }}
                >
                    📄 {file ? file.name : "Choisir un fichier PDF"}
                    <input
                        type="file"
                        accept=".pdf"
                        style={{ display: "none" }}
                        onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); setErr(null); }}
                    />
                </label>
                <button
                    onClick={handleUpload}
                    disabled={!file || uploading}
                    style={{
                        marginTop: 0,
                        opacity: !file || uploading ? 0.5 : 1,
                        fontSize: 13,
                    }}
                >
                    {uploading ? "Import en cours…" : "Importer le manuel"}
                </button>
            </div>
            {result && (
                <p style={{ color: "var(--accent)", fontSize: 13, marginTop: 12, background: "rgba(255,122,0,0.08)", padding: "10px 14px", borderRadius: 8 }}>
                    ✓ {result}
                </p>
            )}
            {err && (
                <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 12, background: "var(--coral-soft)", padding: "10px 14px", borderRadius: 8 }}>
                    {err}
                </p>
            )}
        </div>
    );
}