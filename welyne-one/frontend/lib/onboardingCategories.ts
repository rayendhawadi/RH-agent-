// Libellés lisibles + suggestion automatique pour la catégorie de gabarit
// d'onboarding (§6-A8). Partagé entre le formulaire de création d'offre, la
// page de détail (correction après coup) et l'admin des gabarits — un seul
// endroit à garder synchro avec _CATEGORY_KEYWORDS côté backend
// (services/generation/onboarding_checklist.py).

export const ONBOARDING_CATEGORY_LABELS: Record<string, string> = {
    engineering: "Ingénierie / Tech",
    sales: "Ventes / Commercial",
    marketing: "Marketing",
    hr_support: "RH / Support",
    finance: "Finance",
    general: "Général",
};

const CATEGORY_KEYWORDS: Record<string, string[]> = {
    engineering: ["ingenieur", "developpeur", "devops", "data", "backend", "frontend", "mlops"],
    sales: ["commercial", "vente", "sales", "account executive"],
    marketing: ["marketing", "growth", "communication", "community manager", "brand"],
    hr_support: ["rh", "ressources humaines", "support", "service client", "assistance"],
    finance: ["finance", "comptable", "comptabilite", "controle de gestion", "audit"],
};

function stripAccents(s: string) {
    return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/** Suggestion déterministe par mot-clé — pas de LLM, miroir de pick_role_category(). */
export function suggestOnboardingCategory(jobTitle: string): string {
    const t = stripAccents(jobTitle.toLowerCase());
    for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
        if (keywords.some((kw) => t.includes(kw))) return category;
    }
    return "general";
}