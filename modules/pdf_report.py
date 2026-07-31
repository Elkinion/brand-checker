from __future__ import annotations
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
)

from modules.improvements import compute_improvements

# ---------------------------------------------------------------------
# Tigo Design System v2.0 tokens
# ---------------------------------------------------------------------
BLUE_500 = colors.HexColor("#001EB4")   # main blue
BLUE_900 = colors.HexColor("#00005A")   # darker blue
BLUE_400 = colors.HexColor("#0026E5")
BLUE_50  = colors.HexColor("#E6F1FF")
CYAN     = colors.HexColor("#44C8F5")
GREEN    = colors.HexColor("#00F52D")
YELLOW   = colors.HexColor("#FFBE00")
GRAY_100 = colors.HexColor("#F5F5F5")
GRAY_200 = colors.HexColor("#EBEBEB")
GRAY_300 = colors.HexColor("#D1D1D1")
GRAY_400 = colors.HexColor("#888888")
GRAY_500 = colors.HexColor("#9E9E9E")
GRAY_600 = colors.HexColor("#767676")
BORDER   = colors.HexColor("#E4E8F0")
BG_OK    = colors.HexColor("#E8F5E9")
OK_TEXT  = colors.HexColor("#155724")
BG_ERR   = colors.HexColor("#FFEBEE")
ERR      = colors.HexColor("#C62828")
BG_WARN  = colors.HexColor("#FFF8E1")
WARN     = colors.HexColor("#8A6900")

STATUS_COLORS = {
    "pass":    (BG_OK,   OK_TEXT),
    "fail":    (BG_ERR,  ERR),
    "partial": (BG_WARN, WARN),
}

# ---------------------------------------------------------------------
# Font registration (DM Sans from static/fonts/, fallback to Helvetica)
# ---------------------------------------------------------------------
_FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"
FONT_REG = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_BLACK = "Helvetica-Bold"


def _register_fonts() -> None:
    global FONT_REG, FONT_BOLD, FONT_BLACK
    candidates = {
        "DMSans": _FONT_DIR / "DMSans-Regular.ttf",
        "DMSans-Bold": _FONT_DIR / "DMSans-Bold.ttf",
        "DMSans-Black": _FONT_DIR / "DMSans-Black.ttf",
    }
    if not all(p.exists() for p in candidates.values()):
        return
    try:
        for name, path in candidates.items():
            pdfmetrics.registerFont(TTFont(name, str(path)))
        FONT_REG, FONT_BOLD, FONT_BLACK = "DMSans", "DMSans-Bold", "DMSans-Black"
    except Exception:
        pass


_register_fonts()

# ---------------------------------------------------------------------
# Brand assets
# ---------------------------------------------------------------------
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "static" / "markethink" / "png"
_HEADER_ICON = _ASSETS_DIR / "Recurso 54.png"
_HEADER_LOGO = _ASSETS_DIR / "LOGO TIGO.png"


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            "bcTitle", fontName=FONT_BLACK, fontSize=18,
            textColor=colors.white, alignment=0, leading=20,
        ),
        "eyebrow": ParagraphStyle(
            "bcEyebrow", fontName=FONT_BOLD, fontSize=8,
            textColor=CYAN, leading=10,
        ),
        "h1": ParagraphStyle(
            "bcH1", fontName=FONT_BLACK, fontSize=16,
            textColor=BLUE_900, spaceBefore=8, spaceAfter=4, leading=18,
        ),
        "h2": ParagraphStyle(
            "bcH2", fontName=FONT_BOLD, fontSize=10,
            textColor=BLUE_500, spaceBefore=2, spaceAfter=2, leading=12,
        ),
        "body": ParagraphStyle(
            "bcBody", fontName=FONT_REG, fontSize=9,
            textColor=colors.black, leading=12, spaceAfter=2,
        ),
        "muted": ParagraphStyle(
            "bcMuted", fontName=FONT_REG, fontSize=8,
            textColor=GRAY_600, leading=11, spaceAfter=1,
        ),
        "advice": ParagraphStyle(
            "bcAdvice", fontName=FONT_REG, fontSize=9,
            textColor=colors.black, leading=12, spaceAfter=1,
        ),
        "score_big": ParagraphStyle(
            "bcScoreBig", fontName=FONT_BLACK, fontSize=44,
            textColor=colors.white, alignment=1, leading=44,
        ),
        "score_label": ParagraphStyle(
            "bcScoreLabel", fontName=FONT_BOLD, fontSize=9,
            textColor=CYAN, alignment=1, leading=12,
        ),
        "score_sub": ParagraphStyle(
            "bcScoreSub", fontName=FONT_REG, fontSize=10,
            textColor=colors.white, alignment=1, leading=12,
        ),
        "footer": ParagraphStyle(
            "bcFooter", fontName=FONT_REG, fontSize=7,
            textColor=GRAY_500, alignment=1, leading=9,
        ),
    }


