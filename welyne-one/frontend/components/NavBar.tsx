"use client";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

const NAV = [
    { href: "/jobs", label: "Offres" },
    { href: "/applications", label: "Candidatures" },
    { href: "/sourcing", label: "Sourcing" },
    { href: "/reports", label: "Reporting" },
];

function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
    const [hovered, setHovered] = useState(false);
    return (
        <a
            href={href}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            style={{
                fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
                fontSize: 12,
                fontWeight: active ? 700 : 500,
                textTransform: "uppercase",
                letterSpacing: "0.18em",
                color: active || hovered ? "#FF6B00" : "#a39a8d",
                textDecoration: "none",
                transition: "color 0.18s ease",
                padding: "4px 0",
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
    const [logoutHovered, setLogoutHovered] = useState(false);

    useEffect(() => {
        setRole(localStorage.getItem("welyne_role"));
        setIsLoggedIn(!!localStorage.getItem("welyne_token"));
    }, []);

    function handleLogout() {
        localStorage.removeItem("welyne_token");
        localStorage.removeItem("welyne_role");
        window.location.href = "/";
    }

    const items = role === "admin"
        ? [...NAV, { href: "/admin/users", label: "Admin" }, { href: "/admin/role-templates", label: "Gabarits" }]
        : NAV;

    if (pathname === "/") {
        return null;
    }

    return (
        <nav style={{ display: "flex", gap: 36, alignItems: "center" }}>
            {items.map((item) => (
                <NavLink
                    key={item.href}
                    href={item.href}
                    label={item.label}
                    active={pathname?.startsWith(item.href) ?? false}
                />
            ))}

            {/* Séparateur vertical */}
            <span style={{ color: "rgba(163,154,141,0.25)", fontFamily: "monospace", fontSize: 14, lineHeight: 1 }}>|</span>

            {isLoggedIn ? (
                <button
                    onClick={handleLogout}
                    onMouseEnter={() => setLogoutHovered(true)}
                    onMouseLeave={() => setLogoutHovered(false)}
                    style={{
                        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
                        fontSize: 11,
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.16em",
                        color: logoutHovered ? "#e5484d" : "#6e675c",
                        background: "transparent",
                        border: "none",
                        padding: "4px 0",
                        cursor: "pointer",
                        transition: "color 0.18s ease",
                    }}
                >
                    Déconnexion
                </button>
            ) : (
                <a
                    href="/"
                    style={{
                        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
                        fontSize: 11,
                        fontWeight: 500,
                        textTransform: "uppercase",
                        letterSpacing: "0.16em",
                        color: "#6e675c",
                        textDecoration: "none",
                    }}
                >
                    Connexion
                </a>
            )}
        </nav>
    );
}