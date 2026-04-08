from __future__ import annotations

from PIL import Image, ImageDraw, ImageOps

from .prompts import has_center_front_obstacles


def safe_print_box_ratios(product_title: str, placement: str) -> list[tuple[float, float, float, float]]:
    key = (placement or "").strip().lower()
    if key != "chest":
        return []

    title = (product_title or "").strip().lower()
    if has_center_front_obstacles(product_title):
        return [(0.69, 0.22, 0.85, 0.36)]
    if "hoodie" in title or "sweatshirt" in title:
        return [(0.64, 0.23, 0.83, 0.37)]
    return [(0.60, 0.24, 0.81, 0.38)]


def forbidden_zone_ratios(product_title: str, placement: str) -> list[tuple[float, float, float, float]]:
    key = (placement or "").strip().lower()
    if key != "chest":
        return []

    if not has_center_front_obstacles(product_title):
        return []

    return [
        (0.47, 0.14, 0.54, 0.95),  # zipper / placket line
        (0.29, 0.13, 0.40, 0.48),  # left drawstring corridor
        (0.54, 0.13, 0.69, 0.48),  # right drawstring corridor
        (0.42, 0.10, 0.60, 0.22),  # hood opening / neck hardware area
    ]


def build_product_placement_guide(
    product_img: Image.Image,
    *,
    product_title: str,
    placement: str,
) -> Image.Image | None:
    safe_boxes = safe_print_box_ratios(product_title, placement)
    if not safe_boxes:
        return None

    base = ImageOps.exif_transpose(product_img).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    w, h = base.size
    stroke = max(4, int(round(min(w, h) * 0.006)))
    radius = max(10, int(round(min(w, h) * 0.02)))

    for left, top, right, bottom in forbidden_zone_ratios(product_title, placement):
        box = (
            int(round(w * left)),
            int(round(h * top)),
            int(round(w * right)),
            int(round(h * bottom)),
        )
        draw.rounded_rectangle(box, radius=radius, fill=(230, 64, 64, 72), outline=(230, 64, 64, 255), width=stroke)
        draw.line((box[0], box[1], box[2], box[3]), fill=(255, 255, 255, 190), width=max(2, stroke - 1))
        draw.line((box[0], box[3], box[2], box[1]), fill=(255, 255, 255, 190), width=max(2, stroke - 1))

    for left, top, right, bottom in safe_boxes:
        box = (
            int(round(w * left)),
            int(round(h * top)),
            int(round(w * right)),
            int(round(h * bottom)),
        )
        draw.rounded_rectangle(box, radius=radius, fill=(46, 204, 113, 86), outline=(46, 204, 113, 255), width=stroke)

    return Image.alpha_composite(base, overlay)
