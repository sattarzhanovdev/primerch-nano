from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageChops, ImageOps
from fastapi import Request

from .color_utils import hex_to_rgb, normalize_hex_color
from .storage import build_file_url, uploads_dir


def _local_upload_path_from_url(source_url: str) -> Path | None:
    raw = str(source_url or "").strip()
    if not raw:
        return None

    parsed = urlparse(raw)
    path = (parsed.path or raw).strip()
    if not path.startswith("/uploads/"):
        return None

    name = path.split("/uploads/", 1)[1].split("?", 1)[0].strip()
    if not name:
        return None

    local = uploads_dir() / name
    if local.exists():
        return local
    return None


def _content_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    rgba = img.convert("RGBA")
    alpha_bbox = rgba.getchannel("A").getbbox()

    rgb = rgba.convert("RGB")
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, (255, 255, 255)))
    white_bbox = diff.getbbox()

    if alpha_bbox and white_bbox:
        left = min(alpha_bbox[0], white_bbox[0])
        top = min(alpha_bbox[1], white_bbox[1])
        right = max(alpha_bbox[2], white_bbox[2])
        bottom = max(alpha_bbox[3], white_bbox[3])
        return (left, top, right, bottom)
    return alpha_bbox or white_bbox


def _optimized_logo_path(source: Path, color_hex: str = "") -> Path:
    stat = source.stat()
    version_tag = "logo-ref-v3"
    normalized_color = normalize_hex_color(color_hex, "original")
    signature = hashlib.sha1(
        f"{version_tag}:{source.resolve()}:{stat.st_mtime_ns}:{stat.st_size}:{normalized_color}".encode("utf-8")
    ).hexdigest()[:20]
    return uploads_dir() / f"logo_ref_v3_{signature}.png"

def _recolor_logo(img: Image.Image, color_hex: str) -> Image.Image:
    rgb = hex_to_rgb(color_hex)
    if rgb is None:
        return img

    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    alpha_extrema = alpha.getextrema()

    if alpha_extrema and alpha_extrema != (255, 255):
        mask = alpha
    else:
        grayscale = ImageOps.grayscale(rgba.convert("RGB"))
        mask = ImageChops.invert(grayscale)
        mask = mask.point(lambda value: 0 if value < 8 else min(255, int(value * 1.15)))
        if alpha_extrema:
            mask = ImageChops.lighter(mask, alpha)

    colored = Image.new("RGBA", rgba.size, (*rgb, 0))
    colored.putalpha(mask)
    return colored


def optimize_logo_reference(request: Request, source_url: str, color_hex: str = "") -> str:
    local = _local_upload_path_from_url(source_url)
    if local is None:
        return source_url

    normalized_color = normalize_hex_color(color_hex)
    optimized = _optimized_logo_path(local, normalized_color)
    if optimized.exists():
        return build_file_url(request, f"/uploads/{optimized.name}")

    with Image.open(local) as src:
        img = ImageOps.exif_transpose(src).convert("RGBA")
        bbox = _content_bbox(img)
        if bbox:
            pad = max(8, int(min(img.size) * 0.03))
            left = max(0, bbox[0] - pad)
            top = max(0, bbox[1] - pad)
            right = min(img.size[0], bbox[2] + pad)
            bottom = min(img.size[1], bbox[3] + pad)
            img = img.crop((left, top, right, bottom))

        if normalized_color:
            img = _recolor_logo(img, normalized_color)

        # Add a generous transparent artboard so the model keeps the logo
        # at a more believable physical size instead of inflating it.
        margin = max(64, int(max(img.size) * 0.45))
        canvas_side = max(img.size) + (margin * 2)
        canvas = Image.new("RGBA", (canvas_side, canvas_side), (0, 0, 0, 0))
        offset = ((canvas_side - img.size[0]) // 2, (canvas_side - img.size[1]) // 2)
        canvas.paste(img, offset, img)
        img = canvas

        max_dim = 1400
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        optimized.parent.mkdir(parents=True, exist_ok=True)
        img.save(optimized, format="PNG")

    return build_file_url(request, f"/uploads/{optimized.name}")
