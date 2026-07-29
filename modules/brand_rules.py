from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

from modules.utils import hex_to_rgb, rgb_distance

# ---------------------------------------------------------------------
# Paletas oficiales
# ---------------------------------------------------------------------
BRAND_PALETTE: dict[str, str] = {
    "main_blue":   "#001EB4",
    "darker_blue": "#00005A",
    "bright_blue": "#44C8F5",
    "yellow":      "#FFC200",
    "white":       "#FFFFFF",
    "magenta":     "#ED1966",
    "orange":      "#FB561E",
    "green":       "#00F52D",
    "lime_green":  "#BEFF00",
}

BRAND_PALETTE_PRINT: dict[str, str] = {
    "main_blue":   "#001EB4",
    "white":       "#FFFFFF",
    "bright_blue": "#44C8F5",
    "yellow":      "#FFC200",
    "darker_blue": "#00005A",
    "green":       "#00F52D",
    "lime_green":  "#BEFF00",
}

BRAND_PALETTE_DIGITAL: dict[str, str] = {
    "main_blue":   "#001EB4",
    "white":       "#FFFFFF",
    "bright_blue": "#44C8F5",
    "yellow":      "#FFC200",
    "darker_blue": "#00005A",
    "magenta":     "#ED1966",
    "green":       "#00F52D",
    "lime_green":  "#BEFF00",
}

# OOH (out-of-home / vallas): derived from the CMYK spec in the brand manual.
# Naive CMYK->sRGB: R=255*(1-C)*(1-K), G=255*(1-M)*(1-K), B=255*(1-Y)*(1-K).
# Values come from the "CMYK" column of the official brand palette.
BRAND_PALETTE_OOH: dict[str, str] = {
    "main_blue":   "#0020D9",  # C100 M85 Y0  K15
    "bright_blue": "#66FFF2",  # C60  M0  Y5  K0
    "yellow":      "#FFBF00",  # C0   M25 Y100 K0
    "darker_blue": "#000D80",  # C100 M90 Y0  K50
    "magenta":     "#FF0099",  # C0   M100 Y40 K0
    "white":       "#FFFFFF",
}

PRIMARY_COLORS   = {"main_blue", "darker_blue", "bright_blue", "yellow", "white"}
SECONDARY_COLORS = {"magenta", "orange", "green", "lime_green"}

COLOR_MATCH_THRESHOLD = 80
# Print/photograph variance is larger — loosen tolerance for OOH.
COLOR_MATCH_THRESHOLD_OOH = 110


def get_palette_for_gama(gama: str) -> dict[str, str]:
    if gama == "ooh":
        return BRAND_PALETTE_OOH
    if gama == "impresos":
        return BRAND_PALETTE_PRINT
    if gama == "digitales":
        return BRAND_PALETTE_DIGITAL
    return BRAND_PALETTE


def get_threshold_for_gama(gama: str) -> float:
    return COLOR_MATCH_THRESHOLD_OOH if gama == "ooh" else COLOR_MATCH_THRESHOLD
BRAND_LOGO_NAMES = ["Tigo"]
REQUIRED_DISCLAIMERS = ["Términos y condiciones", "Aplican restricciones"]


def distances_to_palette(hex_str: str, palette: dict[str, str] = BRAND_PALETTE) -> dict[str, float]:
    rgb1 = hex_to_rgb(hex_str)
    return {name: rgb_distance(rgb1, hex_to_rgb(hx)) for name, hx in palette.items()}


def nearest_palette_color(hex_str: str, palette: dict[str, str] = BRAND_PALETTE) -> tuple[str, float]:
    dists = distances_to_palette(hex_str, palette)
    name = min(dists, key=dists.get)
    return name, dists[name]


# ---------------------------------------------------------------------
# Perfiles por tipo de pieza
# ---------------------------------------------------------------------
@dataclass
class Range:
    min: float
    max: float

@dataclass
class TextLimit:
    words: int | None = None
    lines: int | None = None
    chars: int | None = None

