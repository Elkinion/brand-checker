from __future__ import annotations
import json
import re
from pathlib import Path

import httpx

from modules.config import GEMINI_API_KEY, REQUEST_TIMEOUT
from modules.utils import image_to_base64, guess_mime
from modules.brand_rules import (
    Profile, get_profile, get_subjective_rules,
)

GEMINI_MODEL = "gemini-2.5-pro"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

GEMINI_SUBJECTIVE_CONFIG = {
    "temperature": 0.1,
    "seed": 42,
    "responseMimeType": "application/json",
}


def _piece_context_block(profile: Profile) -> str:
    parts = [f"Tipo de pieza: {profile.label}."]
    gama_map = {
        "impresos":  "Impresos (SIN magenta como color proporcional; sólo puntual — ej. tag Flex)",
        "digitales": "Digitales (magenta permitido como acento)",
    }
    parts.append(f"Gama cromática esperada: {gama_map.get(profile.gama, 'Ambos (impresos + digitales)')}.")
    if profile.foto:
        parts.append(f"Fotografía esperada: {profile.foto.min*100:.0f}–{profile.foto.max*100:.0f}% del KV.")
    if profile.oferta_target is not None:
        modulos = profile.oferta_modulos_max or 3
        parts.append(f"Bloque de oferta: ~{profile.oferta_target*100:.0f}% del KV, máximo {modulos} módulo(s).")
    if profile.propuesta_max is not None:
        parts.append(f"Propuesta de valor: hasta {profile.propuesta_max*100:.0f}% del KV.")
    if profile.titular:
        parts.append(f"Titular: máx {profile.titular.words} palabras / {profile.titular.lines} líneas.")
    if profile.secundario:
        parts.append(f"Mensaje secundario: máx {profile.secundario.words} palabras / {profile.secundario.lines} líneas.")
    if profile.legal:
        parts.append(f"Legal: máx {profile.legal.chars} caracteres, {profile.legal.lines} línea(s).")
    if profile.varia_tipografia:
        parts.append("Se permite variación tipográfica en jerarquías.")
    return "\n- ".join(parts)


def _photo_mood_block() -> str:
    return (
        'MOOD FOTOGRÁFICO "YOUNG & COOL" (aplica a toda pieza con foto):\n'
        "- Casting inclusivo: rostros diversos, reales y cercanos. Evitar estéticas hegemónicas o inalcanzables.\n"
        "- Expresión: cero poses; momentos espontáneos; emociones genuinas. Penalizar sonrisas plásticas o rostros indiferentes.\n"
        '- Ángulos: perspectivas atrevidas, estética cotidiana ("estar ahí").\n'
        "- Iluminación: cálida y natural. Prohibido: luz blanca fría, súper brillante, estética de hospital/oficina.\n"
        '- Postproducción: color sutil hacia paleta Tigo, sin falsear la realidad. Texturas de piel reales — penalizar "cera IA" o plásticos.'
    )


def build_prompt(cv: dict, kv_type: str = "tactico_pop") -> str:
    profile = get_profile(kv_type)
    rules = get_subjective_rules(profile)

    logos = cv.get("logos") or []
    logos_str = ", ".join(
        f"{l.get('description')} (score {(l.get('score') or 0):.2f})" for l in logos
    ) if logos else "ninguno"

    colors = cv.get("dominant_colors") or []
    colors_str = ", ".join(
        f"{c['hex']} ({(c.get('pixel_fraction') or 0)*100:.0f}%)" for c in colors
    ) if colors else "no detectados"

    ocr_preview = (cv.get("full_text") or "")[:500]
    text_blocks_count = cv.get("text_blocks_count") or 0

    criteria_str = "\n".join(
        f'- id: "{r.id}" | {r.label} — {r.prompt}' for r in rules
    )

    piece_block = _piece_context_block(profile)
    mood_block = _photo_mood_block()

    return (
        "Eres un experto en brand compliance publicitario para Tigo. "
        "Recibes una pieza gráfica junto con datos objetivos ya extraídos por computer vision. "
        "Evalúa SOLO los criterios subjetivos. No repitas lo que ya dicen los datos objetivos.\n\n"
        "== CONTEXTO DE LA PIEZA ==\n"
        f"- {piece_block}\n\n"
        f"{mood_block}\n\n"
        "== DATOS OBJETIVOS (referencia, NO los re-evalúes) ==\n"
        f"- Logos detectados: {logos_str}\n"
        f"- Colores dominantes: {colors_str}\n"
        f"- Bloques de texto detectados: {text_blocks_count}\n"
        f'- Texto OCR (extracto): "{ocr_preview}"\n\n'
        "== CRITERIOS SUBJETIVOS A EVALUAR ==\n"
        f"{criteria_str}\n\n"
        "== ESTIMACIÓN DE ÁREAS (adicional, aparte de los criterios) ==\n"
        "Estimá visualmente qué fracción del ÁREA TOTAL DE LA PIEZA ocupa cada bloque:\n"
        "- photo_area_pct: fracción ocupada por la FOTOGRAFÍA principal (0.0–1.0). null si no hay foto.\n"
        "- offer_area_pct: fracción del BLOQUE DE OFERTA (precio, %, número grande destacado con caja/módulo de color) (0.0–1.0). null si no hay oferta explícita.\n"
        "- propuesta_area_pct: fracción de la PROPUESTA DE VALOR (bloque de beneficios/tag secundario) (0.0–1.0). null si no la hay.\n"
        "Sé estricto con las estimaciones — mirá la pieza como si dividieras un rectángulo.\n\n"
        "REGLAS DE EVALUACIÓN (importantes):\n"
        "- Razona en orden: primero observa, luego justifica, finalmente asigna el score.\n"
        '- "evidence" debe describir SOLO lo que ves en la imagen, sin interpretar.\n'
        '- "score_justification" debe argumentar el score a partir de la evidencia y del contexto de la pieza.\n'
        "- No infieras datos que no estén en la imagen.\n\n"
        "ESCALA DE SCORING (estricta — usá la escala completa, NO infles):\n"
        "- 5: Excepcional. Estándar de agencia top, sin defectos visibles. Reservalo para casos verdaderamente sobresalientes (≤10% de los casos).\n"
        "- 4: Bueno. Cumple sólidamente con uno o dos detalles menores mejorables.\n"
        "- 3: Aceptable con peros. Cumple lo mínimo del criterio pero hay deficiencias claras.\n"
        "- 2: Por debajo del estándar. Falla en aspectos importantes del criterio.\n"
        "- 1: No cumple. Ausencia, error grave o contradicción directa del criterio.\n\n"
        "CRITERIO DE ESTRICTEZ:\n"
        "- Si dudás entre dos scores, elegí el MÁS BAJO.\n"
        "- No premies la intención: evaluá el resultado ejecutado.\n"
        '- "Se ve correcto pero nada destacable" = 3, no 4.\n'
        '- "Cumple pero con detalles que un director de arte rechazaría" = 2, no 3.\n'
        "- No uses 4 ni 5 a menos que puedas nombrar específicamente qué lo eleva sobre lo aceptable.\n\n"
        "Responde SOLO con JSON válido (sin markdown, sin ```), con esta estructura exacta:\n"
        "{\n"
        '  "subjective_results": [\n'
        "    {\n"
        '      "id": "criterio_id",\n'
        '      "evidence": "qué ves en la imagen, sin opinión",\n'
        '      "score_justification": "por qué ese score, a partir de la evidencia",\n'
        '      "score": 1-5\n'
        "    }\n"
        "  ],\n"
        '  "area_estimates": {\n'
        '    "photo_area_pct": 0.0,\n'
        '    "offer_area_pct": 0.0,\n'
        '    "propuesta_area_pct": 0.0\n'
        "  },\n"
        '  "overall_impression": "resumen de 2 líneas sobre la pieza"\n'
        "}"
    )


