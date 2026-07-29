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

AUTO_KV_TYPE = "auto"

KV_TYPES: dict[str, str] = {
    "Auto (detectar por ratio)": AUTO_KV_TYPE,
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

def missing_secrets() -> list[str]:
    missing = []
    if not GCV_API_KEY:
        missing.append("GCV_API_KEY")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not APP_PASSWORD_HASH:
        missing.append("APP_PASSWORD_HASH")
    return missing