@dataclass
class Profile:
    label: str
    gama: str  # "impresos" | "digitales" | "ambos" | "ooh"
    foto: Range | None = None
    oferta_target: float | None = None
    oferta_modulos_max: int | None = None
    propuesta_max: float | None = None
    titular: TextLimit | None = None
    secundario: TextLimit | None = None
    legal: TextLimit | None = None
    flags: tuple[str, ...] = ()
    varia_tipografia: bool = False


PIECE_PROFILES: dict[str, Profile] = {
    "tactico_pop": Profile(
        label="Táctico POP", gama="ambos",
        foto=Range(0.40, 0.50),
        oferta_target=0.35, oferta_modulos_max=3,
        propuesta_max=0.20,
        titular=TextLimit(words=10, lines=3),
        secundario=TextLimit(words=5, lines=2),
        legal=TextLimit(chars=60, lines=2),
    ),
    "kv_fotografia": Profile(
        label="KV con Fotografía", gama="ambos",
        foto=Range(0.40, 0.60),
        oferta_target=0.35, oferta_modulos_max=3,
        propuesta_max=0.20,
        titular=TextLimit(words=10, lines=3),
        secundario=TextLimit(words=5, lines=2),
        legal=TextLimit(chars=60, lines=2),
        varia_tipografia=True,
    ),
    "atl_full_foto": Profile(
        label="ATL Full Fotográfico", gama="impresos",
        foto=Range(0.85, 1.00),
        titular=TextLimit(words=10, lines=3),
    ),
    "atl_background_color": Profile(
        label="ATL Background Color", gama="impresos",
        foto=Range(0.85, 1.00),
        titular=TextLimit(words=10, lines=3),
        flags=("foto_modulos",),
    ),
    "social_post": Profile(
        label="Social Media — Post", gama="digitales",
        oferta_target=0.35, oferta_modulos_max=3,
        propuesta_max=0.20,
        titular=TextLimit(words=10, lines=3),
        secundario=TextLimit(words=5, lines=2),
        legal=TextLimit(chars=60, lines=2),
        flags=("tag_bu", "product_shot"),
        varia_tipografia=True,
    ),
    "social_story": Profile(
        label="Social Media — Story", gama="digitales",
        oferta_target=0.35, oferta_modulos_max=3,
        propuesta_max=0.20,
        titular=TextLimit(words=10, lines=3),
        secundario=TextLimit(words=5, lines=2),
        legal=TextLimit(chars=60, lines=2),
        flags=("tag_bu", "product_shot", "area_seg_ig"),
        varia_tipografia=True,
    ),
    "social_feed": Profile(
        label="Social Media — Feed", gama="digitales",
        oferta_target=0.35, oferta_modulos_max=3,
        propuesta_max=0.20,
        titular=TextLimit(words=10, lines=3),
        secundario=TextLimit(words=5, lines=2),
        legal=TextLimit(chars=60, lines=2),
        flags=("tag_bu", "product_shot"),
        varia_tipografia=True,
    ),
    "afiche_foto_tienda": Profile(
        label="Afiche Fotográfico Tienda", gama="impresos",
        foto=Range(0.40, 0.80),
        oferta_target=0.35, oferta_modulos_max=3,
        propuesta_max=0.20,
        titular=TextLimit(words=10, lines=3),
        secundario=TextLimit(words=5, lines=2),
        legal=TextLimit(chars=60, lines=2),
        flags=("tag_bu", "marco_bu"),
        varia_tipografia=True,
    ),
    "afiche_tienda": Profile(
        label="Afiche Tienda", gama="impresos",
        foto=Range(0.40, 0.80),
        oferta_target=0.35, oferta_modulos_max=3,
        propuesta_max=0.20,
        titular=TextLimit(words=10, lines=3),
        secundario=TextLimit(words=5, lines=2),
        legal=TextLimit(chars=60, lines=2),
        flags=("tag_bu", "marco_bu"),
        varia_tipografia=True,
    ),
    "afiche_promo_tienda": Profile(
        label="Afiche Promo Tienda", gama="impresos",
        oferta_target=0.35, oferta_modulos_max=3,
        propuesta_max=0.60,  # excepción
        titular=TextLimit(words=10, lines=3),
        secundario=TextLimit(words=5, lines=2),
        legal=TextLimit(chars=60, lines=2),
        flags=("marco_bu",),
        varia_tipografia=True,
    ),
    "ooh_valla": Profile(
        label="OOH / Valla exterior", gama="ooh",
        foto=Range(0.40, 0.80),
        oferta_target=0.35, oferta_modulos_max=3,
        propuesta_max=0.20,
        titular=TextLimit(words=8, lines=2),
        secundario=TextLimit(words=5, lines=2),
        legal=TextLimit(chars=60, lines=2),
        varia_tipografia=True,
    ),
}


