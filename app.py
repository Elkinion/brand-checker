from __future__ import annotations
import base64
import tempfile
from pathlib import Path

import streamlit as st

from modules.auth import require_login, logout_button
from modules.config import KV_TYPES, missing_secrets
from modules.pipeline import analyze_images_parallel
from modules.brand_rules import BRAND_PALETTE

st.set_page_config(
    page_title="Brand Checker · Tigo",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------- Styles (mirrors R www/styles.css) ----------
_STYLES = """
<style>
/* Hide Streamlit's default chrome that overlaps content */
#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { display: none !important; height: 0 !important; }
div[data-testid="stToolbar"] { display: none !important; }
div[data-testid="stDecoration"] { display: none !important; }
footer { visibility: hidden; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }

.stApp { background-color: #f6f7fb; }
.block-container { padding-top: 0 !important; padding-bottom: 2rem;
                   max-width: 1400px; }

/* Brand header */
.bc-header { background:#001eb4; color:#fff; padding:14px 24px;
             display:grid; grid-template-columns:1fr auto 1fr;
             align-items:center; column-gap:14px;
             margin:-1rem -1rem 1.25rem -1rem; border-radius:0 0 12px 12px;
             box-shadow:0 2px 6px rgba(0,0,0,.08); }
.bc-header img { height:60px; width:auto; display:block; }
.bc-header .bc-header-left  { justify-self:start; }
.bc-header .bc-header-right { justify-self:end; }
.bc-header .bc-header-center { text-align:center; }
.bc-header .bc-header-title { font-size:1.35rem; font-weight:700;
                              letter-spacing:.02em; line-height:1; }
.bc-header .bc-header-sub   { font-size:.78rem; opacity:.85; margin-top:3px; }

.app-title { font-weight:700; font-size:1.6rem; margin:0 0 .25rem 0; color:#1a1a1a; }
.app-subtitle { color:#6b7280; margin-bottom:1.2rem; }

/* Card base */
.bc-card { background:#fff; border:1px solid #e6e8ee; border-radius:10px;
           padding:1rem 1.25rem; margin-bottom:.75rem;
           box-shadow:0 1px 2px rgba(0,0,0,.03); }
.bc-card h5 { margin:0 0 .5rem 0; font-weight:600; font-size:1rem; color:#1a1a1a; }
.bc-card h6 { margin:.5rem 0 .3rem 0; font-weight:600; font-size:.85rem; color:#374151; }
.bc-card .bc-detail { color:#4b5563; font-size:.9rem; margin:.4rem 0 0 0; }
.bc-card .bc-value  { font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
                      font-size:.85rem; color:#111827; }

/* Badges */
.bc-badge { display:inline-block; padding:.2rem .6rem; border-radius:999px;
            font-size:.72rem; font-weight:700; text-transform:uppercase;
            letter-spacing:.03em; }
.bc-badge.pass    { background:#d1fae5; color:#065f46; }
.bc-badge.fail    { background:#fee2e2; color:#991b1b; }
.bc-badge.partial { background:#fef3c7; color:#92400e; }
.bc-badge.bc-abcd-a { background:#fde68a; color:#78350f; }
.bc-badge.bc-abcd-b { background:#bfdbfe; color:#1e3a8a; }
.bc-badge.bc-abcd-c { background:#fbcfe8; color:#831843; }
.bc-badge.bc-abcd-d { background:#bbf7d0; color:#064e3b; }

/* Score */
.bc-score-wrap { text-align:center; padding:1.5rem;
                 background:linear-gradient(135deg,#00377B 0%, #1e5bb8 100%);
                 color:#fff; border-radius:12px; margin-bottom:1rem; }
.bc-score-number { font-size:3.5rem; font-weight:800; line-height:1; }
.bc-score-label  { font-size:.85rem; opacity:.9; margin-top:.4rem;
                   text-transform:uppercase; letter-spacing:.05em; }
.bc-score-sub    { display:flex; justify-content:center; gap:1.4rem;
                   margin-top:.6rem; font-size:.85rem; opacity:.92; }

/* Swatches */
.bc-swatch-row { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:.5rem; }
.bc-swatch     { display:flex; flex-direction:column; align-items:center;
                 text-align:center; width:64px; }
.bc-swatch-box { width:56px; height:56px; border-radius:8px;
                 border:1px solid rgba(0,0,0,.1); }
.bc-swatch-label { font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
                   font-size:.68rem; margin-top:.25rem; color:#4b5563; }
.bc-swatch-sub   { font-size:.62rem; color:#9ca3af; }

/* Stars */
.bc-stars { color:#F5A623; font-size:1.05rem; letter-spacing:2px; }
.bc-stars .empty { color:#e5e7eb; }

/* Multi preview grid */
.bc-multi-preview { display:grid;
                    grid-template-columns:repeat(auto-fill,minmax(160px,1fr));
                    gap:.5rem; margin-bottom:.5rem; }
.bc-preview-item  { display:flex; flex-direction:column; align-items:stretch;
                    background:#fff; border:1px solid #e5e7eb; border-radius:8px;
                    padding:.4rem; }
.bc-preview-item img { max-width:100%; max-height:110px; border-radius:4px;
                       object-fit:contain; align-self:center; }
.bc-preview-caption { font-size:.7rem; color:#4b5563; margin-top:.3rem;
                      text-align:center; overflow:hidden; text-overflow:ellipsis;
                      white-space:nowrap; max-width:100%; }

/* OCR */
.bc-ocr { background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px;
          padding:.75rem; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
          font-size:.8rem; white-space:pre-wrap; max-height:280px;
          overflow-y:auto; color:#374151; }

/* Section titles */
.bc-section-title { font-weight:600; font-size:1.05rem;
                    margin:1.25rem 0 .75rem 0; color:#1a1a1a;
                    border-bottom:2px solid #00377B; padding-bottom:.35rem; }

/* Preview big image (right column) */
.bc-preview-wrap { background:#fff; border:1px dashed #d1d5db; border-radius:10px;
                   padding:.5rem; text-align:center; }
.bc-preview-wrap img { max-width:100%; max-height:320px; border-radius:6px; }

/* Buttons full-width */
div[data-testid="stButton"] button { border-radius:8px; }
</style>
"""
st.markdown(_STYLES, unsafe_allow_html=True)


# ---------- Auth ----------
require_login()

missing = missing_secrets()
if missing:
    st.error(f"Faltan secrets: {', '.join(missing)}. Configuralos en `.streamlit/secrets.toml`.")
    st.stop()


# ---------- Session state ----------
def _init():
    st.session_state.setdefault("uploaded_files", [])
    st.session_state.setdefault("kv_types_by_name", {})
    st.session_state.setdefault("results", [])
    st.session_state.setdefault("status", "")
_init()


# ---------- Helpers ----------
def _file_to_data_uri(f) -> str:
    data = f.getvalue() if hasattr(f, "getvalue") else Path(f).read_bytes()
    ext = Path(getattr(f, "name", str(f))).suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _path_to_data_uri(path: str) -> str:
    p = Path(path)
    ext = p.suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def _badge(status: str) -> str:
    label = {"pass": "PASS", "fail": "FAIL", "partial": "PARTIAL"}.get(status, status.upper())
    return f'<span class="bc-badge {status}">{label}</span>'


def _stars(score) -> str:
    if score is None:
        return '<span class="bc-stars">—</span>'
    s = max(0, min(5, int(score)))
    return (f'<span class="bc-stars">{"★" * s}'
            f'<span class="empty">{"★" * (5 - s)}</span></span>')


def _palette_swatches_html() -> str:
    html = '<div class="bc-swatch-row">'
    for name, hex_ in BRAND_PALETTE.items():
        html += (f'<div class="bc-swatch">'
                 f'<div class="bc-swatch-box" style="background:{hex_}"></div>'
                 f'<div class="bc-swatch-label">{hex_}</div>'
                 f'<div class="bc-swatch-sub">{name}</div></div>')
    html += "</div>"
    return html


# ---------- Header ----------
_ICON_PATH = Path(__file__).parent / "static" / "header_icon.png"
_icon_tag_l = _icon_tag_r = ""
if _ICON_PATH.exists():
    _icon_b64 = base64.b64encode(_ICON_PATH.read_bytes()).decode()
    _icon_tag_l = f'<img src="data:image/png;base64,{_icon_b64}" alt="icon"/>'
    _icon_tag_r = _icon_tag_l
st.markdown(
    f'<div class="bc-header">'
    f'<div class="bc-header-left">{_icon_tag_l}</div>'
    f'<div class="bc-header-center">'
    f'<div class="bc-header-title">Brand Checker</div>'
    f'<div class="bc-header-sub">Tigo · Validación de piezas de marca</div>'
    f'</div>'
    f'<div class="bc-header-right">{_icon_tag_r}</div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ---------- Layout: 2 columnas (4/8 como en R) ----------
left, right = st.columns([4, 8], gap="large")


# ================== LEFT COLUMN ==================
with left:
    # Card: Subir piezas
    with st.container():
        st.markdown('<div class="bc-card">', unsafe_allow_html=True)
        st.markdown("##### Subir piezas")

        uploaded = st.file_uploader(
            "Subí imágenes (PNG/JPG) — hasta 500 MB c/u",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            label_visibility="visible",
        )
        if uploaded:
            st.session_state.uploaded_files = uploaded
        files = st.session_state.uploaded_files

        # Multi-preview grid
        if files:
            st.markdown('<div class="bc-multi-preview">', unsafe_allow_html=True)
            grid_html = ""
            for f in files:
                uri = _file_to_data_uri(f)
                grid_html += (
                    f'<div class="bc-preview-item">'
                    f'<img src="{uri}" alt="{f.name}"/>'
                    f'<div class="bc-preview-caption" title="{f.name}">{f.name}</div>'
                    f'</div>'
                )
            st.markdown(grid_html + "</div>", unsafe_allow_html=True)

            # Per-file type selectors (compact list)
            st.markdown('<div style="margin-top:.5rem;"></div>', unsafe_allow_html=True)
            kv_labels = list(KV_TYPES.keys())
            kv_values = list(KV_TYPES.values())
            for idx, f in enumerate(files):
                default_type = st.session_state.kv_types_by_name.get(f.name, "tactico_pop")
                try:
                    default_idx = kv_values.index(default_type)
                except ValueError:
                    default_idx = 0
                sel = st.selectbox(
                    f.name,
                    options=kv_labels,
                    index=default_idx,
                    key=f"kv_type_{f.name}_{idx}",
                )
                st.session_state.kv_types_by_name[f.name] = KV_TYPES[sel]

            # Bulk apply
            with st.expander("Aplicar el mismo tipo a todas"):
                bulk_sel = st.selectbox("Tipo", kv_labels, key="bulk_type_sel")
                if st.button("Aplicar a todas", width="stretch"):
                    for f in files:
                        st.session_state.kv_types_by_name[f.name] = KV_TYPES[bulk_sel]
                    st.rerun()

            # Analyze button
            analyze_clicked = st.button("Analizar", type="primary", width="stretch")
        else:
            st.info("Aún no hay archivos cargados.")
            analyze_clicked = False

        status_slot = st.empty()
        st.markdown('</div>', unsafe_allow_html=True)

    # Card: Paleta oficial
    st.markdown('<div class="bc-card">', unsafe_allow_html=True)
    st.markdown("##### Paleta oficial")
    st.markdown(_palette_swatches_html(), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Logout at the bottom of the left column
    with st.container():
        st.markdown('<div style="margin-top:.5rem;"></div>', unsafe_allow_html=True)
        if st.button("Cerrar sesión", width="stretch"):
            for k in ("auth_ok", "auth_attempts", "auth_locked_until"):
                st.session_state.pop(k, None)
            st.rerun()


# ---------- Trigger analysis ----------
if analyze_clicked and files:
    tmp_dir = Path(tempfile.mkdtemp(prefix="bc_"))
    paths: list[str] = []
    types: list[str] = []
    for f in files:
        p = tmp_dir / f.name
        with open(p, "wb") as w:
            w.write(f.getbuffer())
        paths.append(str(p))
        types.append(st.session_state.kv_types_by_name.get(f.name, "tactico_pop"))

    def cb(msg: str) -> None:
        status_slot.info(msg)

    try:
        with st.spinner("Analizando en paralelo…"):
            results = analyze_images_parallel(paths, types, progress_cb=cb,
                                              max_parallel_images=4)
        st.session_state.results = results
        status_slot.empty()
    except Exception as e:
        status_slot.error(f"Error en el análisis: {e}")


# ================== RIGHT COLUMN ==================
def _render_score_card(result: dict) -> None:
    sc = result.get("score") or {}
    total_pct = (sc.get("total_pct", 0) or 0) * 100
    obj_pct = (sc.get("obj_pct", 0) or 0) * 100
    subj_pct = (sc.get("subj_pct", 0) or 0) * 100
    st.markdown(
        f'<div class="bc-score-wrap">'
        f'<div class="bc-score-number">{total_pct:.0f}%</div>'
        f'<div class="bc-score-label">Score total</div>'
        f'<div class="bc-score-sub">'
        f'<span>Objetivo: <b>{obj_pct:.0f}%</b></span>'
        f'<span>Subjetivo: <b>{subj_pct:.0f}%</b></span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _render_objective(result: dict) -> None:
    rows = result.get("obj_results") or []
    if not rows:
        st.info("Sin criterios objetivos evaluados.")
        return
    html = ""
    for r in rows:
        html += (
            f'<div class="bc-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem;">'
            f'<h5>{r["label"]}</h5>{_badge(r["status"])}</div>'
            f'<p class="bc-detail"><span class="bc-value">{r.get("value","")}</span> — {r.get("detail","")}</p>'
            f'</div>'
        )
    st.markdown(html, unsafe_allow_html=True)


def _render_subjective(result: dict) -> None:
    subj = result.get("subj_data") or {}
    overall = subj.get("overall_impression") or ""
    rows = subj.get("results") or []
    html = ""
    if overall:
        html += (f'<div class="bc-card"><h5>Impresión general (Gemini)</h5>'
                 f'<p class="bc-detail">{overall}</p></div>')
    for r in rows:
        score = r.get("score")
        score_txt = f"{score}/5" if score is not None else "—"
        html += (
            f'<div class="bc-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem;">'
            f'<h5>{r["label"]}</h5>'
            f'<span>{_stars(score)} <span style="color:#6b7280;font-size:.75rem;">{score_txt}</span></span>'
            f'</div>'
            f'<p class="bc-detail">{r.get("observation","")}</p>'
            f'</div>'
        )
    if not html:
        st.info("Sin criterios subjetivos evaluados.")
        return
    st.markdown(html, unsafe_allow_html=True)


def _render_colors(result: dict) -> None:
    cv = result.get("cv") or {}
    colors = cv.get("dominant_colors") or []
    if not colors:
        st.info("No se detectaron colores dominantes.")
        return
    html = '<div class="bc-card"><h5>Colores: detectados vs oficiales</h5>'
    html += '<h6>Colores dominantes detectados</h6><div class="bc-swatch-row">'
    for c in colors:
        pct = (c.get("pixel_fraction") or 0) * 100
        near = c.get("nearest_palette") or "fuera de paleta"
        matched = (c.get("nearest_distance") or 999) < 40
        sub = f"{pct:.0f}% · " + (f"≈ {near}" if matched else "fuera de paleta")
        html += (f'<div class="bc-swatch">'
                 f'<div class="bc-swatch-box" style="background:{c["hex"]}"></div>'
                 f'<div class="bc-swatch-label">{c["hex"]}</div>'
                 f'<div class="bc-swatch-sub">{sub}</div></div>')
    html += "</div>"
    html += '<h6 style="margin-top:1rem;">Paleta oficial</h6>'
    html += _palette_swatches_html()
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def _render_ocr(result: dict) -> None:
    cv = result.get("cv") or {}
    text = (cv.get("full_text") or "").strip()
    if not text:
        st.info("No se detectó texto por OCR.")
        return
    st.markdown(f'<div class="bc-ocr">{text}</div>', unsafe_allow_html=True)


def _render_result(result: dict) -> None:
    if result.get("error"):
        st.markdown(
            f'<div class="bc-card"><h5>Error analizando {result.get("name","")}</h5>'
            f'<p class="bc-detail">{result["error"]}</p></div>',
            unsafe_allow_html=True,
        )
        return

    # Preview + score card at the top
    uri = _path_to_data_uri(result["path"])
    st.markdown(
        f'<div class="bc-preview-wrap"><img src="{uri}" alt="{result["name"]}"/></div>',
        unsafe_allow_html=True,
    )
    _render_score_card(result)

    tabs = st.tabs(["Objetivo", "Subjetivo", "Colores", "Texto (OCR)"])
    with tabs[0]:
        _render_objective(result)
    with tabs[1]:
        _render_subjective(result)
    with tabs[2]:
        _render_colors(result)
    with tabs[3]:
        _render_ocr(result)


with right:
    results = st.session_state.results
    if not results:
        st.markdown('<div class="bc-section-title">Resultados</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="bc-card"><p class="bc-detail">'
            'Los resultados aparecerán aquí después de analizar las piezas.'
            '</p></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="bc-section-title">Resultados</div>', unsafe_allow_html=True)
        if len(results) == 1:
            _render_result(results[0])
        else:
            titles = [r.get("name", f"Pieza {i+1}") for i, r in enumerate(results)]
            result_tabs = st.tabs(titles)
            for tab, r in zip(result_tabs, results):
                with tab:
                    _render_result(r)
