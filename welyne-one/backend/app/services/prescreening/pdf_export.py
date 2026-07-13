"""
Export PDF d'une conversation A5 (spec §6-A5 : « conversation exportable en
PDF pour le dossier »). Un PDF = un dialogue complet : en-tête (candidat,
offre, canal, consentement horodaté), transcript chronologique, puis réponses
extraites + signaux (drapeaux) s'il y en a. Usage archive/dossier candidat —
mise en page volontairement sobre.
"""
from __future__ import annotations

import io
from typing import TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

if TYPE_CHECKING:
    from app.models.conversation import Conversation

_ROLE_LABELS = {"agent": "Assistant IA", "candidate": "Candidat", "system": "Système"}
_FLAG_LABELS = {
    "off_topic_handoff": "Question transmise au recruteur",
    "unclear_after_retry": "Réponse non clarifiée",
    "contradiction": "Contradiction signalée",
    "positive_signal": "Signal positif",
    "warning_signal": "Signal à revoir",
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": base["Title"],
        "h2": base["Heading2"],
        "meta": ParagraphStyle("meta", parent=base["Normal"], textColor=colors.grey, fontSize=9),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10, leading=14, alignment=TA_LEFT),
        "agent": ParagraphStyle(
            "agent", parent=base["Normal"], fontSize=10, leading=14,
            backColor=colors.whitesmoke, borderPadding=6, spaceAfter=6,
        ),
        "candidate": ParagraphStyle(
            "candidate", parent=base["Normal"], fontSize=10, leading=14,
            backColor=colors.HexColor("#eaf2ff"), borderPadding=6, spaceAfter=6,
        ),
        "system": ParagraphStyle(
            "system", parent=base["Normal"], fontSize=9, leading=12,
            textColor=colors.grey, spaceAfter=6, italic=True,
        ),
        "small": ParagraphStyle("small", parent=base["Normal"], fontSize=9, leading=12),
    }


def _fmt_dt(dt) -> str:
    return dt.strftime("%d/%m/%Y %H:%M UTC") if dt else "—"


def build_prescreen_pdf(conv: "Conversation") -> bytes:
    """Construit le PDF du dialogue A5 et retourne les octets (pas d'écriture disque)."""
    styles = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
        title="Pré-qualification candidat",
    )
    story: list = []

    application = conv.application
    candidate = application.candidate if application else None
    job = application.job if application else None

    story.append(Paragraph("Pré-qualification candidat — dossier", styles["title"]))
    story.append(Spacer(1, 4 * mm))

    meta_rows = [
        ["Candidat", candidate.full_name if candidate else "—"],
        ["Offre", job.title if job else "—"],
        ["Canal", conv.channel],
        ["Langue", conv.language.upper()],
        ["Statut", conv.status],
        ["Consentement enregistré", _fmt_dt(conv.consent_at)],
        ["Conversation ID", str(conv.id)],
    ]
    meta_table = Table(meta_rows, colWidths=[45 * mm, 120 * mm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.lightgrey),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Transcript", styles["h2"]))
    story.append(Spacer(1, 2 * mm))
    for msg in conv.messages:
        label = _ROLE_LABELS.get(msg.role, msg.role)
        style = styles.get(msg.role, styles["body"])
        prefix = f"<b>{label}</b> — {_fmt_dt(msg.created_at)}<br/>"
        story.append(Paragraph(prefix + (msg.body or "").replace("\n", "<br/>"), style))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Réponses extraites", styles["h2"]))
    story.append(Spacer(1, 2 * mm))
    if conv.extracted:
        rows = [["Slot", "Valeur"]] + [[k, str(v)] for k, v in conv.extracted.items()]
        ans_table = Table(rows, colWidths=[55 * mm, 110 * mm])
        ans_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(ans_table)
    else:
        story.append(Paragraph("Aucune réponse enregistrée.", styles["small"]))

    if conv.flags:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("Signaux", styles["h2"]))
        story.append(Spacer(1, 2 * mm))
        rows = [["Type", "Détail"]]
        for f in conv.flags:
            if not isinstance(f, dict):
                continue
            rows.append([_FLAG_LABELS.get(f.get("type"), f.get("type", "—")), f.get("note", "")])
        flag_table = Table(rows, colWidths=[55 * mm, 110 * mm])
        flag_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(flag_table)

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "Document généré automatiquement par Welyne One (agent A5). "
        "Décision finale toujours validée par un recruteur humain.",
        styles["meta"],
    ))

    doc.build(story)
    return buf.getvalue()