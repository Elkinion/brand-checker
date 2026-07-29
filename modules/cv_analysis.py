from __future__ import annotations
import httpx
from pathlib import Path

from modules.config import GCV_API_KEY, REQUEST_TIMEOUT
from modules.utils import image_to_base64, image_dimensions
from modules.brand_rules import (
    distances_to_palette, COLOR_MATCH_THRESHOLD,
    PRIMARY_COLORS, SECONDARY_COLORS,
    get_profile, get_palette_for_gama, get_threshold_for_gama,
)

CV_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"
MAX_INLINE_MB = 10


def build_cv_body(image_path: str | Path) -> dict:
    size_mb = Path(image_path).stat().st_size / (1024 * 1024)
    if size_mb > MAX_INLINE_MB:
        raise ValueError(
            f"La imagen pesa {size_mb:.1f} MB. Máximo {MAX_INLINE_MB} MB para envío en base64."
        )
    b64 = image_to_base64(image_path)
    return {
        "requests": [{
            "image": {"content": b64},
            "features": [
                {"type": "LOGO_DETECTION",        "maxResults": 5},
                {"type": "IMAGE_PROPERTIES",      "maxResults": 10},
                {"type": "TEXT_DETECTION",        "maxResults": 50},
                {"type": "SAFE_SEARCH_DETECTION", "maxResults": 1},
            ],
        }],
    }


def call_cv_api(image_path: str | Path, client: httpx.Client | None = None) -> dict:
    if not GCV_API_KEY:
        raise RuntimeError("GCV_API_KEY no está configurada en secrets.toml")
    body = build_cv_body(image_path)
    close = False
    if client is None:
        client = httpx.Client(timeout=REQUEST_TIMEOUT)
        close = True
    try:
        r = client.post(
            CV_ENDPOINT,
            params={"key": GCV_API_KEY},
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
        raise RuntimeError(f"Cloud Vision API error ({r.status_code}): {msg}")
    return r.json()


def process_cv_response(raw: dict, image_dim: tuple[int, int] | None = None,
                        kv_type: str | None = None) -> dict:
    responses = raw.get("responses") or [{}]
    r = responses[0]

    if kv_type:
        profile = get_profile(kv_type)
        palette = get_palette_for_gama(profile.gama)
        threshold = get_threshold_for_gama(profile.gama)
    else:
        from modules.brand_rules import BRAND_PALETTE
        palette = BRAND_PALETTE
        threshold = COLOR_MATCH_THRESHOLD

    # --- Logos ---
    logos: list[dict] = []
    w_img, h_img = (image_dim or (0, 0))
    for l in (r.get("logoAnnotations") or []):
        verts = ((l.get("boundingPoly") or {}).get("vertices")) or []
        xs = [v.get("x", 0) for v in verts]
        ys = [v.get("y", 0) for v in verts]
        if not xs or not ys:
            continue
        w_box = max(xs) - min(xs)
        h_box = max(ys) - min(ys)
        area_box = w_box * h_box
        rel_area = area_box / (w_img * h_img) if w_img and h_img else None
        rel_width = w_box / w_img if w_img else None
        logos.append({
            "description": l.get("description"),
            "score": l.get("score"),
            "bounding_box": {"x": min(xs), "y": min(ys), "w": w_box, "h": h_box},
            "relative_area": rel_area,
            "relative_width": rel_width,
        })

    # --- Colores dominantes ---
    dominant_colors: list[dict] = []
    for c in (((r.get("imagePropertiesAnnotation") or {}).get("dominantColors") or {}).get("colors") or []):
        col = c.get("color") or {}
        rr = int(col.get("red", 0) or 0)
        gg = int(col.get("green", 0) or 0)
        bb = int(col.get("blue", 0) or 0)
        hex_str = "#{:02X}{:02X}{:02X}".format(rr, gg, bb)
        dists = distances_to_palette(hex_str, palette)
        nearest_name = min(dists, key=dists.get)
        nearest_dist = dists[nearest_name]
        is_brand = nearest_dist < threshold
        dominant_colors.append({
            "hex": hex_str,
            "rgb": (rr, gg, bb),
            "pixel_fraction": c.get("pixelFraction", 0) or 0,
            "score": c.get("score", 0) or 0,
            "palette_distances": dists,
            "nearest_palette": nearest_name,
            "nearest_distance": nearest_dist,
            "is_brand": is_brand,
            "is_primary": is_brand and nearest_name in PRIMARY_COLORS,
            "is_secondary": is_brand and nearest_name in SECONDARY_COLORS,
        })

    # --- OCR ---
    full_text = ""
    text_annotations = r.get("textAnnotations") or []
    text_blocks_count = 0
    text_blocks: list[str] = []
    if text_annotations:
        full_text = text_annotations[0].get("description", "") or ""
        text_blocks_count = len(text_annotations) - 1
        text_blocks = [t.get("description", "") for t in text_annotations[1:]]

    # --- Safe search ---
    ss = r.get("safeSearchAnnotation") or {}

    return {
        "logos": logos,
        "dominant_colors": dominant_colors,
        "full_text": full_text,
        "text_blocks_count": text_blocks_count,
        "text_blocks": text_blocks,
        "safe_search": ss,
        "reference_matches": [],
    }


def analyze_image(image_path: str | Path, client: httpx.Client | None = None,
                  kv_type: str | None = None) -> dict:
    dim = image_dimensions(image_path)
    raw = call_cv_api(image_path, client=client)
    return process_cv_response(raw, image_dim=dim, kv_type=kv_type)
