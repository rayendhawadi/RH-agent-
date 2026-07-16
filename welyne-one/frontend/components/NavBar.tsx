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
            fontSize: 14,
            fontWeight: 500,
            color: active ? "#fff" : "#aab4c8",
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

    useEffect(() => {
        setRole(localStorage.getItem("welyne_role"));
    }, []);

    const items = role === "admin" ? [...NAV, { href: "/admin/users", label: "Administration" }] : NAV;

    return (
        <nav style={{ display: "flex", gap: 4, alignItems: "center" }}>
            {items.map((item) => (
                <NavLink key={item.href} href={item.href} label={item.label} active={pathname?.startsWith(item.href) ?? false} />
            ))}
            <a href="/" style={{ marginLeft: 12, fontSize: 13, color: "#7d8aa3" }}>
                Connexion
            </a>
        </nav>
    );
}