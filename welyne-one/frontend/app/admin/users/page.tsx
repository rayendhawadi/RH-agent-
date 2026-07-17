"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type UserRow = { id: string; email: string; full_name: string; role: string; is_active: boolean };

// "admin" n'apparaît volontairement dans AUCUNE liste déroulante : ce rôle
// n'est jamais assignable depuis l'interface, même par un autre admin — le
// backend le refuse aussi (POST/PATCH /users, voir users.py ASSIGNABLE_ROLES).
// Le seul moyen de créer un admin est scripts/seed_admin.py côté serveur.
const ASSIGNABLE_ROLES = ["recruteur", "lecteur"];

export default function AdminUsersPage() {
    const [token, setToken] = useState<string | null>(null);
    const [role, setRole] = useState<string | null>(null);
    const [users, setUsers] = useState<UserRow[]>([]);
    const [error, setError] = useState("");

    const [email, setEmail] = useState("");
    const [fullName, setFullName] = useState("");
    const [newRole, setNewRole] = useState("recruteur");
    const [creating, setCreating] = useState(false);

    useEffect(() => {
        const t = localStorage.getItem("welyne_token");
        const r = localStorage.getItem("welyne_role");
        setToken(t);
        setRole(r);
        if (t && r === "admin") load(t);
    }, []);

    async function load(t: string) {
        try {
            setUsers(await apiFetch("/users", t));
        } catch (e: any) {
            setError(e.message || "Erreur de chargement.");
        }
    }

    async function createUser(e: React.FormEvent) {
        e.preventDefault();
        if (!token) return;
        setCreating(true);
        setError("");
        try {
            await apiFetch("/users", token, {
                method: "POST",
                body: JSON.stringify({ email, full_name: fullName, role: newRole }),
            });
            setEmail(""); setFullName(""); setNewRole("recruteur");
            load(token);
        } catch (e: any) {
            setError(e.message || "Erreur lors de la création.");
        } finally {
            setCreating(false);
        }
    }

    async function changeRole(userId: string, r: string) {
        if (!token) return;
        await apiFetch(`/users/${userId}/role`, token, { method: "PATCH", body: JSON.stringify({ role: r }) });
        load(token);
    }

    async function toggleActive(userId: string) {
        if (!token) return;
        await apiFetch(`/users/${userId}/toggle-active`, token, { method: "POST" });
        load(token);
    }

    if (!token) return <p style={{ color: "var(--ink-soft)" }}>Connectez-vous d&apos;abord.</p>;
    if (role !== "admin") return <p style={{ color: "var(--coral)" }}>Accès réservé au rôle admin.</p>;

    return (
        <div>
            <h1 style={{ fontSize: 24, marginBottom: 20 }}>Administration — comptes utilisateurs</h1>

            <form onSubmit={createUser} className="card" style={{ marginBottom: 20 }}>
                <h3 style={{ marginBottom: 12 }}>Créer un compte</h3>
                <label>Email</label>
                <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
                <label>Nom complet</label>
                <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
                <label>Rôle</label>
                <select value={newRole} onChange={(e) => setNewRole(e.target.value)}>
                    {ASSIGNABLE_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
                <p style={{ fontSize: 12, color: "var(--ink-soft)", margin: "4px 0 0" }}>
                    Aucun mot de passe à définir ici : un email est envoyé au nouvel utilisateur
                    pour confirmer son adresse et choisir lui-même son mot de passe.
                </p>
                <button type="submit" disabled={creating}>{creating ? "Création…" : "Créer le compte"}</button>
                {error && <p style={{ color: "var(--coral)", fontSize: 13, marginTop: 10 }}>{error}</p>}
            </form>

            <div className="card">
                <h3 style={{ marginBottom: 8 }}>Comptes existants</h3>
                <table>
                    <thead>
                        <tr><th>Email</th><th>Nom</th><th>Rôle</th><th>Statut</th><th></th></tr>
                    </thead>
                    <tbody>
                        {users.map((u) => (
                            <tr key={u.id}>
                                <td>{u.email}</td>
                                <td>{u.full_name || "—"}</td>
                                <td>
                                    {u.role === "admin" ? (
                                        <span
                                            className="badge"
                                            title="Le rôle admin ne peut être ni assigné ni modifié depuis l'interface (seul scripts/seed_admin.py le peut, côté serveur)."
                                        >
                                            🔒 admin (protégé)
                                        </span>
                                    ) : (
                                        <select value={u.role} onChange={(e) => changeRole(u.id, e.target.value)} style={{ margin: 0 }}>
                                            {ASSIGNABLE_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                                        </select>
                                    )}
                                </td>
                                <td>
                                    <span className="badge" style={{ color: u.is_active ? "var(--accent-dark)" : "var(--coral)" }}>
                                        {u.is_active ? "actif" : "désactivé"}
                                    </span>
                                </td>
                                <td>
                                    <button onClick={() => toggleActive(u.id)} style={{ fontSize: 12, padding: "4px 10px", marginTop: 0 }}>
                                        {u.is_active ? "Désactiver" : "Réactiver"}
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}