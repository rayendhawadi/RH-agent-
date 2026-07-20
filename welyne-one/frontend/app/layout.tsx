import "./globals.css";
import NavBar from "@/components/NavBar";

export const metadata = { title: "Welyne One — Dashboard" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <header
          style={{
            padding: "14px 28px",
            background: "var(--surface)",
            borderBottom: "1px solid var(--line)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              aria-hidden
              style={{
                width: 28, height: 28, borderRadius: 7,
                background: "linear-gradient(135deg, var(--accent), var(--accent-dark))",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 14, color: "#fff",
              }}
            >
              W
            </div>
            <strong style={{ fontFamily: "'Space Grotesk', sans-serif", color: "#fff", fontSize: 16, fontWeight: 700, letterSpacing: "-0.02em" }}>
              Welyne One
            </strong>
            {/* signature : trace visuelle du pipeline d'agents A0→A9 — l'ordre
                des agents porte une vraie information (recrutement = séquence),
                repris comme motif dans la puce de statut des tableaux. */}
            <div className="mono" style={{ display: "flex", gap: 3, marginLeft: 4 }} aria-hidden>
              {Array.from({ length: 9 }).map((_, i) => (
                <span
                  key={i}
                  style={{
                    width: 4, height: 4, borderRadius: "50%",
                    background: i < 4 ? "var(--accent)" : "rgba(239, 231, 219, 0.15)",
                  }}
                />
              ))}
            </div>
          </div>

          <NavBar />
        </header>
        <main style={{ padding: "32px clamp(20px, 4vw, 56px)", maxWidth: 1600, margin: "0 auto" }}>{children}</main>
      </body>
    </html>
  );
}