def get_profile(kv_type: str) -> Profile:
    return PIECE_PROFILES.get(kv_type) or PIECE_PROFILES["tactico_pop"]


# ---------------------------------------------------------------------
# Reglas OBJETIVAS
# ---------------------------------------------------------------------
# `cv` es un dict con: logos, dominant_colors, full_text, text_blocks,
# safe_search, reference_matches, dominant_area (opcional), offer_area (opcional).

Status = str  # "pass" | "fail" | "partial"

@dataclass
class RuleResult:
    status: Status
    value: str
    detail: str

@dataclass
class ObjectiveRule:
    id: str
    label: str
    weight: int
    fn: Callable[[dict, Profile], RuleResult]
    applies_when: Callable[[Profile], bool] | None = None


def _pct(v: float, dp: int = 1) -> str:
    return f"{round(v * 100, dp)}%"


def _rule_logo_detected(cv: dict, profile: Profile) -> RuleResult:
    from modules.logo_matcher import load_reference_logos  # avoid circular at import
    refs_loaded = len(load_reference_logos()) > 0
    ref_hits = cv.get("reference_matches") or []
    logos = cv.get("logos") or []

    if refs_loaded:
        if ref_hits:
            names = list(dict.fromkeys(h.get("name", "") for h in ref_hits))
            if len(names) == 1:
                names_str = names[0]
            elif len(names) == 2:
                names_str = " y ".join(names)
            else:
                names_str = ", ".join(names[:-1]) + f" y {names[-1]}"
            locs = [str(h.get("location")) for h in ref_hits if h.get("location")]
            loc_str = f" Ubicación: {'; '.join(dict.fromkeys(locs))}." if locs else ""
            label = "Logo de marca detectado" if len(names) == 1 else f"{len(names)} logos de marca detectados"
            return RuleResult("pass", names_str, f"{label}: {names_str}.{loc_str}")
        elif logos:
            return RuleResult(
                "partial",
                ", ".join(l.get("description", "") for l in logos),
                "Vision detectó logos, pero Gemini no encontró ninguna referencia de static/logos.",
            )
        else:
            return RuleResult("fail", "No detectado",
                              "Ningún logo de referencia presente en la pieza.")
    elif logos:
        return RuleResult(
            "pass",
            ", ".join(l.get("description", "") for l in logos),
            f"Se detectaron {len(logos)} logo(s). (Sin referencias en static/logos)",
        )
    else:
        return RuleResult("fail", "No detectado", "No se detectó ningún logo en la imagen.")


def _rule_logo_max_width(cv: dict, profile: Profile) -> RuleResult:
    widths: list[float] = []
    for l in cv.get("logos") or []:
        rw = l.get("relative_width")
        if rw is not None:
            widths.append(float(rw))
    for m in cv.get("reference_matches") or []:
        rw = m.get("relative_width")
        if rw is not None:
            widths.append(float(rw))
    if not widths:
        return RuleResult("partial", "—", "Dato no disponible: no se pudo medir el ancho del logo.")
    max_w = max(widths)
    pct_txt = f"{round(max_w * 100, 1)}%"
    if max_w <= 1 / 3:
        return RuleResult("pass", pct_txt,
                          f"El logo ocupa {pct_txt} del ancho del KV (límite 33%).")
    return RuleResult("fail", pct_txt,
                      f"El logo ocupa {pct_txt} del ancho del KV — excede el límite del 33%.")


