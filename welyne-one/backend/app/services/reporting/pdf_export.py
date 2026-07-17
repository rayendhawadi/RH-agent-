"""Rapport PDF A9 (§6-A9, livrable : "export CSV/PDF")."""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def build_report_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [Paragraph("Welyne One — Rapport de reporting (A9)", styles["Title"]), Spacer(1, 12)]

    story.append(Paragraph(f"Total candidatures : {data['total']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    def _table(title: str, rows: list[list[str]]) -> None:
        story.append(Paragraph(title, styles["Heading2"]))
        t = Table([["Clé", "Valeur"]] + rows, colWidths=[260, 200])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e4e7ec")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(t)
        story.append(Spacer(1, 14))

    _table("Funnel par statut", [[k, str(v)] for k, v in data["by_status"].items()])
    _table("Candidatures par source", [[k, str(v)] for k, v in data["by_source"].items()])
    _table("Délais moyens par étape (heures)", [[s["stage"], f"{s['avg_hours']}h (n={s['n']})"] for s in data["stage_timings"]])

    sla = data["sla"]
    _table("SLA parsing/scoring", [
        ["Parsing — moyenne", f"{sla['parsing']['avg_min']} min"],
        ["Parsing — p95", f"{sla['parsing']['p95_min']} min"],
        ["Scoring — moyenne", f"{sla['scoring']['avg_min']} min"],
        ["Scoring — p95", f"{sla['scoring']['p95_min']} min"],
    ])
    _table("Distribution des scores", [[b["range"], str(b["count"])] for b in data["score_distribution"]])

    cost = data["cost"]
    _table("Coût tokens estimé", [
        ["Fenêtre", f"{cost['window_days']} jours"],
        ["Tokens totaux", str(cost["total_tokens"])],
        ["Coût estimé (USD)", str(cost["total_cost_usd_estimate"])],
        ["Embauches", str(cost["hires"])],
        ["Coût estimé / embauche (USD)", str(cost["cost_usd_per_hire_estimate"] or "—")],
    ])

    doc.build(story)
    return buf.getvalue()