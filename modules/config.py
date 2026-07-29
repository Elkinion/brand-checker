from __future__ import annotations
import os
import streamlit as st

def _get(key: str, default: str | None = None) -> str | None:
    try:
        val = st.secrets.get(key)  # type: ignore[attr-defined]
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(key, default)

GCV_API_KEY = _get("GCV_API_KEY", "")
GEMINI_API_KEY = _get("GEMINI_API_KEY", "")
GCP_PROJECT_ID = _get("GCP_PROJECT_ID", "")
GCP_PROJECT_NUMBER = _get("GCP_PROJECT_NUMBER", "")
APP_PASSWORD_HASH = _get("APP_PASSWORD_HASH", "")

LOGOS_DIR = "static/logos"
REQUEST_TIMEOUT = 120

KV_TYPES: dict[str, str] = {
    "Social — Post (1:1)": "social_post",
    "Social — Story (9:16)": "social_story",
    "Social — Feed (horiz.)": "social_feed",
    "OOH / Valla exterior": "ooh_valla",
    "KV con Fotografía": "kv_fotografia",
    "Afiche Tienda": "afiche_tienda",
    "Afiche Promo Tienda": "afiche_promo_tienda",
    "ATL": "atl_full_foto",
    "Táctico POP": "tactico_pop",
}

# Compatibilidad ratio -> qué kv_types son plausibles.
# Categorías: ultrawide (>=2.5), landscape (1.4-2.5), square (0.85-1.4),
#             portrait_std (0.65-0.85), portrait_tall (<0.65).
KV_TYPE_RATIOS: dict[str, set[str]] = {
    "social_post":         {"square"},
    "social_story":        {"portrait_tall"},
    "social_feed":         {"landscape"},
    "ooh_valla":           {"ultrawide", "landscape"},
    "kv_fotografia":       {"square", "portrait_std", "landscape"},
    "afiche_tienda":       {"square", "portrait_std", "portrait_tall"},
    "afiche_promo_tienda": {"square", "portrait_std", "portrait_tall"},
    "atl_full_foto":       {"landscape", "ultrawide", "square", "portrait_std"},
    "tactico_pop":         {"square", "portrait_std", "portrait_tall"},
}

def missing_secrets() -> list[str]:
    missing = []
    if not GCV_API_KEY:
        missing.append("GCV_API_KEY")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not APP_PASSWORD_HASH:
        missing.append("APP_PASSWORD_HASH")
    return missing