def _rule_brand_colors_usage(cv: dict, profile: Profile) -> RuleResult:
    colors = cv.get("dominant_colors") or []
    if not colors:
        return RuleResult("fail", "—", "No se pudieron extraer colores dominantes.")
    primarios = sorted({c["nearest_palette"] for c in colors if c.get("is_primary")})
    secundarios = sorted({c["nearest_palette"] for c in colors if c.get("is_secondary")})
    np_, ns = len(primarios), len(secundarios)
    detail = (
        f"Primarios detectados ({np_}): {', '.join(primarios) if primarios else 'ninguno'}. "
        f"Secundarios detectados ({ns}): {', '.join(secundarios) if secundarios else 'ninguno'}."
    )
    val = f"P:{np_} / S:{ns}"
    if np_ >= 2 and ns <= 1:
        return RuleResult("pass", val, f"Uso correcto de la paleta. {detail}")
    if np_ == 0 or ns >= 3:
        return RuleResult("fail", val, f"Uso incorrecto de la paleta. {detail}")
    if np_ == 1 or ns == 2:
        return RuleResult("partial", val, f"Uso parcial de la paleta. {detail}")
    return RuleResult("partial", val, f"Uso aceptable pero mejorable. {detail}")


def _rule_color_palette(cv: dict, profile: Profile) -> RuleResult:
    colors = cv.get("dominant_colors") or []
    if not colors:
        return RuleResult("fail", "—", "No se pudieron extraer colores dominantes.")
    total = len(colors)
    matches = sum(1 for c in colors if c.get("is_brand"))
    val = f"{matches}/{total} match"
    parts = []
    for c in colors:
        tag = " [P]" if c.get("is_primary") else " [S]" if c.get("is_secondary") else ""
        pct = (c.get("pixel_fraction") or 0) * 100
        parts.append(f"{c['hex']} ({pct:.1f}%){tag}")
    all_detail = f" Colores detectados ({total}): {', '.join(parts)}."
    if matches >= 2:
        return RuleResult("pass", val, "Los colores dominantes coinciden con la paleta oficial." + all_detail)
    if matches == 1:
        return RuleResult("partial", val, "Solo un color dominante coincide con la paleta." + all_detail)
    return RuleResult("fail", val, "Ningún color dominante coincide con la paleta oficial." + all_detail)


def _rule_disclaimer(cv: dict, profile: Profile) -> RuleResult:
    max_chars = (profile.legal.chars if profile.legal else 60) or 60
    max_lines = (profile.legal.lines if profile.legal else 2) or 2
    txt_raw = cv.get("full_text") or ""
    txt = txt_raw.lower()
    hits = [d for d in REQUIRED_DISCLAIMERS if d.lower() in txt]

    legal_note = ""
    if hits:
        matched_lines = [
            line for line in txt_raw.split("\n")
            if any(d.lower() in line.lower() for d in REQUIRED_DISCLAIMERS)
        ]
        n_chars = sum(len(l) for l in matched_lines) + max(0, len(matched_lines) - 1)
        if n_chars > max_chars or len(matched_lines) > max_lines:
            legal_note = (
                f" Nota: el texto legal es extenso ({n_chars} car., "
                f"{len(matched_lines)} línea(s); máx {max_chars} / {max_lines})."
            )
        return RuleResult("pass", f"{len(hits)} encontrado(s)",
                          "Se detectó disclaimer legal en el texto." + legal_note)
    return RuleResult("fail", "0", "No se encontró disclaimer legal requerido.")


