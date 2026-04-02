from __future__ import annotations

import secrets
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .storage import uploads_dir


def render_text_png(
    text: str,
    *,
    width: int = 1200,
    height: int = 700,
    padding: int = 16,
    font_size: int = 140,
) -> Path:
    text = (text or "").strip()
    if not text:
        raise ValueError("text is empty")

    # Use transparent pixels with WHITE RGB to avoid a black rectangle if some pipeline drops alpha.
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    try:
        # Prefer bold for readability after embroidery/print simulation.
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

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
        # Bold-ish by drawing twice with small offsets.
        draw.text((x, y), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x + 1, y), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y + 1), line, font=font, fill=(0, 0, 0, 255))
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

    filename = f"text_{secrets.token_hex(10)}.png"
    out = uploads_dir() / filename
    img.save(out, format="PNG")
    return out
