"""Test A1 sur 10 briefs variés — vérifie qu'aucun ne casse le schéma JobSpec (§6, CA agent A1).
Usage : python scripts/test_a1_batch.py <email> <password>
"""
import sys
import requests

BASE = "http://localhost:8000"

BRIEFS = [
    "Développeur Full Stack, Tunis, 3 ans XP, React + Node.js, anglais requis.",
    "Poste: Comptable senior. Diplome expertise comptable exige. Sfax. CDI.",
    "recherche commercial terrain b2b, permis b obligatoire, tunisois, primes",
    "Ingénieur DevOps — Kubernetes, AWS, 5+ ans, remote possible, français/anglais",
    "Assistante RH junior, débutant accepté, Tunis centre, temps plein",
    "Chef de projet IT senior. Gestion equipe 10 personnes. Agile/Scrum. Sousse.",
    "Data analyst - SQL, PowerBI, 2 ans exp min, doit resider en Tunisie",
    "Responsable marketing digital, SEO/SEA, budget pub, Tunis, CDI 40h",
    "Technicien support niveau 1, astreintes weekend, permis obligatoire, Nabeul",
    "Architecte logiciel principal - 8 ans XP, microservices, mentorat equipe junior",
]


def main():
    if len(sys.argv) != 3:
        print("Usage: python test_a1_batch.py <email> <password>")
        sys.exit(1)
    email, password = sys.argv[1], sys.argv[2]

    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    passed, failed = 0, 0
    for i, brief in enumerate(BRIEFS, 1):
        job = requests.post(f"{BASE}/jobs", json={"title": f"Test A1 #{i}"}, headers=headers).json()
        job_id = job["id"]
        try:
            resp = requests.post(
                f"{BASE}/jobs/{job_id}/generate-spec",
                json={"raw_brief": brief},
                headers=headers,
                timeout=90,
            )
            resp.raise_for_status()
            spec = resp.json()["job_spec"]
            has_content = bool(spec.get("missions") or spec.get("must_have"))
            status = "OK" if has_content else "VIDE"
            print(f"[{i:2}] {status:4} - missions={len(spec.get('missions', []))} "
                  f"must_have={len(spec.get('must_have', []))} "
                  f"hard_filters={len(spec.get('hard_filters', []))}")
            passed += 1 if has_content else 0
            failed += 0 if has_content else 1
        except Exception as e:
            print(f"[{i:2}] ERREUR - {e}")
            failed += 1

    print(f"\n{passed}/{len(BRIEFS)} fiches générées sans erreur de schéma.")
    if failed:
        print(f"{failed} échec(s) — voir le détail ci-dessus (CA agent A1 exige 10/10).")


if __name__ == "__main__":
    main()