def _rule_text_simplicity(cv: dict, profile: Profile) -> RuleResult:
    main_words_max = (profile.titular.words if profile.titular else 10) or 10
    main_lines_max = (profile.titular.lines if profile.titular else 3) or 3
    sec_words_max = (profile.secundario.words if profile.secundario else None)
    sec_lines_max = (profile.secundario.lines if profile.secundario else None)

    blocks = cv.get("text_blocks") or []
    if not blocks:
        return RuleResult("partial", "0 bloques", "No hay bloques de texto detectados por OCR.")

    blocks_str = [str(b) for b in blocks]
    ordered = sorted(blocks_str, key=len, reverse=True)

    def _count_words(s: str) -> int:
        return len(s.strip().split()) if s and s.strip() else 0

    def _count_lines(s: str) -> int:
        return len(s.split("\n")) if s else 0

    main_txt = ordered[0]
    mw, ml = _count_words(main_txt), _count_lines(main_txt)
    main_ok = mw <= main_words_max and ml <= main_lines_max

    sw = sl = 0
    sec_ok = True
    if len(ordered) >= 2 and sec_words_max is not None:
        sec_txt = ordered[1]
        sw, sl = _count_words(sec_txt), _count_lines(sec_txt)
        sec_ok = sw <= sec_words_max and (sec_lines_max is None or sl <= sec_lines_max)

    detail = (
        f"Principal: {mw} pal / {ml} líneas (máx {main_words_max}/{main_lines_max}). "
        f"Secundario: {sw} pal / {sl} líneas."
    )
    if main_ok and sec_ok:
        return RuleResult("pass", "OK", f"Mensaje simple. {detail}")
    if main_ok or sec_ok:
        return RuleResult("partial", "Parcial", f"Solo un mensaje cumple. {detail}")
    return RuleResult("fail", "Saturado", f"Mensajes demasiado largos. {detail}")


def _rule_photo_area(cv: dict, profile: Profile) -> RuleResult:
    assert profile.foto is not None
    lo, hi = profile.foto.min, profile.foto.max
    area = cv.get("dominant_area")
    if area is None:
        objs = cv.get("image_objects") or []
        if objs:
            area = max((o.get("relative_area") or 0) for o in objs)
    if area is None:
        return RuleResult("partial", "—",
                          f"Dato no disponible. Rango esperado: {lo*100:.0f}–{hi*100:.0f}%.")
    pct_txt = f"{round(area * 100, 1)}%"
    soft_lo = max(0.0, lo - 0.10)
    if lo <= area <= hi:
        return RuleResult("pass", pct_txt,
                          f"La fotografía ocupa el área recomendada ({lo*100:.0f}–{hi*100:.0f}%).")
    if soft_lo <= area < lo:
        return RuleResult("partial", pct_txt,
                          f"Cerca del rango pero por debajo (esperado {lo*100:.0f}–{hi*100:.0f}%).")
    return RuleResult("fail", pct_txt,
                      f"Fuera del rango esperado ({lo*100:.0f}–{hi*100:.0f}%).")


def _rule_offer_area(cv: dict, profile: Profile) -> RuleResult:
    assert profile.oferta_target is not None
    target = profile.oferta_target
    lo, hi = target - 0.05, target + 0.05
    area = cv.get("offer_area")
    if area is None:
        return RuleResult("partial", "—", f"Dato no disponible. Target ~{target*100:.0f}%.")
    pct_txt = f"{round(area * 100, 1)}%"
    if lo <= area <= hi:
        return RuleResult("pass", pct_txt, f"Bloque de oferta en target (~{target*100:.0f}%).")
    if (lo - 0.10) <= area < lo:
        return RuleResult("partial", pct_txt,
                          f"Bloque de oferta algo pequeño (target ~{target*100:.0f}%).")
    return RuleResult("fail", pct_txt, f"Fuera del rango esperado (~{target*100:.0f}%).")


def _rule_propuesta_valor_area(cv: dict, profile: Profile) -> RuleResult:
    assert profile.propuesta_max is not None
    max_prop = profile.propuesta_max
    area = cv.get("additional_area") or cv.get("propuesta_area")
    if area is None:
        return RuleResult("partial", "—",
                          f"Dato no disponible. Máx propuesta: {max_prop*100:.0f}%.")
    pct_txt = f"{round(area * 100, 1)}%"
    if area <= max_prop:
        return RuleResult("pass", pct_txt,
                          f"Propuesta de valor dentro del máximo ({max_prop*100:.0f}%).")
    if area <= max_prop + 0.05:
        return RuleResult("partial", pct_txt,
                          f"Excede ligeramente el máximo ({max_prop*100:.0f}%).")
    return RuleResult("fail", pct_txt, f"Ocupa demasiado espacio (>{max_prop*100:.0f}%).")


