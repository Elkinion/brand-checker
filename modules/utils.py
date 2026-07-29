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


def ratio_category(w: int, h: int) -> str:
    if not h:
        return "square"
    r = w / h
    if r >= 2.5:
        return "ultrawide"
    if r >= 1.4:
        return "landscape"
    if r >= 0.85:
        return "square"
    if r >= 0.65:
        return "portrait_std"
    return "portrait_tall"


def image_ratio_category(path: str | Path) -> str | None:
    dim = image_dimensions(path)
    if not dim:
        return None
    return ratio_category(dim[0], dim[1])


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, int(c))) for c in rgb))
