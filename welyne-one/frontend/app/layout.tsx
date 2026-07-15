import "./globals.css";

export const metadata = { title: "Welyne One — Dashboard" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <header style={{ padding: "12px 24px", borderBottom: "1px solid #e2e2e2", display: "flex", justifyContent: "space-between" }}>
          <strong>Welyne One — Agent IA RH</strong>
          <nav style={{ display: "flex", gap: 16 }}>
            <a href="/">Connexion</a>
            <a href="/jobs">Offres</a>
            <a href="/applications">Candidatures</a>
            <a href="/applications">Candidatures</a>
            <a href="/reports">Reporting</a>
          </nav>
        </header>
        <main style={{ padding: 24, maxWidth: 1000, margin: "0 auto" }}>{children}</main>
      </body>
    </html>
  );
}
