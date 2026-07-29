from __future__ import annotations
import json
import re
from pathlib import Path
from functools import lru_cache

import httpx

from modules.config import GEMINI_API_KEY, LOGOS_DIR, REQUEST_TIMEOUT
from modules.utils import image_to_base64, guess_mime

LOGO_MIN_CONFIDENCE = 0.6
LOGO_MODEL = "gemini-2.5-flash"
LOGO_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{LOGO_MODEL}:generateContent"

LOGO_PROMPT = """Te muestro dos imágenes:
1. KV: una pieza publicitaria.
2. LOGO: un logo de marca de referencia.

Determina si el logo de la imagen 2 aparece visualmente dentro de la imagen 1.
Considera "presente" sólo si está claramente visible (puede estar redimensionado o levemente recortado, pero su diseño debe ser inequívocamente el mismo).
NO consideres "presente" si es un logo distinto de una marca similar, un texto que menciona la marca, o un parecido vago.

Si está presente, estima qué fracción del ANCHO del KV ocupa el logo (0.0 a 1.0). Por ejemplo, si el logo ocupa aproximadamente un cuarto del ancho del KV, devuelve 0.25.

Responde SOLO con JSON válido (sin markdown), con esta estructura:
{
  "present": true|false,
  "confidence": 0.0-1.0,
  "relative_width": 0.0-1.0,
  "location": "descripción breve de dónde aparece, o null si no aparece"
}"""


def _prettify_ref_name(name: str) -> str:
    s = re.sub(r"[-_]+", " ", name)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return "Logo"
    words = [w for w in s.split(" ") if w]
    def _is_hash(w: str) -> bool:
        return len(w) >= 6 and bool(re.search(r"[a-zA-Z]", w)) and bool(re.search(r"[0-9]", w))
    filtered = [w for w in words if not _is_hash(w)]
    if not filtered:
        filtered = words
    seen: dict[str, None] = {}
    for w in filtered:
        seen.setdefault(w.lower(), None)
    return " ".join(w.title() for w in seen.keys())


@lru_cache(maxsize=1)
def load_reference_logos() -> list[dict]:
    d = Path(LOGOS_DIR)
    if not d.exists():
        return []
    refs = []
    for f in sorted(d.iterdir()):
        if f.suffix.lower() in (".png", ".jpg", ".jpeg"):
            refs.append({
                "file": f.name,
                "name": _prettify_ref_name(f.stem),
                "path": str(f),
            })
    return refs


def build_logo_body(kv_path: str | Path, ref_path: str | Path) -> dict:
    return {
        "contents": [{
            "parts": [
                {"text": LOGO_PROMPT},
                {"text": "Imagen 1 (KV):"},
                {"inline_data": {"mime_type": guess_mime(kv_path), "data": image_to_base64(kv_path)}},
                {"text": "Imagen 2 (LOGO):"},
                {"inline_data": {"mime_type": guess_mime(ref_path), "data": image_to_base64(ref_path)}},
            ],
        }],
        "generationConfig": {
            "temperature": 0.1,
            "seed": 42,
            "responseMimeType": "application/json",
        },
    }


def _extract_text(raw: dict) -> str:
    try:
        return raw["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return ""


def parse_logo_response(status: int, raw: dict | None) -> dict:
    empty = {"present": False, "confidence": 0.0, "relative_width": None, "location": None}
    if status >= 400 or not raw:
        return empty
    txt = _extract_text(raw).strip()
    txt = re.sub(r"^```(json)?", "", txt).strip()
    txt = re.sub(r"```$", "", txt).strip()
    try:
        parsed = json.loads(txt)
    except Exception:
        return empty
    rw = parsed.get("relative_width")
    try:
        rw = float(rw) if rw is not None else None
        if rw is not None:
            rw = max(0.0, min(1.0, rw))
    except Exception:
        rw = None
    return {
        "present": bool(parsed.get("present")),
        "confidence": float(parsed.get("confidence") or 0),
        "relative_width": rw,
        "location": parsed.get("location"),
    }


def check_logo(kv_path: str | Path, ref: dict, client: httpx.Client) -> dict | None:
    """Returns a match dict if present with high enough confidence, else None."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY no está configurada en secrets.toml")
    body = build_logo_body(kv_path, ref["path"])
    r = client.post(
        LOGO_ENDPOINT,
        params={"key": GEMINI_API_KEY},
        json=body,
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    try:
        raw = r.json()
    except Exception:
        raw = None
    parsed = parse_logo_response(r.status_code, raw)
    if parsed["present"] and parsed["confidence"] >= LOGO_MIN_CONFIDENCE:
        return {
            "name": ref["name"],
            "confidence": parsed["confidence"],
            "relative_width": parsed["relative_width"],
            "location": parsed["location"],
        }
    return None
