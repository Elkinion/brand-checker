from __future__ import annotations
from typing import Any

STATUS_VALUE = {"pass": 1.0, "partial": 0.5, "fail": 0.0}

# Peso relativo image-score: 50% objetivo, 50% subjetivo.
OBJ_WEIGHT = 0.5
SUBJ_WEIGHT = 0.5

# Consejos cortos por regla. Deben caber en 1-2 líneas.
ADVICE: dict[str, str] = {
    # --- Objetivas ---
    "logo_detected": "Asegurate de que el logo Tigo esté presente y nítido; si usás variantes, dejá el master en static/logos.",
    "logo_max_width": "Achicá el logo: no debe superar 1/3 del ancho del KV.",
    "brand_colors_usage": "Reforzá 2+ primarios (azul, celeste, amarillo, blanco) y limitá secundarios a 1 uso puntual.",
    "color_palette": "Ajustá los colores dominantes hacia la paleta oficial; evitá matices fuera de manual.",
    "disclaimer": "Sumá el disclaimer legal (\"Términos y condiciones aplican\") en máx 60 caracteres / 2 líneas.",
    "text_simplicity": "Recortá el titular a ≤10 palabras/3 líneas y el secundario a ≤5 palabras.",
    "photo_area": "Regulá el área de la fotografía al rango del perfil (subí o achicá según indique el detalle).",
    "offer_area": "Ajustá el bloque de oferta al ~35% del área del KV.",
    "propuesta_valor_area": "Achicá la propuesta de valor: no debe superar el % máximo del perfil.",
    "gama_coherence": "En impresos evitá magenta como color proporcional (dejalo solo para tag Flex puntual).",
    "safe_search": "Revisá que la imagen no incluya elementos flagged como riesgosos (violencia, adulto, etc.).",

    # --- Subjetivas ---
    "composition_clean": "Simplificá la composición y respetá el área segura; más aire, menos elementos.",
    "youth_modern": "Actualizá el mood: casting joven, ángulos frescos, evitá estéticas corporativas antiguas.",
    "cta_clarity": "Hacé el CTA más visible: contraste alto, jerarquía mayor, fuera del área saturada.",
    "copy_image_coherence": "Alineá conceptualmente copy y foto; buscá contraste del texto contra el fondo.",
    "visual_hierarchy": "Reordená la jerarquía: logo → mensaje principal → oferta → CTA → legal.",
    "ai_photo_quality": "Buscá iluminación cálida y natural, casting diverso y expresiones espontáneas.",
    "secondary_color_contrast": "Usá los secundarios (magenta, naranja, verde) solo como acento, no como color dominante.",
    "logo_position_score": "Mové el logo a la esquina INFERIOR DERECHA (posición recomendada por el manual).",
    "logo_color_score": "Usá logo blanco sobre azul #001EB4, o azul Tigo sobre fondo claro.",
    "titular_uppercase": "Pasá el titular a MAYÚSCULAS en tipografía DM Sans (o sans-serif geométrica).",
    "ai_vs_stock": "Reemplazá fotos IA de baja calidad por foto real o stock; cuidá texturas de piel.",
    "typographic_hierarchy": "Ajustá tamaños: secundario ≈60% del titular, copy ≈30% del titular.",

    # --- Condicionales por flag ---
    "tag_bu": "Agregá el tag de Unidad de Negocio en la esquina superior derecha con los colores correctos.",
    "marco_bu": "Sumá un marco de color BU de ~1/32 del ancho del formato.",
    "foto_modulos": "Dividí la foto en 3 módulos tipo ícono de señal Tigo, con un modelo en primer plano.",
    "area_seg_ig": "Reubicá logo, oferta y CTA fuera de las áreas seguras superior/inferior de Story.",
    "product_shot": "Agregá un product shot limpio que refuerce sin competir con el modelo.",
}

DEFAULT_ADVICE = "Revisá este ítem contra el manual de marca y ajustá para acercarlo al ideal."


def _obj_total_weight(obj_results: list[dict]) -> float:
    return float(sum((r.get("weight") or 1) for r in (obj_results or []))) or 1.0


def _subj_total_weight(subj_rows: list[dict]) -> float:
    # Solo cuentan las reglas con score.
    return float(sum((r.get("weight") or 1) for r in (subj_rows or [])
                     if r.get("score") is not None)) or 1.0


def compute_improvements(result: dict) -> list[dict]:
    """
    Devuelve una lista de mejoras ordenada por ganancia potencial (puntos
    porcentuales sobre el score total). Solo incluye reglas que NO están
    en el máximo (pass u obj weight=full, o score=5 en subj).
    """
    if not result or result.get("error"):
        return []

    obj_results = result.get("obj_results") or []
    subj = result.get("subj_data") or {}
    subj_rows = subj.get("results") or []

    obj_w_total = _obj_total_weight(obj_results)
    subj_w_total = _subj_total_weight(subj_rows)

    items: list[dict] = []

    for r in obj_results:
        status = r.get("status", "fail")
        cur = STATUS_VALUE.get(status, 0.0)
        if cur >= 1.0:
            continue
        w = float(r.get("weight") or 1)
        # Ganancia en puntos porcentuales del total (0-100).
        gain_pp = OBJ_WEIGHT * ((1.0 - cur) * w / obj_w_total) * 100.0
        items.append({
            "id": r.get("id", ""),
            "label": r.get("label", ""),
            "kind": "obj",
            "current": status.upper(),
            "gain_pp": gain_pp,
            "detail": r.get("detail", ""),
            "advice": ADVICE.get(r.get("id", ""), DEFAULT_ADVICE),
        })

    for r in subj_rows:
        score = r.get("score")
        if score is None:
            continue
        try:
            s = float(score)
        except Exception:
            continue
        if s >= 5.0:
            continue
        w = float(r.get("weight") or 1)
        frac = s / 5.0
        gain_pp = SUBJ_WEIGHT * ((1.0 - frac) * w / subj_w_total) * 100.0
        items.append({
            "id": r.get("id", ""),
            "label": r.get("label", ""),
            "kind": "subj",
            "current": f"{int(s)}/5",
            "gain_pp": gain_pp,
            "detail": r.get("observation", ""),
            "advice": ADVICE.get(r.get("id", ""), DEFAULT_ADVICE),
        })

    items.sort(key=lambda x: x["gain_pp"], reverse=True)
    return items
