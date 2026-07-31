from __future__ import annotations
import base64
import tempfile
from pathlib import Path

import streamlit as st

from modules.auth import require_login, logout_button
from modules.config import KV_TYPES, KV_TYPE_RATIOS, missing_secrets
from modules.pipeline import analyze_images_parallel
from modules.brand_rules import BRAND_PALETTE
from modules.improvements import compute_improvements
from modules.pdf_report import build_pdf
from modules.utils import ratio_category

_FAVICON_PATH = Path(__file__).parent / "static" / "favicon_r54.png"
_PAGE_ICON = str(_FAVICON_PATH) if _FAVICON_PATH.exists() else "🎯"

st.set_page_config(
    page_title="Brand Checker · Tigo",
    page_icon=_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------- Styles (Tigo Design System v2.0 tokens) ----------
_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700;9..40,800;9..40,900&display=swap');
/* ---------- Design tokens (from Tigo DS v2.0) ---------- */
:root {
  --blue-900:#00005A; --blue-500:#001EB4; --blue-400:#0026E5; --blue-50:#E6F1FF;
  --cyan:#44C8F5;
  --green:#00F52D; --yellow:#FFBE00; --magenta:#FF0064; --orange:#FB561E;
  --gray-100:#F5F5F5; --gray-200:#EBEBEB; --gray-300:#D1D1D1;
  --gray-400:#888;    --gray-500:#9E9E9E; --gray-600:#767676;
  --err:#C62828; --ok:#1A7F3C; --bg-err:#FFEBEE; --bg-ok:#E8F5E9;
  --font:'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --r-input:16px; --r-card:20px; --r-pill:9999px;
  --focus:0 0 0 3px rgba(68,200,245,.4);
  --sh-sm:0 1px 4px rgba(0,0,0,.08);
  --sh-md:0 4px 16px rgba(0,0,0,.10);
}

/* Hide Streamlit chrome */
#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { display: none !important; height: 0 !important; }
div[data-testid="stToolbar"] { display: none !important; }
div[data-testid="stDecoration"] { display: none !important; }
footer { visibility: hidden; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }

html, body, [class*="css"], .stApp, .stMarkdown, .stButton, .stSelectbox,
.stTextInput, .stFileUploader, .stTabs, .stExpander,
.stAlert, .stSpinner, div[data-testid="stAppViewContainer"] {
  font-family: var(--font) !important;
}
.stApp { background: #F4F6FA; color: var(--blue-900); }
.block-container { padding-top: 0 !important; padding-bottom: 2rem;
                   max-width: 1400px; }

/* ---------- Header ---------- */
.bc-header { background: var(--blue-500); color:#fff; padding:16px 26px;
             display:grid; grid-template-columns:1fr auto 1fr;
             align-items:center; column-gap:14px;
             margin:-1rem -1rem 1.5rem -1rem;
             border-radius:0 0 var(--r-card) var(--r-card);
             box-shadow: var(--sh-sm); }
.bc-header img { height:60px; width:auto; display:block; }
.bc-header .bc-header-left  { justify-self:start; }
.bc-header .bc-header-right { justify-self:end; }
.bc-header .bc-header-center { text-align:center; }
.bc-header .bc-header-title { font-size:1.45rem; font-weight:800;
                              letter-spacing:-.02em; line-height:1; }
.bc-header .bc-header-sub   { font-size:.72rem; opacity:.72; margin-top:5px;
                              text-transform:uppercase; letter-spacing:1.5px;
                              font-weight:600; color: var(--cyan); }

/* ---------- Card base ---------- */
.bc-card { background:#fff; border:1px solid #E4E8F0;
           border-radius: var(--r-card);
           padding:18px 20px; margin-bottom:12px;
           box-shadow: var(--sh-sm); }
.bc-card h5 { margin:0 0 .5rem 0; font-weight:800; font-size:14.5px;
              color: var(--blue-900); letter-spacing:-.01em; }
.bc-card h6 { margin:.5rem 0 .3rem 0; font-weight:700; font-size:12px;
              color: var(--blue-500); text-transform:uppercase;
              letter-spacing:1px; }
.bc-card .bc-detail { color: var(--gray-600); font-size:13.5px;
                      margin:.4rem 0 0 0; line-height:1.55; }
.bc-card .bc-value  { font-family:'Menlo','Monaco',monospace;
                      font-size:12.5px; color: var(--blue-500); font-weight:700; }

/* ---------- Badges ---------- */
.bc-badge { display:inline-flex; align-items:center; padding:3px 10px;
            border-radius: var(--r-pill); font-size:10px; font-weight:800;
            text-transform:uppercase; letter-spacing:1px; }
.bc-badge.pass    { background: var(--bg-ok);  color:#155724; }
.bc-badge.fail    { background: var(--bg-err); color: var(--err); }
.bc-badge.partial { background:#FFF8E1;        color:#8a6900; }

/* ---------- Score pill ---------- */
.bc-score-pill { display:flex; align-items:center; justify-content:space-between;
                 gap:1rem; padding:10px 16px;
                 background: linear-gradient(135deg, var(--blue-900) 0%, var(--blue-500) 100%);
                 color:#fff; border-radius: var(--r-card);
                 margin-bottom:12px; box-shadow: var(--sh-sm); }
.bc-score-pill .bc-score-main { display:flex; align-items:baseline; gap:.5rem; }
.bc-score-pill .bc-score-number { font-size:1.8rem; font-weight:900;
                                  line-height:1; letter-spacing:-.02em; }
.bc-score-pill .bc-score-label  { font-size:10px; opacity:.72;
                                  text-transform:uppercase; letter-spacing:2px;
                                  font-weight:700; color: var(--cyan); }
.bc-score-pill .bc-score-sub    { display:flex; gap:1rem; font-size:12.5px;
                                  opacity:.92; }
.bc-score-pill .bc-score-sub b  { font-weight:800; color:#fff; }

/* ---------- Swatches ---------- */
.bc-swatch-row { display:flex; flex-wrap:wrap; gap:.6rem; margin-top:.6rem; }
.bc-swatch     { display:flex; flex-direction:column; align-items:center;
                 text-align:center; width:68px; }
.bc-swatch-box { width:60px; height:60px; border-radius:12px;
                 border:1px solid rgba(0,0,0,.06); }
.bc-swatch-label { font-family:'Menlo','Monaco',monospace; font-size:10px;
                   margin-top:.35rem; color: var(--blue-500); font-weight:700; }
.bc-swatch-sub   { font-size:10px; color: var(--gray-500); }

/* ---------- Stars ---------- */
.bc-stars { color: var(--yellow); font-size:1.05rem; letter-spacing:2px; }
.bc-stars .empty { color: var(--gray-200); }

/* ---------- Multi preview grid ---------- */
.bc-multi-preview { display:grid;
                    grid-template-columns:repeat(auto-fill,minmax(160px,1fr));
                    gap:8px; margin-bottom:.5rem; }
.bc-preview-item  { display:flex; flex-direction:column; align-items:stretch;
                    background:#fff; border:1px solid #E4E8F0;
                    border-radius: 14px; padding:8px; }
.bc-preview-item img { max-width:100%; max-height:110px; border-radius:8px;
                       object-fit:contain; align-self:center; }
.bc-preview-caption { font-size:11px; color: var(--gray-600); margin-top:5px;
                      text-align:center; overflow:hidden; text-overflow:ellipsis;
                      white-space:nowrap; max-width:100%; }

/* ---------- OCR ---------- */
.bc-ocr { background: var(--gray-100); border:1px solid #E4E8F0;
          border-radius: 14px; padding:12px 14px;
          font-family:'Menlo','Monaco',monospace;
          font-size:12px; white-space:pre-wrap; max-height:280px;
          overflow-y:auto; color: var(--blue-900); }

/* ---------- Section title ---------- */
.bc-section-title { font-weight:900; font-size:22px;
                    margin:1rem 0 1rem 0; color: var(--blue-900);
                    letter-spacing:-.5px; }
.bc-section-title::before { content:''; display:inline-block; width:6px;
                            height:22px; background: var(--cyan);
                            margin-right:12px; vertical-align:middle;
                            border-radius:3px; }

/* ---------- Preview big image ---------- */
.bc-preview-wrap { background:#fff; border:1px solid #E4E8F0;
                   border-radius: var(--r-card);
                   padding:14px; text-align:center; box-shadow: var(--sh-sm); }
.bc-preview-wrap img { max-width:100%; max-height:320px; border-radius: 14px; }

/* ---------- Buttons ---------- */
div[data-testid="stButton"] button,
div[data-testid="stDownloadButton"] button,
div[data-testid="stFormSubmitButton"] button {
  border-radius: var(--r-pill) !important;
  font-family: var(--font) !important;
  font-weight: 700 !important;
  min-height: 40px;
  padding: 0 24px;
  transition: background .15s, transform .1s;
}
div[data-testid="stButton"] button:active,
div[data-testid="stDownloadButton"] button:active { transform: scale(.98); }
div[data-testid="stButton"] button:focus-visible,
div[data-testid="stDownloadButton"] button:focus-visible {
  outline:none; box-shadow: var(--focus);
}
/* Primary */
div[data-testid="stButton"] button[kind="primary"],
div[data-testid="stFormSubmitButton"] button[kind="primary"] {
  background: var(--blue-500) !important; color:#fff !important;
  border: none !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover {
  background: var(--blue-400) !important;
}
/* Secondary / default */
div[data-testid="stButton"] button[kind="secondary"],
div[data-testid="stDownloadButton"] button {
  background: #fff !important; color: var(--blue-500) !important;
  border: 2px solid var(--blue-500) !important;
}
div[data-testid="stButton"] button[kind="secondary"]:hover,
div[data-testid="stDownloadButton"] button:hover {
  background: var(--blue-50) !important;
}

/* ---------- Inputs / selects ---------- */
div[data-testid="stSelectbox"] > div > div,
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
  border-radius: var(--r-input) !important;
  border: 1.5px solid var(--gray-300) !important;
  min-height: 44px !important;
}
div[data-baseweb="select"]:focus-within > div,
div[data-baseweb="input"]:focus-within > div {
  border-color: var(--blue-500) !important;
  box-shadow: 0 0 0 3px rgba(0,30,180,.08) !important;
}

/* ---------- File uploader ---------- */
div[data-testid="stFileUploader"] section {
  border: 1.5px dashed var(--gray-300) !important;
  border-radius: var(--r-card) !important;
  background: #fff;
}
div[data-testid="stFileUploader"] section:hover {
  border-color: var(--blue-500) !important;
}

/* ---------- Tabs ---------- */
div[data-baseweb="tab-list"] {
  gap: 4px !important; border-bottom: 1px solid #E4E8F0 !important;
}
button[data-baseweb="tab"] {
  font-weight: 700 !important; color: var(--gray-500) !important;
  padding: 10px 18px !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--blue-500) !important;
}
div[data-baseweb="tab-highlight"] {
  background: var(--blue-500) !important; height: 3px !important;
}

/* ---------- Alerts ---------- */
div[data-testid="stAlert"] {
  border-radius: var(--r-card) !important;
  border: none !important; font-family: var(--font);
}
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


def _file_ratio_category(f) -> str | None:
    from io import BytesIO
    from PIL import Image
    try:
        data = f.getvalue() if hasattr(f, "getvalue") else Path(f).read_bytes()
        with Image.open(BytesIO(data)) as img:
            w, h = img.size
        return ratio_category(w, h)
    except Exception:
        return None


def _kv_options_for_file(f) -> tuple[list[str], list[str]]:
    """Devuelve (labels, values) del dropdown filtrados por ratio del archivo."""
    cat = _file_ratio_category(f)
    all_items = list(KV_TYPES.items())
    if not cat:
        return [k for k, _ in all_items], [v for _, v in all_items]
    filtered = [(k, v) for k, v in all_items
                if cat in KV_TYPE_RATIOS.get(v, set())]
    if not filtered:
        filtered = all_items
    return [k for k, _ in filtered], [v for _, v in filtered]


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

            # Per-file type selectors (filtered by image ratio)
            st.markdown('<div style="margin-top:.5rem;"></div>', unsafe_allow_html=True)
            for idx, f in enumerate(files):
                labels, values = _kv_options_for_file(f)
                stored = st.session_state.kv_types_by_name.get(f.name)
                try:
                    default_idx = values.index(stored) if stored in values else 0
                except ValueError:
                    default_idx = 0
                sel = st.selectbox(
                    f.name,
                    options=labels,
                    index=default_idx,
                    key=f"kv_type_{f.name}_{idx}",
                )
                # Map back label -> value using filtered list, not global KV_TYPES.
                st.session_state.kv_types_by_name[f.name] = values[labels.index(sel)]

            # Bulk apply (only files whose ratio is compatible receive the type)
            with st.expander("Aplicar el mismo tipo a todas (compatibles)"):
                bulk_labels = list(KV_TYPES.keys())
                bulk_sel = st.selectbox("Tipo", bulk_labels, key="bulk_type_sel")
                if st.button("Aplicar a todas", width="stretch"):
                    target_value = KV_TYPES[bulk_sel]
                    for f in files:
                        cat = _file_ratio_category(f)
                        allowed = KV_TYPE_RATIOS.get(target_value, set())
                        if cat is None or cat in allowed:
                            st.session_state.kv_types_by_name[f.name] = target_value
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
        f'<div class="bc-score-pill">'
        f'<div class="bc-score-main">'
        f'<span class="bc-score-number">{total_pct:.0f}%</span>'
        f'<span class="bc-score-label">Score total</span>'
        f'</div>'
        f'<div class="bc-score-sub">'
        f'<span>Objetivo <b>{obj_pct:.0f}%</b></span>'
        f'<span>Subjetivo <b>{subj_pct:.0f}%</b></span>'
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


def _render_improvements(result: dict) -> None:
    items = compute_improvements(result)
    if not items:
        st.success("No hay mejoras pendientes — el score está en su máximo.")
        return

    st.markdown(
        '<p class="bc-detail" style="margin-top:0;">Ordenado por impacto en el '
        'score total (puntos porcentuales que subirías al llevarlo a nota máxima).</p>',
        unsafe_allow_html=True,
    )
    html = ""
    for i, it in enumerate(items, 1):
        kind_badge = ("bc-badge partial" if it["kind"] == "subj" else "bc-badge fail")
        html += (
            f'<div class="bc-card">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;gap:.5rem;">'
            f'<h5>{i}. {it["label"]}</h5>'
            f'<span style="font-weight:700;color:#065f46;">+{it["gain_pp"]:.1f} pts</span>'
            f'</div>'
            f'<div style="margin:.2rem 0 .4rem 0;">'
            f'<span class="{kind_badge}">{it["kind"].upper()}</span>'
            f'<span style="margin-left:.5rem;color:#6b7280;font-size:.78rem;">'
            f'Estado actual: <b>{it["current"]}</b></span>'
            f'</div>'
            f'<p class="bc-detail"><b>Consejo:</b> {it["advice"]}</p>'
            f'</div>'
        )
    st.markdown(html, unsafe_allow_html=True)


def _render_result(result: dict) -> None:
    if result.get("error"):
        st.markdown(
            f'<div class="bc-card"><h5>Error analizando {result.get("name","")}</h5>'
            f'<p class="bc-detail">{result["error"]}</p></div>',
            unsafe_allow_html=True,
        )
        return

    # Score pill on top, then preview
    _render_score_card(result)
    uri = _path_to_data_uri(result["path"])
    st.markdown(
        f'<div class="bc-preview-wrap"><img src="{uri}" alt="{result["name"]}"/></div>',
        unsafe_allow_html=True,
    )

    # PDF download
    try:
        pdf_bytes = build_pdf(result)
        pdf_name = f"{Path(result['name']).stem}_brand_check.pdf"
        st.download_button(
            "📄 Descargar reporte PDF",
            data=pdf_bytes,
            file_name=pdf_name,
            mime="application/pdf",
            width="stretch",
            key=f"pdf_dl_{result['name']}",
        )
    except Exception as e:
        st.warning(f"No se pudo generar el PDF: {e}")

    tabs = st.tabs(["Mejoras", "Objetivo", "Subjetivo", "Colores", "Texto (OCR)"])
    with tabs[0]:
        _render_improvements(result)
    with tabs[1]:
        _render_objective(result)
    with tabs[2]:
        _render_subjective(result)
    with tabs[3]:
        _render_colors(result)
    with tabs[4]:
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
