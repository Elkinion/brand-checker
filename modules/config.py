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
    "Táctico POP": "tactico_pop",
    "KV con Fotografía": "kv_fotografia",
    "ATL Full Fotográfico": "atl_full_foto",
    "ATL Background Color": "atl_background_color",
    "Social Media — Post (1:1)": "social_post",
    "Social Media — Story (9:16)": "social_story",
    "Social Media — Feed (horiz.)": "social_feed",
    "Afiche Fotográfico Tienda": "afiche_foto_tienda",
    "Afiche Tienda": "afiche_tienda",
    "Afiche Promo Tienda": "afiche_promo_tienda",
    "OOH / Valla exterior": "ooh_valla",
    "Foto de la calle (extraer valla)": "street",
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