def _rule_gama_coherence(cv: dict, profile: Profile) -> RuleResult:
    colors = cv.get("dominant_colors") or []
    if not colors:
        return RuleResult("partial", "—", "Sin colores dominantes para evaluar gama.")
    threshold = get_threshold_for_gama(profile.gama)
    magenta_frac = sum(
        (c.get("pixel_fraction") or 0)
        for c in colors
        if c.get("nearest_palette") == "magenta"
        and (c.get("nearest_distance") or 1e9) < threshold
    )
    pct = round(magenta_frac * 100, 1)
    if profile.gama == "impresos":
        if magenta_frac > 0.05:
            return RuleResult("fail", f"{pct}% magenta",
                              "El magenta es color digital: no debe usarse como proporcional en impresos (sólo puntual, ej. tag Flex).")
        if magenta_frac > 0.01:
            return RuleResult("partial", f"{pct}% magenta",
                              "Magenta presente en pieza impresa; verificar que sea puntual (tag Flex).")
        return RuleResult("pass", f"{pct}% magenta",
                          "Sin uso proporcional de magenta en pieza impresa.")
    if profile.gama == "ooh":
        return RuleResult("pass", f"{pct}% magenta",
                          "Gama OOH (CMYK): paleta impresa con magenta permitido como secundario.")
    return RuleResult("pass", f"{pct}% magenta",
                      "Gama digital: el magenta es válido como acento secundario.")


def _rule_safe_search(cv: dict, profile: Profile) -> RuleResult:
    ss = cv.get("safe_search") or {}
    risky_levels = {"LIKELY", "VERY_LIKELY"}
    risky = [k for k, v in ss.items() if v in risky_levels]
    if not risky:
        return RuleResult("pass", "OK", "No se detectó contenido inapropiado.")
    return RuleResult("fail", ", ".join(risky), f"Categorías de riesgo: {', '.join(risky)}")


OBJECTIVE_RULES: list[ObjectiveRule] = [
    ObjectiveRule("logo_detected", "Logo detectado", 2, _rule_logo_detected),
    ObjectiveRule("logo_max_width", "Ancho del logo ≤ 1/3 del KV", 1, _rule_logo_max_width),
    ObjectiveRule("brand_colors_usage", "Uso correcto de colores primarios y secundarios", 2,
                  _rule_brand_colors_usage),
    ObjectiveRule("color_palette", "Colores oficiales de marca (general)", 1, _rule_color_palette),
    ObjectiveRule("disclaimer", "Disclaimer legal en OCR", 1, _rule_disclaimer,
                  applies_when=lambda p: p.legal is not None),
    ObjectiveRule("text_simplicity", "Simplicidad de mensaje (líneas y palabras)", 1,
                  _rule_text_simplicity, applies_when=lambda p: p.titular is not None),
    ObjectiveRule("photo_area", "Área de fotografía", 1, _rule_photo_area,
                  applies_when=lambda p: p.foto is not None),
    ObjectiveRule("offer_area", "Área de oferta", 1, _rule_offer_area,
                  applies_when=lambda p: p.oferta_target is not None),
    ObjectiveRule("propuesta_valor_area", "Propuesta de valor (máx %)", 1,
                  _rule_propuesta_valor_area,
                  applies_when=lambda p: p.propuesta_max is not None),
    ObjectiveRule("gama_coherence", "Coherencia de gama (impresos vs digital)", 1,
                  _rule_gama_coherence),
    ObjectiveRule("safe_search", "Contenido seguro", 2, _rule_safe_search),
]


def evaluate_objective_rules(cv: dict, kv_type: str) -> list[dict]:
    profile = get_profile(kv_type)
    out: list[dict] = []
    for rule in OBJECTIVE_RULES:
        if rule.applies_when and not rule.applies_when(profile):
            continue
        try:
            res = rule.fn(cv, profile)
        except Exception as e:
            res = RuleResult("partial", "—", f"Error al evaluar: {e}")
        out.append({
            "id": rule.id,
            "label": rule.label,
            "weight": rule.weight,
            "status": res.status,
            "value": res.value,
            "detail": res.detail,
        })
    return out