def _brand_icon(path: Path, height_mm: float):
    if not path.exists():
        return None
    try:
        img = Image(str(path))
        iw, ih = img.imageWidth, img.imageHeight
        target_h = height_mm * mm
        scale = target_h / ih
        img.drawWidth = iw * scale
        img.drawHeight = target_h
        return img
    except Exception:
        return None


def _header_flowable(subtitle: str) -> Table:
    s = _styles()
    icon = _brand_icon(_HEADER_ICON, height_mm=12)
    title_cell = [
        Paragraph("BRAND CHECKER · TIGO", s["eyebrow"]),
        Spacer(1, 3),
        Paragraph(subtitle, s["title"]),
    ]
    left_cell = icon if icon else Paragraph("", s["body"])
    tbl = Table([[left_cell, title_cell]],
                colWidths=[22 * mm, 148 * mm], rowHeights=[22 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_500),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 12),
        ("RIGHTPADDING", (0, 0), (0, 0), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 6),
        ("RIGHTPADDING", (1, 0), (1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _score_flowable(score: dict) -> Table:
    s = _styles()
    total = (score.get("total_pct", 0) or 0) * 100
    obj = (score.get("obj_pct", 0) or 0) * 100
    subj = (score.get("subj_pct", 0) or 0) * 100
    inner = Table(
        [[Paragraph("SCORE TOTAL", s["score_label"])],
         [Paragraph(f"{total:.0f}%", s["score_big"])],
         [Paragraph(f"Objetivo <b>{obj:.0f}%</b>  ·  Subjetivo <b>{subj:.0f}%</b>",
                    s["score_sub"])]],
        colWidths=[170 * mm],
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_900),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
    ]))
    return inner


