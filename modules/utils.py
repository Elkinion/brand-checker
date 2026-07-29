from __future__ import annotations
import base64
import mimetypes
from pathlib import Path
from PIL import Image

MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def image_to_base64(path: str | Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def guess_mime(path: str | Path) -> str:
    ext = Path(path).suffix.lower()
    if ext in MIME_BY_EXT:
        return MIME_BY_EXT[ext]
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def image_dimensions(path: str | Path) -> tuple[int, int] | None:
    try:
        with Image.open(path) as img:
            return img.size  # (w, h)
    except Exception:
        return None


def detect_kv_type_from_image(path: str | Path) -> str:
    """
    Heurística por aspect ratio (w/h). Solo mira geometría, no contenido.
    Se usa como default cuando el usuario elige "Auto".
    """
    dim = image_dimensions(path)
    if not dim:
        return "tactico_pop"
    w, h = dim
    if h == 0:
        return "tactico_pop"
    ratio = w / h  # >1 horizontal, <1 vertical

    if ratio >= 2.5:
        return "ooh_valla"                 # Ultra-wide (vallas 3x1, 4x1)
    if 1.4 <= ratio < 2.5:
        return "social_feed"               # Horizontal (16:9, feed)
    if 0.85 <= ratio <= 1.15:
        return "social_post"               # ~Cuadrado (1:1)
    if 0.45 <= ratio < 0.65:
        return "social_story"              # Portrait alto (9:16, ~0.56)
    if 0.65 <= ratio < 0.85:
        return "afiche_tienda"             # Portrait estándar (3:4, 5:7)
    if ratio < 0.45:
        return "social_story"              # Muy alto, tratar como story
    return "tactico_pop"


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, int(c))) for c in rgb))