# ---------------------------------------------------------------------
# Reglas SUBJETIVAS (evaluadas por Gemini, score 1-5)
# ---------------------------------------------------------------------
@dataclass
class SubjectiveRule:
    id: str
    label: str
    weight: int
    prompt: str


SUBJECTIVE_RULES: list[SubjectiveRule] = [
    SubjectiveRule(
        "composition_clean", "Composición simple y limpia", 1,
        "¿La composición es simple y limpia? ¿Hay buen uso del espacio en blanco y los elementos respetan el área segura?"),
    SubjectiveRule(
        "youth_modern", "Concepto joven / moderno", 1,
        "¿La pieza transmite un concepto joven y moderno acorde a la marca Tigo?"),
    SubjectiveRule(
        "cta_clarity", "CTA claro y atractivo", 2,
        "¿El claim o CTA es claro, visible, está bien ubicado y respeta el área segura?"),
    SubjectiveRule(
        "copy_image_coherence", "Coherencia copy ↔ imagen", 2,
        "¿Hay coherencia visual y conceptual entre el copy y la fotografía? ¿La imagen genera contraste adecuado con el fondo y los colores de marca?"),
    SubjectiveRule(
        "visual_hierarchy", "Jerarquía visual", 1,
        "¿La jerarquía visual guía correctamente la mirada en este orden: logo → mensaje principal → oferta → CTA → legal?"),
    SubjectiveRule(
        "ai_photo_quality", "Calidad y mood fotográfico (Young & Cool)", 1,
        "Evaluá la fotografía contra el mood 'Young & Cool' de Tigo: (a) casting diverso y realista, no estéticas hegemónicas; "
        "(b) expresiones espontáneas, sin poses ni sonrisas plásticas; (c) ángulos atrevidos y estética cotidiana ('estar ahí'); "
        "(d) iluminación cálida y natural — penalizar luz blanca fría, brillante o estética de hospital/oficina; "
        "(e) postproducción sutil hacia paleta Tigo, sin falsear; texturas de piel reales — penalizar 'cera IA' o plástico. "
        "Detectar también artefactos típicos de IA generativa."),
    SubjectiveRule(
        "secondary_color_contrast", "Uso de colores secundarios para contraste", 1,
        "¿Los colores secundarios (magenta, naranja, verde, lima) se usan de forma puntual para generar contraste, "
        "especialmente en bloques de oferta? ¿O dominan incorrectamente la composición?"),
    SubjectiveRule(
        "logo_position_score", "Posición del logo (según manual)", 2,
        "Puntá la posición del logo Tigo en la pieza según manual de marca: "
        "5 = esquina INFERIOR DERECHA (recomendado, 100pts); "
        "4 = esquina SUPERIOR DERECHA (80pts); "
        "3 = esquinas IZQUIERDAS (70pts); "
        "2 = centrado o posición no estándar; "
        "1 = ausente o cortado/superpuesto. "
        "Describí en qué esquina/zona ves el logo (o cuál domina si hay varios) y ajustá el score en consecuencia."),
    SubjectiveRule(
        "logo_color_score", "Color del logo (según manual)", 2,
        "Puntá el tratamiento cromático del logo Tigo según manual: "
        "5 = blanco sobre azul puro Tigo (#001EB4) — 100pts; "
        "4 = azul Tigo sobre fondo claro — 80pts; "
        "3 = logo sobre fotografía o textura — 75pts; "
        "2 = colores fuera de manual (por ejemplo negro, gris, rojo, etc.); "
        "1 = logo ilegible por bajo contraste o mal tratamiento. "
        "Describí exactamente el color del logo y el fondo sobre el que aparece."),
    SubjectiveRule(
        "titular_uppercase", "Titular en MAYÚSCULAS", 1,
        "¿El titular (mensaje principal) está TODO EN MAYÚSCULAS como pide el manual? "
        "5 = todo en mayúsculas, tipografía DM Sans o similar geométrica sans-serif; "
        "4 = mayúsculas con alguna palabra puntual en otro estilo justificado; "
        "3 = mezcla mayúsculas/minúsculas; "
        "2 = mayormente minúsculas; "
        "1 = todo en minúsculas o tipografía script/serif fuera de manual. "
        "Considerá que en Tactico POP es requerido; en ATL/Social es sugerido."),
    SubjectiveRule(
        "ai_vs_stock", "Autenticidad de la foto (stock/real vs full IA)", 1,
        "Clasificá la fotografía: "
        "5 = foto real o de stock de alta calidad, texturas de piel naturales, iluminación creíble; "
        "4 = foto real con retoque IA leve (color grading, limpieza), aún convincente; "
        "3 = combinación foto + IA visible pero aceptable; "
        "2 = generación IA evidente (piel de cera, manos raras, ojos vacíos, fondo plástico); "
        "1 = full IA de baja calidad con artefactos claros (dedos extra, deformaciones, texturas irreales). "
        'Explicá qué señales de "cera IA" o autenticidad observás.'),
    SubjectiveRule(
        "typographic_hierarchy", "Jerarquía tipográfica (titular vs secundario vs copy)", 1,
        "Evaluá la jerarquía visual entre bloques de texto según el manual: "
        "el MENSAJE SECUNDARIO debe rondar el 60% del tamaño del titular; "
        "el COPY debe rondar el 30% del titular. "
        "5 = ratios muy cercanos a los ideales, jerarquía impecable; "
        "4 = jerarquía clara con desvíos menores; "
        "3 = jerarquía perceptible pero con ratios visiblemente fuera; "
        "2 = jerarquía confusa, tamaños compiten entre sí; "
        "1 = sin jerarquía tipográfica (todo del mismo peso o titular más chico que copy). "
        "Estimá los ratios y mencionalos en la evidencia."),
]