def build_body(image_path: str | Path, prompt_text: str) -> dict:
    return {
        "contents": [{
            "parts": [
                {"text": prompt_text},
                {"inline_data": {
                    "mime_type": guess_mime(image_path),
                    "data": image_to_base64(image_path),
                }},
            ],
        }],
        "generationConfig": GEMINI_SUBJECTIVE_CONFIG,
    }


def _extract_json(raw: dict) -> dict:
    try:
        txt = raw["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise RuntimeError("Gemini devolvió una respuesta vacía.")
    if not txt:
        raise RuntimeError("Gemini devolvió una respuesta vacía.")
    txt = re.sub(r"^```(json)?", "", txt.strip()).strip()
    txt = re.sub(r"```$", "", txt).strip()
    return json.loads(txt)


def _compose_observation(m: dict) -> str:
    obs = m.get("observation")
    if obs:
        return str(obs)
    ev = str(m.get("evidence") or "")
    jt = str(m.get("score_justification") or "")
    if ev and jt:
        return f"Evidencia: {ev} · Juicio: {jt}"
    return jt or ev or ""


def _enrich(parsed: dict, kv_type: str) -> dict:
    profile = get_profile(kv_type)
    rules = get_subjective_rules(profile)
    subj_results = parsed.get("subjective_results") or []
    by_id = {r.get("id"): r for r in subj_results if r.get("id")}
    enriched: list[dict] = []
    for rule in rules:
        m = by_id.get(rule.id)
        if m is not None:
            try:
                score = int(m.get("score"))
            except Exception:
                score = None
            enriched.append({
                "id": rule.id,
                "label": rule.label,
                "weight": rule.weight,
                "score": score,
                "observation": _compose_observation(m),
            })
        else:
            enriched.append({
                "id": rule.id,
                "label": rule.label,
                "weight": rule.weight,
                "score": None,
                "observation": "Sin respuesta de Gemini para este criterio.",
            })
    areas = parsed.get("area_estimates") or {}
    def _f(x):
        try:
            return float(x) if x is not None else None
        except (TypeError, ValueError):
            return None
    return {
        "results": enriched,
        "overall_impression": parsed.get("overall_impression") or "",
        "area_estimates": {
            "photo_area_pct": _f(areas.get("photo_area_pct")),
            "offer_area_pct": _f(areas.get("offer_area_pct")),
            "propuesta_area_pct": _f(areas.get("propuesta_area_pct")),
        },
    }


def analyze_subjective(image_path: str | Path, cv: dict, kv_type: str,
                       client: httpx.Client | None = None) -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY no está configurada en secrets.toml")
    prompt = build_prompt(cv, kv_type)
    body = build_body(image_path, prompt)
    close = False
    if client is None:
        client = httpx.Client(timeout=REQUEST_TIMEOUT)
        close = True
    try:
        r = client.post(
            GEMINI_ENDPOINT,
            params={"key": GEMINI_API_KEY},
            json=body,
            headers={"Content-Type": "application/json"},
        )
    finally:
        if close:
            client.close()
    if r.status_code >= 400:
        try:
            msg = r.json().get("error", {}).get("message", r.reason_phrase)
        except Exception:
            msg = r.text[:300]
        raise RuntimeError(f"Gemini API error ({r.status_code}): {msg}")
    parsed = _extract_json(r.json())
    return _enrich(parsed, kv_type)