def _accent_h1(text: str):
    """Section heading with cyan accent bar to the left."""
    s = _styles()
    bar = Table([[""]], colWidths=[2 * mm], rowHeights=[7 * mm])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CYAN)]))
    row = Table([[bar, Paragraph(text, s["h1"])]],
                colWidths=[5 * mm, 165 * mm])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return row


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
        Paragraph("<b>CRITERIO</b>", s["h2"]),
        Paragraph("<b>ESTADO</b>", s["h2"]),
        Paragraph("<b>+PTS</b>", s["h2"]),
        Paragraph("<b>CONSEJO</b>", s["h2"]),
    ]]
    for i, it in enumerate(view, 1):
        data.append([
            Paragraph(str(i), s["body"]),
            Paragraph(f"<b>{it['label']}</b><br/>"
                      f"<font size=7 color='{GRAY_500.hexval()}'>{it['kind'].upper()}</font>",
                      s["body"]),
            Paragraph(it["current"], s["body"]),
            Paragraph(f"<b><font color='{OK_TEXT.hexval()}'>+{it['gain_pp']:.1f}</font></b>",
                      s["body"]),
            Paragraph(it["advice"], s["advice"]),
        ])
    tbl = Table(data, colWidths=[8 * mm, 45 * mm, 18 * mm, 15 * mm, 84 * mm],
                repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE_50),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BLUE_500),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _rules_table(rows: list[dict], is_obj: bool) -> Table:
    s = _styles()
    if not rows:
        return Table([["Sin resultados."]], colWidths=[170 * mm])
    data = [[
        Paragraph("<b>CRITERIO</b>", s["h2"]),
        Paragraph("<b>ESTADO</b>", s["h2"]),
        Paragraph("<b>DETALLE</b>", s["h2"]),
    ]]
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE_50),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BLUE_500),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
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
            score_txt = f"{score}/5" if score is not None else "—"
            status_cell = Paragraph(f"<b>{score_txt}</b>", s["body"])

        detail_field = r.get("detail") if is_obj else r.get("observation", "")
        value_field = r.get("value") if is_obj else ""
        detail_text = (f"<b>{value_field}</b> — {detail_field}"
                       if value_field else (detail_field or ""))
        data.append([
            Paragraph(r.get("label", ""), s["body"]),
            status_cell,
            Paragraph(detail_text, s["muted"]),
        ])
    tbl = Table(data, colWidths=[55 * mm, 25 * mm, 90 * mm], repeatRows=1)
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _footer(canvas, doc):
    """Small footer bar on every page — DS-aligned."""
    canvas.saveState()
    canvas.setFillColor(GRAY_500)
    canvas.setFont(FONT_REG, 7)
    page_num = canvas.getPageNumber()
    footer_text = f"Brand Checker · Tigo · Página {page_num}"
    canvas.drawCentredString(A4[0] / 2, 8 * mm, footer_text)
    canvas.restoreState()


def build_pdf(result: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=14 * mm, bottomMargin=14 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
        title=f"Brand Checker — {result.get('name','')}",
        author="Tigo Brand Checker",
    )
    s = _styles()
    story: list[Any] = []

    story.append(_header_flowable(result.get("name", "Pieza")))
    story.append(Spacer(1, 8))

    story.append(_score_flowable(result.get("score") or {}))
    story.append(Spacer(1, 10))

    # Preview + metadata
    img = _image_flowable(result.get("path", ""))
    meta_lines = [
        Paragraph(f"<b>ARCHIVO</b>", s["h2"]),
        Paragraph(result.get('name', ''), s["body"]),
        Spacer(1, 4),
        Paragraph(f"<b>TIPO DE PIEZA</b>", s["h2"]),
        Paragraph(result.get('kv_type', ''), s["body"]),
    ]
    subj_impression = ((result.get("subj_data") or {}).get("overall_impression") or "")
    if subj_impression:
        meta_lines.extend([
            Spacer(1, 4),
            Paragraph("<b>IMPRESIÓN GENERAL</b>", s["h2"]),
            Paragraph(subj_impression, s["muted"]),
        ])

    if img is not None:
        meta_tbl = Table([[img, meta_lines]],
                         colWidths=[85 * mm, 85 * mm])
        meta_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (0, 0), 0.5, BORDER),
            ("LEFTPADDING", (1, 0), (1, 0), 12),
        ]))
        story.append(meta_tbl)
    else:
        story.extend(meta_lines)
    story.append(Spacer(1, 12))

    # Improvements
    improvements = compute_improvements(result)
    story.append(_accent_h1("Cómo mejorar la puntuación"))
    story.append(Paragraph(
        "Ordenado por impacto potencial en el score total (puntos porcentuales).",
        s["muted"],
    ))
    story.append(Spacer(1, 4))
    story.append(_improvements_table(improvements))
    story.append(Spacer(1, 12))

    # Objective rules
    story.append(_accent_h1("Evaluación objetiva"))
    story.append(Spacer(1, 4))
    story.append(_rules_table(result.get("obj_results") or [], is_obj=True))
    story.append(Spacer(1, 12))

    # Subjective rules
    story.append(_accent_h1("Evaluación subjetiva (Gemini)"))
    story.append(Spacer(1, 4))
    subj_rows = ((result.get("subj_data") or {}).get("results")) or []
    story.append(_rules_table(subj_rows, is_obj=False))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