SUBJECTIVE_RULES_FLAG_CONDITIONAL: dict[str, SubjectiveRule] = {
    "tag_bu": SubjectiveRule(
        "tag_bu", "Tag de Unidad de Negocio (esquina superior derecha)", 2,
        "¿Hay un módulo/tag de Unidad de Negocio en la esquina superior derecha? "
        "Colores correctos por unidad: Prepago = módulo amarillo con texto blanco; "
        "Postpago = módulo celeste con texto azul; Hogar = módulo blanco con texto azul; "
        "Flex = módulo magenta con texto blanco. "
        "Penalizar ausencia, ubicación incorrecta o colores fuera de la especificación."),
    "marco_bu": SubjectiveRule(
        "marco_bu", "Marco de color BU (1/32 del ancho)", 1,
        "¿La pieza tiene un borde/marco de color de Unidad de Negocio de aproximadamente "
        "1/32 del ancho del formato, para despegarla de la contaminación visual del POP? "
        "Penalizar ausencia o grosor claramente distinto del especificado."),
    "foto_modulos": SubjectiveRule(
        "foto_modulos", "Fotografía en módulos (ícono de señal)", 2,
        "¿La composición fotográfica está dividida en 3 módulos que simulan el ícono "
        "de señal de Tigo, con un modelo humano en primer plano atravesándolos? "
        "Evaluar presencia de los 3 módulos, alineación y protagonismo del modelo."),
    "area_seg_ig": SubjectiveRule(
        "area_seg_ig", "Áreas seguras de Story (Instagram)", 1,
        "En formato 9:16 Story, las zonas superior e inferior son áreas seguras "
        "que pueden ser tapadas por UI de Instagram (avatar, sticker, botones). "
        "¿Los elementos clave (logo, oferta, CTA, mensaje) están fuera de esas zonas?"),
    "product_shot": SubjectiveRule(
        "product_shot", "Product shot (foto de producto para social)", 1,
        "En piezas de social media, ¿hay un product shot / bodegón que refuerce "
        "el mensaje sin competir con el modelo humano? Evaluar limpieza, "
        "iluminación y coherencia con el resto de la composición."),
}


def get_subjective_rules(profile: Profile) -> list[SubjectiveRule]:
    extras = [SUBJECTIVE_RULES_FLAG_CONDITIONAL[f]
              for f in profile.flags
              if f in SUBJECTIVE_RULES_FLAG_CONDITIONAL]
    return list(SUBJECTIVE_RULES) + extras
