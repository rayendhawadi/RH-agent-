"use client";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

const NAV = [
    { href: "/jobs", label: "Offres" },
    { href: "/applications", label: "Candidatures" },
    { href: "/reports", label: "Reporting" },
];

function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
    return (<a

        href={href}
        style={{
            padding: "6px 14px",
            borderRadius: 999,
            fontSize: 13,
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            color: active ? "#fff" : "var(--ink-soft)",
            background: active ? "var(--accent)" : "transparent",
            textDecoration: "none",
            transition: "color 0.15s ease",
        }}
    >
        {label}
    </a>
    );
}

export default function NavBar() {
    const pathname = usePathname();
    const [role, setRole] = useState<string | null>(null);
    const [isLoggedIn, setIsLoggedIn] = useState(false);

    useEffect(() => {
        setRole(localStorage.getItem("welyne_role"));
        setIsLoggedIn(!!localStorage.getItem("welyne_token"));
    }, []);

    function handleLogout() {
        localStorage.removeItem("welyne_token");
        localStorage.removeItem("welyne_role");
        window.location.href = "/";
    }

    const items = role === "admin" ? [...NAV, { href: "/admin/users", label: "Administration" }] : NAV;

    return (
        <nav style={{ display: "flex", gap: 4, alignItems: "center" }}>
            {items.map((item) => (
                <NavLink key={item.href} href={item.href} label={item.label} active={pathname?.startsWith(item.href) ?? false} />
            ))}
            {isLoggedIn ? (
                <button
                    onClick={handleLogout}
                    style={{
                        marginLeft: 12,
                        fontSize: 13,
                        fontWeight: 600,
                        color: "var(--ink-soft)",
                        background: "transparent",
                        border: "1px solid var(--line)",
                        borderRadius: 999,
                        padding: "5px 14px",
                        cursor: "pointer",
                        transition: "color 0.15s ease, border-color 0.15s ease",
                    }}
                    onMouseEnter={(e) => {
                        (e.currentTarget as HTMLButtonElement).style.color = "var(--coral)";
                        (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--coral)";
                    }}
                    onMouseLeave={(e) => {
                        (e.currentTarget as HTMLButtonElement).style.color = "var(--ink-soft)";
                        (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--line)";
                    }}
                >
                    Déconnexion
                </button>
            ) : (
                <a href="/" style={{ marginLeft: 12, fontSize: 13, color: "var(--ink-faint)" }}>
                    Connexion
                </a>
            )}
        </nav>
    );
}