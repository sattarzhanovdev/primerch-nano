from __future__ import annotations

import hashlib
from pathlib import Path
from threading import RLock

from PIL import Image, ImageDraw, ImageFont

from .storage import uploads_dir


_TEXT_RENDER_LOCK = RLock()
_TEXT_RENDER_CACHE: dict[str, Path] = {}
_TEXT_RENDER_VERSION = "v3"
_FONT_CANDIDATES = (
    "DejaVuSans-Bold.ttf",
    "DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/Library/Fonts/Arial.ttf",
    "/Library/Fonts/ArialHB.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)


def _text_cache_key(
    text: str,
    width: int,
    height: int,
    padding: int,
    font_size: int,
    min_width: int,
    min_height: int,
) -> str:
    payload = "\n".join(
        [
            _TEXT_RENDER_VERSION,
            text,
            str(width),
            str(height),
            str(padding),
            str(font_size),
            str(min_width),
            str(min_height),
        ]
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _load_font(font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, font_size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_text_png(
    text: str,
    *,
    width: int = 1200,
    height: int = 700,
    padding: int = 16,
    font_size: int = 140,
    min_width: int = 240,
    min_height: int = 240,
) -> Path:
    text = (text or "").strip()
    if not text:
        raise ValueError("text is empty")

    cache_key = _text_cache_key(text, width, height, padding, font_size, min_width, min_height)
    with _TEXT_RENDER_LOCK:
        cached = _TEXT_RENDER_CACHE.get(cache_key)
        if cached and cached.exists():
            return cached

    deterministic_out = uploads_dir() / f"text_{cache_key[:20]}.png"
    with _TEXT_RENDER_LOCK:
        if deterministic_out.exists():
            _TEXT_RENDER_CACHE[cache_key] = deterministic_out
            return deterministic_out

    # Use transparent pixels with WHITE RGB to avoid a black rectangle if some pipeline drops alpha.
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Prefer fonts with reliable Cyrillic coverage; otherwise text mode can
    # produce ambiguous reference glyphs and the model may misspell the word.
    font = _load_font(font_size)

    # Simple wrapping
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for w in words:
        test = " ".join([*current, w])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= width - padding * 2:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    if not lines:
        lines = [text]

    y = padding
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        line_h = bbox[3] - bbox[1]
        x = (width - line_w) // 2
        draw.text((x, y), line, font=font, fill=(0, 0, 0, 255))
        y += line_h + 24

    # Crop tightly to avoid the model hallucinating a "big rectangle patch".
    alpha = img.split()[-1]
    non_empty = alpha.getbbox()
    if non_empty:
        l, t, r, b = non_empty
        l = max(0, l - padding)
        t = max(0, t - padding)
        r = min(img.size[0], r + padding)
        b = min(img.size[1], b + padding)
        img = img.crop((l, t, r, b))

    # Keep enough transparent canvas around short words so upstream image validation
    # accepts the asset and the text does not get interpreted as an oversized patch.
    margin = max(padding * 2, int(max(img.size) * 0.4))
    canvas_w = max(min_width, img.size[0] + margin * 2)
    canvas_h = max(min_height, img.size[1] + margin * 2)
    if canvas_w != img.size[0] or canvas_h != img.size[1]:
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
        offset = ((canvas_w - img.size[0]) // 2, (canvas_h - img.size[1]) // 2)
        canvas.paste(img, offset, img)
        img = canvas

    with _TEXT_RENDER_LOCK:
        cached = _TEXT_RENDER_CACHE.get(cache_key)
        if cached and cached.exists():
            return cached
        if deterministic_out.exists():
            _TEXT_RENDER_CACHE[cache_key] = deterministic_out
            return deterministic_out
        img.save(deterministic_out, format="PNG")
        _TEXT_RENDER_CACHE[cache_key] = deterministic_out
        return deterministic_out
