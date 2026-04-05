from __future__ import annotations

import re


_HEX_COLOR_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def normalize_hex_color(value: str, default: str = "") -> str:
    raw = str(value or "").strip()
    if not raw:
        return default

    match = _HEX_COLOR_RE.fullmatch(raw)
    if not match:
        return default

    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return f"#{digits.lower()}"


def hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    normalized = normalize_hex_color(value)
    if not normalized:
        return None

    return (
        int(normalized[1:3], 16),
        int(normalized[3:5], 16),
        int(normalized[5:7], 16),
    )
