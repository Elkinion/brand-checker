from __future__ import annotations
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether,
)

from modules.improvements import compute_improvements

BRAND_BLUE = colors.HexColor("#001EB4")
BRAND_DARK = colors.HexColor("#00005A")
GRAY_SOFT = colors.HexColor("#E6E8EE")
GRAY_TEXT = colors.HexColor("#4B5563")

STATUS_COLORS = {
    "pass": (colors.HexColor("#D1FAE5"), colors.HexColor("#065F46")),
    "fail": (colors.HexColor("#FEE2E2"), colors.HexColor("#991B1B")),
    "partial": (colors.HexColor("#FEF3C7"), colors.HexColor("#92400E")),
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    s = {
        "title": ParagraphStyle("bcTitle", parent=base["Title"],
                                fontSize=20, textColor=colors.white,
                                alignment=1, spaceAfter=0),
        "h1": ParagraphStyle("bcH1", parent=base["Heading1"],
                             fontSize=14, textColor=BRAND_DARK,
                             spaceBefore=10, spaceAfter=6),
        "h2": ParagraphStyle("bcH2", parent=base["Heading2"],
                             fontSize=11, textColor=BRAND_DARK,
                             spaceBefore=4, spaceAfter=3),
        "body": ParagraphStyle("bcBody", parent=base["BodyText"],
                               fontSize=9, textColor=colors.black,
                               leading=12, spaceAfter=3),
        "muted": ParagraphStyle("bcMuted", parent=base["BodyText"],
                                fontSize=8, textColor=GRAY_TEXT,
                                leading=10, spaceAfter=2),
        "advice": ParagraphStyle("bcAdvice", parent=base["BodyText"],
                                 fontSize=9, textColor=colors.black,
                                 leading=12, spaceAfter=2, leftIndent=6),
        "score_big": ParagraphStyle("bcScoreBig", parent=base["Title"],
                                    fontSize=40, textColor=colors.white,
                                    alignment=1, spaceAfter=0, leading=42),
        "score_sub": ParagraphStyle("bcScoreSub", parent=base["BodyText"],
                                    fontSize=10, textColor=colors.white,
                                    alignment=1, spaceAfter=0),
    }
    return s


def _header_flowable(name: str) -> Table:
    s = _styles()
    tbl = Table([[Paragraph(f"Brand Checker · {name}", s["title"])]],
                colWidths=[170 * mm], rowHeights=[16 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    return tbl


def _score_flowable(score: dict) -> Table:
    s = _styles()
    total = (score.get("total_pct", 0) or 0) * 100
    obj = (score.get("obj_pct", 0) or 0) * 100
    subj = (score.get("subj_pct", 0) or 0) * 100
    inner = Table(
        [[Paragraph(f"{total:.0f}%", s["score_big"])],
         [Paragraph("SCORE TOTAL", s["score_sub"])],
         [Paragraph(f"Objetivo <b>{obj:.0f}%</b> · Subjetivo <b>{subj:.0f}%</b>",
                    s["score_sub"])]],
        colWidths=[170 * mm],
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
    ]))
    return inner


def _image_flowable(path: str, max_w_mm: float = 80, max_h_mm: float = 60):
    if not path or not Path(path).exists():
        return None
    try:
        img = Image(path)
        iw, ih = img.imageWidth, img.imageHeight
        max_w = max_w_mm * mm
        max_h = max_h_mm * mm
        scale = min(max_w / iw, max_h / ih, 1.0)
        img.drawWidth = iw * scale
        img.drawHeight = ih * scale
        img.hAlign = "CENTER"
        return img
    except Exception:
        return None


def _improvements_table(items: list[dict], top_n: int | None = None) -> Table:
    s = _styles()
    view = items if top_n is None else items[:top_n]
    if not view:
        return Table([["Sin recomendaciones — el score está en su máximo."]],
                     colWidths=[170 * mm])

    data = [[
        Paragraph("<b>#</b>", s["body"]),
        Paragraph("<b>Criterio</b>", s["body"]),
        Paragraph("<b>Estado</b>", s["body"]),
        Paragraph("<b>+pts</b>", s["body"]),
        Paragraph("<b>Consejo</b>", s["body"]),
    ]]
    for i, it in enumerate(view, 1):
        data.append([
            Paragraph(str(i), s["body"]),
            Paragraph(f"<b>{it['label']}</b><br/>"
                      f"<font size=7 color='#6B7280'>{it['kind'].upper()}</font>",
                      s["body"]),
            Paragraph(it["current"], s["body"]),
            Paragraph(f"+{it['gain_pp']:.1f}", s["body"]),
            Paragraph(it["advice"], s["advice"]),
        ])
    tbl = Table(data, colWidths=[8 * mm, 45 * mm, 18 * mm, 15 * mm, 84 * mm],
                repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_SOFT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _rules_table(rows: list[dict], is_obj: bool) -> Table:
    s = _styles()
    if not rows:
        return Table([["Sin resultados."]], colWidths=[170 * mm])
    data = [[
        Paragraph("<b>Criterio</b>", s["body"]),
        Paragraph("<b>Estado</b>", s["body"]),
        Paragraph("<b>Detalle</b>", s["body"]),
    ]]
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_SOFT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, r in enumerate(rows, 1):
        if is_obj:
            status = r.get("status", "fail")
            bg, fg = STATUS_COLORS.get(status, (colors.white, colors.black))
            status_cell = Paragraph(
                f"<font color='{fg.hexval()}'><b>{status.upper()}</b></font>",
                s["body"],
            )
            style_cmds.append(("BACKGROUND", (1, i), (1, i), bg))
        else:
            score = r.get("score")
            status_cell = Paragraph(f"{score}/5" if score is not None else "—",
                                    s["body"])

        detail_field = r.get("detail") if is_obj else r.get("observation", "")
        value_field = r.get("value") if is_obj else ""
        detail_text = f"<b>{value_field}</b> — {detail_field}" if value_field else (detail_field or "")
        data.append([
            Paragraph(r.get("label", ""), s["body"]),
            status_cell,
            Paragraph(detail_text, s["muted"]),
        ])
    tbl = Table(data, colWidths=[55 * mm, 25 * mm, 90 * mm], repeatRows=1)
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def build_pdf(result: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
        title=f"Brand Checker — {result.get('name','')}",
    )
    s = _styles()
    story: list[Any] = []

    story.append(_header_flowable(result.get("name", "Pieza")))
    story.append(Spacer(1, 6))

    story.append(_score_flowable(result.get("score") or {}))
    story.append(Spacer(1, 8))

    # Preview + metadata
    img = _image_flowable(result.get("path", ""))
    meta_lines = [
        Paragraph(f"<b>Archivo:</b> {result.get('name','')}", s["body"]),
        Paragraph(f"<b>Tipo:</b> {result.get('kv_type','')}", s["body"]),
    ]
    subj_impression = ((result.get("subj_data") or {}).get("overall_impression") or "")
    if subj_impression:
        meta_lines.append(Spacer(1, 3))
        meta_lines.append(Paragraph("<b>Impresión general:</b>", s["body"]))
        meta_lines.append(Paragraph(subj_impression, s["muted"]))

    if img is not None:
        story.append(Table([[img, meta_lines]],
                           colWidths=[85 * mm, 85 * mm]))
    else:
        story.extend(meta_lines)
    story.append(Spacer(1, 10))

    # Improvements
    improvements = compute_improvements(result)
    story.append(Paragraph("Cómo mejorar la puntuación", s["h1"]))
    story.append(Paragraph(
        "Ordenado por impacto potencial en el score total (puntos porcentuales).",
        s["muted"],
    ))
    story.append(Spacer(1, 4))
    story.append(_improvements_table(improvements))
    story.append(Spacer(1, 10))

    # Objective rules
    story.append(Paragraph("Evaluación objetiva", s["h1"]))
    story.append(_rules_table(result.get("obj_results") or [], is_obj=True))
    story.append(Spacer(1, 10))

    # Subjective rules
    story.append(Paragraph("Evaluación subjetiva (Gemini)", s["h1"]))
    subj_rows = ((result.get("subj_data") or {}).get("results")) or []
    story.append(_rules_table(subj_rows, is_obj=False))

    doc.build(story)
    return buf.getvalue()
