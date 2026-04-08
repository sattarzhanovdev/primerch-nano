from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptInputs:
    product_title: str
    application: str  # tampon_print, screen_print, dtg, dtf, decal, embroidery, engraving
    placement: str  # chest
    aspect_ratio: str = "3:4"
    scene_mode: str = "on_model"  # product_only | on_model
    model_gender: str = "neutral"  # male | female | neutral
    source_kind: str = "logo"  # logo | text
    source_text: str = ""  # used when source_kind=text
    source_color: str = ""  # used when a custom text/logo color is requested
    remove_logo_bg: bool = False  # if True, model must cut out logo from its background
    speed_mode: str = "quality"  # quality | fast
    has_placement_guide: bool = False


def _detect_text_scripts(text: str) -> set[str]:
    scripts: set[str] = set()
    for ch in text or "":
        code = ord(ch)
        if "A" <= ch <= "Z" or "a" <= ch <= "z":
            scripts.add("latin")
        elif 0x0400 <= code <= 0x04FF or 0x0500 <= code <= 0x052F:
            scripts.add("cyrillic")
    return scripts


PLACEMENT_HINTS: dict[str, str] = {
    # NOTE: do not prefix with "ONLY" here; we add "ONLY" explicitly in placement locks
    # to avoid "ONLY ONLY ..." ambiguity in prompts.
    "right_sleeve": "on the WEARER'S RIGHT sleeve panel (anatomical right arm), in the upper-mid sleeve area, below the shoulder seam and above the sleeve cuff",
    "left_sleeve": "on the WEARER'S LEFT sleeve panel (anatomical left arm), in the upper-mid sleeve area, below the shoulder seam and above the sleeve cuff",
    "wearer_right_sleeve": "on the WEARER'S RIGHT sleeve panel (anatomical right arm), in the upper-mid sleeve area, below the shoulder seam and above the sleeve cuff",
    "wearer_left_sleeve": "on the WEARER'S LEFT sleeve panel (anatomical left arm), in the upper-mid sleeve area, below the shoulder seam and above the sleeve cuff",
    "chest": "on the chest area",
    "back": "on the upper back",
    "front": "on the front area",
    "belly": "on the belly front area",
    "left_side": "on the left side",
    "right_side": "on the right side",
    "top": "on the top area",
    "bottom": "on the bottom area",
    "mug_left": "on the left side of the mug",
    "mug_right": "on the right side of the mug",
    "mug_wrap": "wrapped naturally around the mug",
}

APPLICATION_HINTS: dict[str, str] = {
    "tampon_print": "ultra-realistic tampoprint (pad printing): very sharp small print, thin ink layer, no transfer film edge",
    "screen_print": "ultra-realistic screen print: crisp edges, solid coverage, mostly matte ink, very subtle thickness",
    "dtg": "ultra-realistic DTG direct-to-garment print: ink absorbed into fibers, no raised edge, no transfer film, soft matte finish",
    "dtf": "ultra-realistic DTF heat transfer: thin carrier film, slight gloss, subtle film edge (no thick sticker look)",
    "decal": "ultra-realistic decal transfer (overglaze/cold decal): extremely thin, slightly glossy, integrated into the surface (no fabric texture)",
    "embroidery": "ultra-realistic premium embroidery: stitched threads, visible stitches, subtle raised relief",
    "engraving": "ultra-realistic laser engraving: etched/recessed mark, no ink print, material-interaction shading",
}

def _build_compact_technique_hint(application: str) -> str:
    app = (application or "").strip().lower()
    if app == "screen_print":
        return "Technique: screen print (matte ink on top of fabric, crisp edges, no transfer film)."
    if app == "dtg":
        return "Technique: DTG (ink absorbed into fibers; matte; NO transfer film edge; fabric grain shows through)."
    if app == "dtf":
        return "Technique: DTF (thin heat-transfer layer; slight gloss; very subtle edge; NOT ink-absorbed)."
    if app == "tampon_print":
        return "Technique: tampoprint (very sharp thin ink, minimal distortion; NO film edge; NOT embroidered)."
    if app == "decal":
        return "Technique: decal transfer (ultra-thin, slightly glossy, sealed look; no fabric-texture absorption)."
    if app == "embroidery":
        return "Technique: embroidery (real stitched threads with visible stitches and subtle raised relief; NOT flat print)."
    if app == "engraving":
        return "Technique: laser engraving (etched/recessed tone-on-tone mark; NOT colored ink print)."
    return ""


def _build_technique_lock_block(application: str) -> str:
    """
    Adds explicit technique-disambiguation so different application methods remain visually distinct.
    """
    app = (application or "").strip().lower()

    if app == "screen_print":
        return """
TECHNIQUE LOCK (SCREEN PRINT):
- Matte ink on top of fabric with crisp edges and solid coverage.
- Very subtle ink thickness is OK, but do NOT make it puffy/high-relief.
- Absolutely NO transfer film / carrier outline.
- Do NOT make it look like DTG (absorbed) or DTF (glossy film transfer).
""".strip()

    if app == "dtg":
        return """
TECHNIQUE LOCK (DTG):
- Ink must look absorbed into the fibers: soft matte, fabric grain visible through the print.
- No glossy sheen, no carrier film, no visible transfer edge.
- Edges can be slightly softened by the fabric texture (but keep the design readable).
- Do NOT make it look like DTF (gloss + subtle film edge) or screen print (ink sitting on top).
""".strip()

    if app == "dtf":
        return """
TECHNIQUE LOCK (DTF):
- Must look like a thin heat-transfer layer: slightly glossy, high color density, clean shape.
- A very subtle edge is allowed; but do NOT show a big rectangular film border.
- Do NOT make it look absorbed into fibers (DTG look is forbidden).
- Do NOT make it look like thick sticker/plastic patch.
""".strip()

    if app == "tampon_print":
        return """
TECHNIQUE LOCK (TAMPOPRINT / PAD PRINT):
- Extremely sharp small print with a thin ink layer and crisp edges.
- Minimal warping; keep the design very clean and precise.
- NO glossy transfer film edge; NO embroidery texture.
- Do NOT make it look like DTG (fiber absorption) or DTF (transfer film).
""".strip()

    if app == "decal":
        return """
TECHNIQUE LOCK (DECAL):
- Ultra-thin transfer with a slightly glossy sealed look.
- No raised ink thickness, no embroidered thread texture, no fabric-absorbed ink look.
- Do NOT show a thick sticker border or chunky plastic film.
""".strip()

    if app == "embroidery":
        return """
TECHNIQUE LOCK (EMBROIDERY):
- Visible stitched threads, stitch direction, stitch density, and subtle raised relief.
- Should look physically sewn into fabric (micro-shadows around thread).
- Do NOT make it look like flat ink print (screen/DTG/DTF) or like engraved/etched.
""".strip()

    if app == "engraving":
        return """
TECHNIQUE LOCK (LASER ENGRAVING):
- Etched/recessed tone-on-tone mark with subtle depth shading and micro-shadows.
- No ink, no embroidery threads, no glossy film, no colored print.
- Do NOT turn it into a printed decal/transfer.
""".strip()

    return ""


def _human_model_text(model_gender: str) -> str:
    gender_map = {
        "male": "male human model",
        "female": "female human model",
        "neutral": "human model",
    }
    return gender_map.get(model_gender, "human model")


def _is_headwear_product(product_title: str) -> bool:
    hay = (product_title or "").strip().lower()
    markers = (
        "baseball cap",
        "bucket hat",
        "beanie",
        "bandana",
        "visor",
        "headwear",
        "cap",
        "hat",
        "кеп",
        "бейсбол",
        "панама",
        "шапк",
        "бандан",
        "козыр",
        "голов",
    )
    return any(marker in hay for marker in markers)

def has_center_front_obstacles(product_title: str) -> bool:
    hay = (product_title or "").strip().lower()
    markers = (
        "zip hoodie",
        "jacket",
        "raincoat",
        "polo shirt",
        "shirt",
        "anorak",
        "parka",
        "cardigan",
        "толстовк",
        "куртк",
        "ветров",
        "дождев",
        "поло",
        "рубаш",
        "кардиган",
        "парка",
    )
    return any(marker in hay for marker in markers)


def has_hanging_drawstrings(product_title: str) -> bool:
    hay = (product_title or "").strip().lower()
    markers = (
        "hoodie",
        "zip hoodie",
        "худи",
        "толстовк",
    )
    return any(marker in hay for marker in markers)

def prefers_center_chest_logo(product_title: str, source_kind: str) -> bool:
    return (
        (source_kind or "").strip().lower() == "logo"
        and not has_center_front_obstacles(product_title)
    )


def _placement_hint_for_product(product_title: str, placement_key: str, source_kind: str = "") -> str:
    key = (placement_key or "").strip()
    base = PLACEMENT_HINTS.get(key, key)

    if _is_headwear_product(product_title):
        if key == "front":
            return "on the FRONT PANEL of the cap, centered on the crown ABOVE the brim"
        if key == "back":
            return "on the BACK PANEL of the cap, centered above the strap/closure"
        if key == "left_side":
            return "on the LEFT SIDE panel of the cap, centered"
        if key == "right_side":
            return "on the RIGHT SIDE panel of the cap, centered"
        if key == "top":
            return "on the TOP crown area of the cap, centered"
    if key == "chest" and has_center_front_obstacles(product_title):
        return (
            "on one clean upper chest panel, slightly off-center, fully away from the center line, "
            "zipper/placket, hood opening, and hanging drawstrings"
        )
    if key == "chest" and has_hanging_drawstrings(product_title):
        return "centered on the middle chest, BELOW the hanging drawstrings and below the hood opening"
    if key == "chest" and prefers_center_chest_logo(product_title, source_kind):
        return "centered on the upper-middle chest"
    return base

def _build_product_scope_lock(product_title: str) -> str:
    if not _is_headwear_product(product_title):
        return ""

    return """
PRODUCT SCOPE (CRITICAL):
- The requested product is the headwear item (cap/hat) from image 1.
- Apply the design ONLY on the headwear item itself at the requested placement.
- Do NOT apply the design on any other clothing (t-shirt/hoodie/jacket/pants) or accessories.
- Keep all other garments plain/blank with NO text, NO logos, and NO prints.
- If the headwear placement is not clearly visible, adjust pose/camera so the headwear area becomes visible (do NOT move the design to the shirt).
""".strip()

def _build_compact_product_scope_hint(product_title: str) -> str:
    if _is_headwear_product(product_title):
        return " Product scope: cap/hat only; apply design ONLY on headwear; never move it to the shirt; keep clothing blank."
    return ""


def _build_overlap_avoidance_block(product_title: str, placement_key: str) -> str:
    key = (placement_key or "").strip()
    lines = [
        "OVERLAP AVOIDANCE (CRITICAL):",
        "- Keep the entire application on one clean uninterrupted printable surface of the target product.",
        "- Do NOT place the design over seams, stitching, piping, panel joins, pockets, zippers, buttons, snaps, drawstrings, labels, tags, closures, buckles, or hardware.",
        "- Do NOT let the design cross from the target surface onto trim, ribbing, straps, handles, accessories, or background elements.",
        "- If a product detail blocks the requested area, move the design within the SAME placement to the nearest blank area or scale it down.",
        "- Never solve the fit by printing over product construction details.",
    ]

    if key in {"chest", "front", "belly", "back"}:
        lines.extend([
            "- Keep the design inside one flat torso panel with clear margins from the collar, neckline, shoulder seams, side seams, hem, placket, hood opening, and cuffs.",
            "- Do NOT place the design on or across a pocket, kangaroo pocket, zipper, button placket, drawstring, or ribbed waistband.",
        ])
        if key == "chest" and has_center_front_obstacles(product_title):
            lines.extend([
                "- If the product has a center zipper/placket or hanging hood drawstrings, place the design fully on ONE upper chest panel to the side of those details.",
                "- Never center the design between the drawstrings or across the front closure line.",
            ])
        elif key == "chest" and has_hanging_drawstrings(product_title):
            lines.extend([
                "- For hoodies with hanging drawstrings, keep the design centered but LOWER on the chest, below the drawstring endpoints and below the hood opening.",
                "- Never let the design intersect the drawstrings or sit in the narrow corridor between them.",
            ])
    elif key in {"right_sleeve", "left_sleeve", "wearer_right_sleeve", "wearer_left_sleeve"}:
        lines.extend([
            "- Keep the design fully inside the sleeve panel and away from the shoulder seam, armhole seam, cuff, and any panel boundary.",
            "- Do NOT place the design on the shoulder top, collar, torso panel, or across any seam.",
        ])
    elif key.startswith("mug_"):
        lines.extend([
            "- Keep the design on the smooth mug body only.",
            "- Do NOT place the design on or across the handle, rim, base, inner lip, or shadow/background.",
        ])
    elif _is_headwear_product(product_title):
        lines.extend([
            "- Keep the design on the requested cap panel only.",
            "- Do NOT place the design over the brim edge, top button, eyelets, panel seams, sweatband edge, or back strap/closure.",
        ])

    return "\n".join(lines)


def _build_compact_overlap_avoidance_hint(product_title: str, placement_key: str) -> str:
    key = (placement_key or "").strip()
    hint = (
        " Keep the application on one clean uninterrupted printable surface only. "
        "Never place it over seams, pockets, zippers, buttons, labels, drawstrings, hardware, or other product details. "
        "If space is tight, scale down or shift within the same placement."
    )

    if key.startswith("mug_"):
        return hint + " Mug only: stay on the mug body, not the handle, rim, or base."
    if _is_headwear_product(product_title):
        return hint + " Headwear only: avoid brim edges, eyelets, panel seams, and back strap/closure."
    if key == "chest" and has_center_front_obstacles(product_title):
        return (
            hint
            + " If the garment has a zipper/placket or hanging drawstrings, keep the design on a single upper chest panel beside them, never across the center line."
        )
    if key == "chest" and has_hanging_drawstrings(product_title):
        return (
            hint
            + " For drawstring hoodies, keep the design centered but lower on the chest, below the hanging drawstrings; never let the design intersect them."
        )
    return hint


def _build_foreground_occlusion_block(product_title: str, placement_key: str) -> str:
    key = (placement_key or "").strip()
    if key not in {"chest", "front", "belly", "back"}:
        return ""

    if not has_center_front_obstacles(product_title) and "hoodie" not in (product_title or "").lower():
        return """
FOREGROUND OCCLUSION (CRITICAL):
- Treat any foreground garment details that pass in front of the placement area as being ABOVE the design.
- If a seam, flap, fold edge, strap, or hardware crosses the design area, it must remain visible on top and naturally occlude the design.
- The design must never overwrite or erase garment construction details.
""".strip()

    return """
FOREGROUND OCCLUSION (CRITICAL):
- The design is printed on the fabric surface UNDER existing garment details, not on top of them.
- Drawstrings, zipper teeth, zipper pull, placket edges, hood opening edges, seam ridges, pocket edges, folds, and shadows must stay fully visible ABOVE the design.
- If any of those foreground details cross the placement area, they must naturally occlude/hide the covered part of the design.
- Never paint, replace, blur, erase, or flatten those foreground details to make room for the design.
- The design may be partially hidden by those objects; that is correct. The objects must stay on top.
""".strip()


def _build_compact_foreground_occlusion_hint(product_title: str, placement_key: str) -> str:
    key = (placement_key or "").strip()
    if key not in {"chest", "front", "belly", "back"}:
        return ""
    if has_center_front_obstacles(product_title) or "hoodie" in (product_title or "").lower():
        return (
            " Foreground details such as drawstrings, zipper/placket, seam ridges, pocket edges, folds, and shadows must remain ABOVE the design and occlude it naturally."
        )
    return (
        " Any foreground garment detail crossing the placement must remain visible on top of the design and occlude it naturally."
    )


def _build_placement_guide_block(has_placement_guide: bool, placement_key: str) -> str:
    if not has_placement_guide:
        return ""
    key = (placement_key or "").strip()
    if key not in {"chest", "front", "belly", "back"}:
        return ""
    return """
PLACEMENT GUIDE IMAGE (CRITICAL):
- Image 3 is a placement guide only.
- Green-marked area = the ONLY allowed printable fabric for the design.
- Red-marked zones = forbidden garment details / foreground objects.
- Place the entire design fully inside the green area from image 3.
- Do NOT move the design into any red-marked zone.
- Do NOT copy any green/red overlays, guide boxes, marks, or annotations from image 3 into the final output.
""".strip()


def _build_compact_placement_guide_hint(has_placement_guide: bool, placement_key: str) -> str:
    if not has_placement_guide:
        return ""
    key = (placement_key or "").strip()
    if key not in {"chest", "front", "belly", "back"}:
        return ""
    return (
        " Image 3 is a placement guide only: keep the whole design inside the green zone, avoid all red-marked zones, and never copy the guide markings into the output."
    )


def _build_model_framing_block(product_title: str, placement_key: str) -> str:
    key = (placement_key or "").strip()

    if _is_headwear_product(product_title):
        return """
MODEL FRAMING:
- Show the model full-length (head-to-toe) with the face clearly visible.
- Keep the headwear fully visible and prominent.
- Do NOT crop the top of the head or the top of the headwear.
- Do NOT zoom out so far that the headwear becomes tiny or unreadable.
""".strip()

    if key in {"right_sleeve", "left_sleeve", "wearer_right_sleeve", "wearer_left_sleeve"}:
        return """
MODEL FRAMING:
- Show the model full-length (head-to-toe) with the face clearly visible.
- Keep the target sleeve closest to the camera and prominent in frame.
- You may slightly raise/rotate the arm naturally to reveal the sleeve panel.
""".strip()

    if key == "chest":
        return """
MODEL FRAMING:
- Show a compact upper-body ecommerce photo (head to waist/hips).
- Keep the face visible and the entire head fully in frame.
- Keep the chest/upper torso large and centered so the application is clearly readable.
- Do NOT frame head-to-toe full-length; avoid showing feet/shoes.
""".strip()

    return """
MODEL FRAMING:
- Show the model in full height, from head to feet.
- Keep the full body silhouette visible in frame.
- Keep the face clearly visible (not obscured, not cropped).
- Keep the entire head fully visible, including the top of the head/hair.
- Keep both feet / full footwear fully visible.
- Leave a small clean margin above the head and below the feet.
- Do NOT crop the model to only the face, bust, or upper torso.
""".strip()


def _build_viewpoint_block(placement_key: str) -> str:
    key = (placement_key or "").strip()

    if key in {"right_sleeve", "wearer_right_sleeve"}:
        return """
VIEWPOINT / CAMERA ANGLE:
- Use a clear right-side 3/4 profile or right-side view.
- Turn the model so the WEARER'S RIGHT sleeve is the primary visible surface.
- Keep the wearer's right arm closest to the camera.
- Do NOT use a straight front-facing pose.
- Do NOT let the chest/front become the main visible surface.
""".strip()

    if key in {"left_sleeve", "wearer_left_sleeve"}:
        return """
VIEWPOINT / CAMERA ANGLE:
- Use a clear left-side 3/4 profile or left-side view.
- Turn the model so the WEARER'S LEFT sleeve is the primary visible surface.
- Keep the wearer's left arm closest to the camera.
- Do NOT use a straight front-facing pose.
- Do NOT let the chest/front become the main visible surface.
""".strip()

    if key == "left_side":
        return """
VIEWPOINT / CAMERA ANGLE:
- Show the product from its LEFT side.
- Use a clear left-side profile / side-angle view.
- The left side panel must be the primary visible surface in frame.
- Do NOT use a front view or mostly front-facing angle.
""".strip()

    if key == "right_side":
        return """
VIEWPOINT / CAMERA ANGLE:
- Show the product from its RIGHT side.
- Use a clear right-side profile / side-angle view.
- The right side panel must be the primary visible surface in frame.
- Do NOT use a front view or mostly front-facing angle.
""".strip()

    return ""


def _build_scene_block(scene_mode: str, model_gender: str, source_kind: str, product_title: str, placement_key: str) -> str:
    viewpoint_block = _build_viewpoint_block(placement_key)

    if scene_mode == "product_only":
        base = """
SCENE RULES:
- Keep the first image as a product-only image.
- Do NOT add a person, model, mannequin, arms, hands, or body.
- Preserve the original product shape and product presentation.
- Do NOT redesign the scene.
- Show the FULL product in the frame, so the entire item is visible.
- Do NOT crop the product.
- Keep the target placement area clearly visible.

GARMENT IDENTITY LOCK (CRITICAL):
- The product in the output must be the EXACT same product as in the first image.
- Do NOT change garment color, fabric texture, weave, material finish, seams, stitching, buttons, collar, cuffs, hem, or silhouette.
- Do NOT swap the product for a different garment, even if it looks similar.
""".strip()
        if viewpoint_block:
            return base + "\n" + viewpoint_block
        return base

    model_text = _human_model_text(model_gender)
    framing_block = _build_model_framing_block(product_title, placement_key)

    extra_text_rules = ""
    if (source_kind or "").strip().lower() == "text":
        extra_text_rules = """
- Keep the pose simple and natural so the applied text remains readable.
- Avoid extreme folds, twisting, stretching, or aggressive fabric distortion over the design area.
- Do NOT sacrifice text readability for realism.
""".strip()

    base = f"""
SCENE RULES:
- Present the product worn by a real {model_text}.
- Show a real person clearly wearing / trying on the product.
- Use a human model only; do NOT use a mannequin, hanger, flat lay, invisible body, or floating garment.
- The result must look like a real commercial fashion photograph, not AI art.
- Keep the garment itself EXACTLY consistent with the first image.
- Do NOT redesign, replace, restyle, recolor, or “upgrade” the garment.
- Do NOT change the cut, fit, silhouette, sleeve shape, collar, placket, buttons, hem, fabric texture, or material appearance.
- Do NOT alter the garment’s base color, shading, pattern, weave, or fabric grain.
- Use professional studio lighting, soft realistic shadows, clean styling, and natural body proportions.
- Frame the subject like an ecommerce apparel photoshoot.
- Keep the target placement area clearly visible and unobstructed.
- Do NOT crop out the application area.
- Preserve realistic posture, fabric drape, and clothing tension on the body.
""".strip()

    base = base + "\n" + framing_block
    if viewpoint_block:
        base = base + "\n" + viewpoint_block

    if extra_text_rules:
        return base + "\n" + extra_text_rules
    return base


def _build_fast_scene_block(scene_mode: str, model_gender: str, product_title: str, placement_key: str) -> str:
    viewpoint_block = _build_viewpoint_block(placement_key)

    if scene_mode == "product_only":
        base = """
SCENE:
- Product-only ecommerce studio photo.
- Do NOT add a person, model, mannequin, body, arms, or hands.
- Show the FULL product in the frame, so the entire item is visible.
- Do NOT crop the product.
- Keep the target area clearly visible.
""".strip()
        if viewpoint_block:
            return base + "\n\n" + viewpoint_block
        return base

    model_text = _human_model_text(model_gender)
    framing_block = _build_model_framing_block(product_title, placement_key)
    base = f"""
SCENE:
- Show the EXACT product worn by a real {model_text}.
- The person must be clearly wearing / trying on the item.
- Use a simple ecommerce pose with the placement area visible.
- Do NOT use a mannequin, hanger, flat lay, invisible body, or floating garment.

{framing_block}
""".strip()
    if viewpoint_block:
        return base + "\n\n" + viewpoint_block
    return base


def _build_material_block(application: str, source_kind: str) -> str:
    kind = (source_kind or "").strip().lower()
    app = (application or "").strip().lower()

    if app == "embroidery":
        if kind == "text":
            return """
EMBROIDERY TEXT REALISM:
- The embroidery must look like real stitched thread sewn into the fabric.
- Maintain clean letter edges and clear letter anatomy.
- Keep each character distinct and readable.
- Do NOT over-distort, over-warp, melt, smear, or stylize the letters.
- Use strong thread contrast against the garment.
- Avoid low-contrast embroidery such as white on white or light gray on white.
- Preserve realistic stitch texture, thread depth, and subtle raised relief.
- Keep the result looking premium and physically believable.
""".strip()

        return """
EMBROIDERY REALISM:
- The embroidery must look like real stitched thread sewn into the fabric.
- Show visible stitch direction, stitch density, thread thickness, thread relief, and subtle raised depth.
- The logo must conform naturally to the garment surface.
- The logo must bend and deform slightly according to real fabric folds, curvature, sleeve rotation, chest volume, and garment tension.
- Follow the local surface geometry exactly, as real embroidery would on curved fabric.
- Add subtle micro-shadows around raised thread areas.
- Preserve realistic fabric compression underneath the embroidery.
- Keep the embroidery edges sewn, tactile, and physically integrated into the garment.
- Avoid flat printed appearance, sticker look, plastic gloss, or floating appearance.
""".strip()

    if app == "screen_print":
        return (
            """
SCREEN PRINT REALISM:
- Screen print should look like real ink on the surface: crisp edges, opaque coverage, mostly matte finish.
- Very subtle ink thickness is allowed, but avoid puffy/high-relief effects.
- No transfer film, no glossy sticker look, no visible carrier edge.
""".strip()
            if kind != "text"
            else """
SCREEN PRINT TEXT REALISM:
- Keep the text crisp and fully readable.
- Screen print should look like matte ink with sharp edges and solid coverage.
- No glossy carrier film edge; do not make it look like a sticker.
""".strip()
        )

    if app == "dtg":
        return (
            """
DTG REALISM:
- DTG must look like ink absorbed into fabric fibers (no transfer film).
- No raised edge, no plastic gloss; soft matte finish.
- Allow mild fabric-texture show-through and slight natural softening at edges.
""".strip()
            if kind != "text"
            else """
DTG TEXT REALISM:
- Keep the text fully readable.
- DTG should look like ink absorbed into the fibers: no film edge, no thickness, matte finish.
""".strip()
        )

    if app == "dtf":
        return (
            """
DTF REALISM:
- DTF must look like a thin heat-transfer layer with a subtle carrier film.
- Slight gloss is allowed; show a very subtle edge only if physically plausible.
- Avoid thick sticker/plastic patch look and avoid large obvious rectangular film borders.
""".strip()
            if kind != "text"
            else """
DTF TEXT REALISM:
- Keep the text fully readable.
- DTF should look like a thin transfer: slight gloss and a subtle edge are ok, but never a thick sticker.
""".strip()
        )

    if app == "tampon_print":
        return (
            """
TAMPOPRINT REALISM:
- Tampoprint (pad printing) must look like a very sharp small print with a thin ink layer.
- Keep edges crisp and clean; minimal distortion; no fabric-absorption look.
- Do NOT add embroidery texture, transfer film borders, or raised relief.
""".strip()
            if kind != "text"
            else """
TAMPOPRINT TEXT REALISM:
- Keep the text crisp and fully readable.
- Tampoprint should be a thin sharp ink layer with clean edges (no transfer film, no embroidery).
""".strip()
        )

    if app == "decal":
        return (
            """
DECAL REALISM:
- Decal (overglaze/cold) must look extremely thin and integrated into the surface.
- Slight gloss is allowed; no fabric-thread/embroidery texture; no raised ink.
- Avoid obvious sticker borders and avoid thick plastic film appearance.
""".strip()
            if kind != "text"
            else """
DECAL TEXT REALISM:
- Keep the text fully readable.
- Decal should look extremely thin and slightly glossy, integrated into the surface (not embroidered, not absorbed ink).
""".strip()
        )

    if app == "engraving":
        return (
            """
LASER ENGRAVING REALISM:
- Laser engraving must look etched/recessed into the material (no colored ink print).
- The mark should be tone-on-tone with subtle depth, micro-shadows, and realistic burn/etch shading.
- Avoid glossy sticker/print appearance; avoid embroidery texture.
""".strip()
            if kind != "text"
            else """
LASER ENGRAVING TEXT REALISM:
- Keep the text fully readable.
- The text must look laser-engraved (etched/recessed), tone-on-tone, with subtle depth/shading; never like printed ink.
""".strip()
        )

    return f"""
MATERIAL REALISM:
- Make the {application} look physically realistic for the product material.
- Follow the original lighting, folds, surface curvature, and perspective.
- Preserve realistic depth and material interaction.
""".strip()


def _build_focus_block(placement_key: str) -> str:
    if placement_key in {"right_sleeve", "left_sleeve", "wearer_right_sleeve", "wearer_left_sleeve"}:
        return """
FOCUS / CROPPING (SLEEVE):
- Output EXACTLY ONE photo (single frame). Do NOT create a diptych, collage, split panel, or multi-view layout.
- Show the model full-length (head-to-toe) with the face clearly visible.
- Use a 3/4 pose so the target sleeve is closest to the camera and clearly readable.
- Keep the sleeve panel and the applied design clearly visible (do not make it tiny).
- The application must sit below the shoulder seam and above the sleeve cuff.
- The application must NOT touch the collar/neckline.
- Do NOT mirror, flip, or swap garment/person orientation.
- Keep the target sleeve as the dominant visible plane, not the chest/front.
""".strip()

    return """
FOCUS / CROPPING:
- Output a single image (no collage, no split panels).
""".strip()


def _build_side_disambiguation_block(placement_key: str) -> str:
    if placement_key in {"right_sleeve", "wearer_right_sleeve"}:
        return """
SLEEVE PLACEMENT LOCK:
- Apply the design ONLY on the WEARER'S RIGHT sleeve.
- The design must be placed on the sleeve fabric panel itself.
- Place it in the upper-middle sleeve region, below the shoulder seam and above the cuff.
- Do NOT place it on the shoulder top.
- Do NOT place it on the collar.
- Do NOT place it on the neck opening area.
- Do NOT place it on the chest or front torso.
- Do NOT let the text drift upward toward the collar.
- Do NOT let the design cross garment panel boundaries.
- RIGHT sleeve means the sleeve attached to the wearer's RIGHT arm (anatomical right), regardless of where it appears in the photo.
- Do NOT decide the side by “left/right side of the image”. The camera angle may swap sides.
- Preserve the wearer's true anatomical side at all times.
- The non-target sleeve must remain blank.
- If the sleeve is not clearly visible in the original photo, adjust the pose/camera so the RIGHT sleeve becomes the primary visible area (do NOT move the design to the chest).

FINAL CHECK (CRITICAL):
- Before finalizing the output, verify the design is on the WEARER'S RIGHT sleeve (and NOT on chest/back/left sleeve).
- If it is not on the right sleeve, redo the placement to the right sleeve.
""".strip()

    if placement_key in {"left_sleeve", "wearer_left_sleeve"}:
        return """
SLEEVE PLACEMENT LOCK:
- Apply the design ONLY on the WEARER'S LEFT sleeve.
- The design must be placed on the sleeve fabric panel itself.
- Place it in the upper-middle sleeve region, below the shoulder seam and above the cuff.
- Do NOT place it on the shoulder top.
- Do NOT place it on the collar.
- Do NOT place it on the neck opening area.
- Do NOT place it on the chest or front torso.
- Do NOT let the text drift upward toward the collar.
- Do NOT let the design cross garment panel boundaries.
- LEFT sleeve means the sleeve attached to the wearer's LEFT arm (anatomical left), regardless of where it appears in the photo.
- Do NOT decide the side by “left/right side of the image”. The camera angle may swap sides.
- Preserve the wearer's true anatomical side at all times.
- The non-target sleeve must remain blank.
- If the sleeve is not clearly visible in the original photo, adjust the pose/camera so the LEFT sleeve becomes the primary visible area (do NOT move the design to the chest).

FINAL CHECK (CRITICAL):
- Before finalizing the output, verify the design is on the WEARER'S LEFT sleeve (and NOT on chest/back/right sleeve).
- If it is not on the left sleeve, redo the placement to the left sleeve.
""".strip()

    return ""


def _build_source_fidelity_block(
    source_kind: str,
    source_text: str,
    source_color: str = "",
    *,
    remove_logo_bg: bool = False,
) -> str:
    if (source_kind or "").strip().lower() == "text":
        st = (source_text or "").strip()
        requested_color = (source_color or "").strip()
        scripts = _detect_text_scripts(st)
        char_lock = ""
        compact = "".join(ch for ch in st if not ch.isspace())
        if compact and len(compact) <= 12:
            quoted_chars = ", ".join(f'"{ch}"' for ch in compact)
            char_lock = f"""
CHARACTER LOCK (CRITICAL):
- The text has EXACTLY {len(compact)} characters.
- Characters in order: {quoted_chars}.
- Do NOT omit, merge, replace, or reorder any character.
""".strip()
        script_lock = ""
        if scripts == {"latin"}:
            script_lock = """
SCRIPT LOCK (CRITICAL):
- Use LATIN letters only.
- Do NOT transliterate, substitute, or replace any letter with a Cyrillic lookalike.
""".strip()
        elif scripts == {"cyrillic"}:
            script_lock = """
SCRIPT LOCK (CRITICAL):
- Use CYRILLIC letters only.
- Do NOT transliterate, substitute, or replace any letter with a Latin lookalike.
""".strip()
        elif scripts == {"latin", "cyrillic"}:
            script_lock = """
SCRIPT LOCK (CRITICAL):
- Preserve the exact mixed Latin/Cyrillic character sequence from the source.
- Do NOT normalize the word into a single alphabet and do NOT substitute lookalike letters.
""".strip()
        color_block = f"""
COLOR & VISIBILITY:
- Use EXACTLY this text color: {requested_color}.
- Preserve that color faithfully in the final print/embroidery.
- Keep the text readable while retaining the requested color.
- Do NOT auto-convert the text to black, white, or another substitute color.
""".strip() if requested_color else """
COLOR & VISIBILITY:
- The text color must clearly contrast with the garment.
- If the garment is white or light, use black or near-black thread/ink.
- If the garment is dark, use white or light gray thread/ink.
- NEVER use same-color-on-same-color.
- Ensure strong visual separation between text and fabric.
""".strip()

        return f"""
STRICT TEXT FIDELITY (CRITICAL):
- The text to apply is EXACTLY: "{st}"
- Treat image 2 as the exact authoritative wordmark artwork for this text.
- Copy the visible glyph shapes from image 2; do NOT re-type or reinterpret the word from scratch.
- Every letter must be correct, readable, and clearly recognizable.
- The word must read exactly as "{st}" with no deviations.

TEXT STYLE:
- Use a clean Arial-like sans-serif font.
- Use a simple, modern, non-decorative, non-ornamental font style.
- Do NOT use gothic, script, handwritten, distorted, decorative, melted, glitched, or futuristic lettering.
- Keep the typography clean, commercial, and easy to read.

TEXT RULES:
- Preserve exact spelling, casing, spacing, and proportions.
- Do NOT modify, stylize, reinterpret, paraphrase, or distort the text.
- Do NOT switch alphabet/script, do NOT transliterate, and do NOT replace letters with lookalike characters from another alphabet.
- Do NOT generate fake letters or approximate letter-like shapes.
- Do NOT merge letters into abstract forms.
- The text must be fully legible at normal viewing distance.

{char_lock}

{script_lock}

{color_block}

STRICT PROHIBITIONS:
- No broken letters
- No pseudo-text
- No unreadable typography
- No mirrored text
- No extra letters
- No misspellings

OUTPUT REQUIREMENT:
- The result must look like real professional apparel branding with clean, readable typography.
""".strip()

    requested_color = (source_color or "").strip()
    color_block = f"""
COLOR FIDELITY (CRITICAL):
- Use EXACTLY this logo color: {requested_color}.
- Preserve that color faithfully in the final application.
- Do NOT revert the logo to its original source color.
- Do NOT substitute a nearby shade or recolor it automatically.
""".strip() if requested_color else ""

    # Always remove background for logo sources to avoid "white rectangle" artifacts.
    bg_remove = """
BACKGROUND REMOVAL (CRITICAL):
- Treat any background in image 2 (solid/gradient/photo/paper/texture) as NOT part of the logo.
- Cut out the logo cleanly and use ONLY the logo artwork as a transparent cutout.
- Do NOT place a white/black rectangle, badge, box, or backdrop behind the logo unless it is part of the logo artwork itself.
- Preserve edges (anti-aliasing) with NO halos and NO leftover background pixels.
- If image 2 contains an intentional background shape that is clearly part of the logo artwork, keep ONLY that shape (not the surrounding photo/paper).
""".strip()

    base = """
STRICT LOGO FIDELITY:
- Treat image 2 as the exact master brand artwork.
- Copy only the visible logo marks from image 2.
- Preserve the exact shape, spacing, layout, colors, proportions, orientation, edges, and all design details.
- Do NOT modify, redraw, restyle, reinterpret, simplify, enhance, replace, regenerate, vectorize, or "clean up" the logo.
- Do NOT substitute the logo with a similar brand mark, alternate glyphs, fake letters, or an approximate symbol.
- If the logo cannot be preserved exactly, leave the target area blank instead of inventing another logo.
""".strip()
    parts = [base]
    if bg_remove:
        parts.append(bg_remove)
    if color_block:
        parts.append(color_block)
    return "\n\n".join(parts)


def _build_source_fidelity_block_fast(
    source_kind: str,
    source_text: str,
    source_color: str = "",
    *,
    remove_logo_bg: bool = False,
) -> str:
    kind = (source_kind or "").strip().lower()
    if kind == "text":
        text = (source_text or "").strip()
        requested_color = (source_color or "").strip()
        scripts = _detect_text_scripts(text)
        color_line = f"\n- Use EXACTLY this text color: {requested_color}." if requested_color else ""
        compact = "".join(ch for ch in text if not ch.isspace())
        char_line = ""
        if compact and len(compact) <= 12:
            quoted_chars = ", ".join(f'"{ch}"' for ch in compact)
            char_line = f"\n- Exact character order: {quoted_chars}. Do not omit or replace any character."
        script_line = ""
        if scripts == {"latin"}:
            script_line = " Use LATIN letters only; never substitute Cyrillic lookalikes."
        elif scripts == {"cyrillic"}:
            script_line = " Use CYRILLIC letters only; never substitute Latin lookalikes."
        elif scripts == {"latin", "cyrillic"}:
            script_line = " Preserve the exact mixed Latin/Cyrillic sequence; do not normalize or transliterate it."
        return f"""
TEXT FIDELITY (CRITICAL):
- Render EXACTLY this text: {text!r}
- Treat image 2 as the exact wordmark artwork; copy it rather than re-typing it.
- Preserve spelling, casing, spacing, and order.
- Keep it fully legible; no stylization that breaks letters.{color_line}{char_line}
- Do NOT change alphabet/script, transliterate, or substitute lookalike letters between Cyrillic and Latin.{script_line}
""".strip()

    requested_color = (source_color or "").strip()
    color_line = f"\n- Keep the logo in EXACTLY this color: {requested_color}. Do NOT revert it." if requested_color else ""
    bg_line = (
        "\n- Remove/cut out any background from image 2; treat it as transparent (no white box, no rectangle, no halo)."
    )
    return f"""
LOGO FIDELITY (CRITICAL):
- Copy the logo from image 2 EXACTLY (shape, colors, spacing, proportions, orientation).
- Do NOT redraw, restyle, simplify, enhance, or "clean up" the logo.
- If exact fidelity is not possible, leave the area blank (do not invent).{bg_line}{color_line}
""".strip()


def _build_no_invention_block(source_kind: str) -> str:
    if (source_kind or "").strip().lower() == "text":
        return """
NO-INVENTION RULE (CRITICAL):
- Edit only what is required to place the provided text.
- Treat image 2 as the source artwork for the wordmark itself.
- Do NOT re-type, transliterate, or "correct" the word into another alphabet or casing.
- Do NOT invent new letters, words, symbols, decorations, textures, logos, or branding.
- If the text cannot be preserved exactly, keep the application area blank rather than inventing approximate text.
- Do NOT add any extra elements to "improve" the result.
""".strip()

    return """
NO-INVENTION RULE (CRITICAL):
- Edit only what is required to place the provided logo.
- Do NOT invent new logo parts, icons, outlines, text, textures, decorations, or alternate branding.
- If any part of the logo cannot be preserved exactly, leave that area unchanged rather than generating a replacement.
- Do NOT add any extra elements to "improve" the result.
""".strip()


def _build_negative_block(source_kind: str) -> str:
    lines = [
        "DO NOT ADD:",
        "- tags",
        "- labels",
        "- neck labels",
        "- sleeve labels",
        "- hem labels",
        "- extra embroidery",
        "- extra print",
        "- extra logos",
        "- stray letters",
        "- isolated glyph fragments",
        "- partial wordmarks",
        "- any additional text besides the provided design",
        "- brand marks",
        "- badges",
        "- stickers",
        "- patches elsewhere",
        "- packaging",
        "- hangtags",
        "- watermark",
        "- decorative elements not present in the original product",
        "- unnecessary background props",
    ]

    if (source_kind or "").strip().lower() == "text":
        lines.extend([
            "- random letters",
            "- fake typography",
            "- corrupted text",
            "- mirrored text",
            "- wrong alphabet/script",
            "- Cyrillic/Latin lookalike substitutions",
            "- wrong casing",
            "- unreadable lettering",
            "- extra words",
            "- misspellings",
        ])

    return "\n".join(lines)


def _build_surface_conformity_block(source_kind: str) -> str:
    if (source_kind or "").strip().lower() == "text":
        return """
SURFACE CONFORMITY:
- The application must follow the local geometry of the product surface.
- Respect folds, wrinkles, seams, stretching, drape, curvature, compression, and perspective.
- Apply only mild realistic deformation over the text area.
- Keep the text readable and structurally intact.
- Do NOT over-warp, over-bend, over-stretch, or over-compress the letters.
- Keep the text scale realistic for the product.
""".strip()

    return """
SURFACE CONFORMITY:
- The application must follow the local geometry of the product surface.
- Respect folds, wrinkles, seams, stretching, drape, curvature, compression, and perspective.
- The design must not appear flat if the fabric is curved.
- Warp the design naturally where the material bends, exactly as it would in a real photograph.
- Keep the design scale realistic for the product.
""".strip()


def _build_text_layout_block(placement_key: str, source_kind: str) -> str:
    if (source_kind or "").strip().lower() != "text":
        return ""

    key = (placement_key or "").strip()
    if key in {"right_sleeve", "left_sleeve", "wearer_right_sleeve", "wearer_left_sleeve"}:
        return """
TEXT LAYOUT (CRITICAL):
- Render the text as one small normal readable horizontal wordmark across the upper sleeve.
- Keep the word upright for left-to-right reading, with the baseline roughly parallel to the ground / sleeve cuff.
- Place it in the upper sleeve area, not along the forearm length.
- If the word feels too long, reduce the font size instead of rotating or stacking it.
- Do NOT rotate the text by 90 degrees.
- Do NOT stack letters vertically.
- Do NOT run the word vertically down the sleeve.
- Do NOT turn the word into a vertical column.
- Do NOT place one letter under another.
- Keep the text compact, clean, and easy to read at a glance.
""".strip()

    return """
TEXT LAYOUT:
- Keep the text upright, readable, and arranged as a normal horizontal word or line.
- Do NOT stack letters vertically.
- Do NOT rotate the text into a vertical reading direction.
""".strip()


def _build_logo_layout_block(placement_key: str, source_kind: str) -> str:
    if (source_kind or "").strip().lower() != "logo":
        return ""

    key = (placement_key or "").strip()
    if key in {"right_sleeve", "left_sleeve", "wearer_right_sleeve", "wearer_left_sleeve"}:
        return """
LOGO LAYOUT (CRITICAL):
- Apply the entire logo from image 2 as one intact compact logo lockup.
- Do NOT split the logo into separate pieces.
- Do NOT isolate, invent, or add standalone letters, glyphs, initials, or fragments beside the logo.
- If image 2 contains an icon plus a wordmark, keep that full arrangement together in the same order as image 2.
- If the full logo feels too long for the sleeve, scale down the whole logo uniformly until it fits.
- Do NOT crop, truncate, abbreviate, wrap, stack, or partially omit the logo.
- Do NOT place any detached mark before or after the logo.
""".strip()

    return """
LOGO LAYOUT:
- Keep the logo as one intact mark exactly as shown in image 2.
- Do NOT split the logo into multiple separate elements.
- If it feels too large, scale down the entire logo uniformly instead of cropping it.
""".strip()


def _build_scale_lock_block(placement_key: str, source_kind: str) -> str:
    key = (placement_key or "").strip()
    kind = (source_kind or "").strip().lower()

    if key in {"right_sleeve", "left_sleeve", "wearer_right_sleeve", "wearer_left_sleeve", "chest"}:
        target_size = "about 18-28% of the garment width / sleeve panel width"
    elif key in {"front", "belly", "back"}:
        target_size = "about 20-35% of the printable area width"
    elif key in {"mug_left", "mug_right"}:
        target_size = "about 22-32% of the mug body width"
    elif key == "mug_wrap":
        target_size = "about 45-60% of the printable wrap width"
    else:
        target_size = "about 18-30% of the target area width"

    if kind == "text":
        return f"""
DESIGN SCALE (CRITICAL):
- Keep the text at a commercially realistic size.
- Default to a modest readable size, not an oversized statement graphic.
- Leave clear blank product area around the text.
- For this placement, keep the visible text around {target_size}.
- If uncertain, choose the smaller believable size.
- Do NOT let the text fill most of the target area or dominate the full product photo.
""".strip()

    return f"""
LOGO SCALE (CRITICAL):
- Keep the logo small-to-medium and commercially realistic.
- Do NOT upscale the logo aggressively just because image 2 is tightly cropped.
- Leave clear blank product area around the logo.
- For this placement, keep the visible logo around {target_size}.
- If uncertain, choose the smaller believable size.
- Never let the logo fill most of the target area or become the main subject of the photo.
""".strip()

def _canonicalize_placement(placement_key: str) -> str:
    """
    Normalize placement keys so prompts always refer to the wearer's anatomical side.
    Frontend may send either `right_sleeve/left_sleeve` or `wearer_right_sleeve/wearer_left_sleeve`.
    """
    key = (placement_key or "").strip()
    if key == "right_sleeve":
        return "wearer_right_sleeve"
    if key == "left_sleeve":
        return "wearer_left_sleeve"
    return key

def _build_sleeve_exclusion_block(placement_key: str) -> str:
    if placement_key not in {"right_sleeve", "left_sleeve", "wearer_right_sleeve", "wearer_left_sleeve"}:
        return ""

    return """
FORBIDDEN AREAS FOR SLEEVE PLACEMENT:
- collar
- placket
- neckline
- shoulder top
- trapezius area
- chest
- upper torso
- back
- opposite sleeve
- seam-crossing placement
""".strip()

def _build_position_anchor_block(placement_key: str) -> str:
    if placement_key in {"right_sleeve", "wearer_right_sleeve"}:
        return """
POSITION ANCHOR:
- Anchor the design at the center of the wearer's right sleeve panel.
- Keep a clear margin from the shoulder seam above and the cuff below.
- Keep the entire design inside the sleeve panel boundaries.
""".strip()

    if placement_key in {"left_sleeve", "wearer_left_sleeve"}:
        return """
POSITION ANCHOR:
- Anchor the design at the center of the wearer's left sleeve panel.
- Keep a clear margin from the shoulder seam above and the cuff below.
- Keep the entire design inside the sleeve panel boundaries.
""".strip()

    return ""

def _wants_full_body_framing(scene_mode: str, product_title: str, placement_key: str) -> bool:
    mode = (scene_mode or "").strip().lower()
    if mode == "product_only":
        return False

    key = (placement_key or "").strip()
    if key.startswith("mug_"):
        return False
    # For chest/front branding, a compact upper-body shot is preferred.
    if key in {"chest", "front", "belly", "back"}:
        return False
    return True

def _build_full_body_framing_block() -> str:
    return """
FULL-BODY FRAMING (CRITICAL):
- Show the model full-length, head-to-toe (include feet/shoes).
- Keep the face clearly visible (not obscured, not cropped).
- Prefer a standing full-body ecommerce pose.
- Do NOT crop out the head/face, hands, or feet.
- Keep the product and the target placement area clearly visible (not tiny).
""".strip()

def _build_compact_framing_hint(scene_mode: str, product_title: str, placement_key: str) -> str:
    mode = (scene_mode or "").strip().lower()
    if mode == "product_only":
        return ""

    key = (placement_key or "").strip()
    if _is_headwear_product(product_title):
        return " Framing: full-body head-to-toe with face visible; include feet/shoes; keep the headwear fully visible (do not crop the top)."
    if key in {"right_sleeve", "left_sleeve", "wearer_right_sleeve", "wearer_left_sleeve"}:
        return " Framing: full-body head-to-toe with face visible; keep the target sleeve closest to camera and clearly readable."
    if key.startswith("mug_"):
        return ""
    if key == "chest":
        return " Framing: compact upper-body (head to waist/hips) with face visible; keep the chest area large; do NOT show full-length head-to-toe."
    return " Framing: full-body head-to-toe with face visible; include feet/shoes; do not crop the person."


def _build_compact_sleeve_lock(placement_key: str) -> str:
    key = (placement_key or "").strip()
    if key in {"right_sleeve", "wearer_right_sleeve"}:
        return (
            " SLEEVE LOCK: Apply design ONLY on the WEARER'S RIGHT sleeve (anatomical right). "
            "Opposite/left sleeve must stay blank. Do not mirror/flip. If wrong side, redo."
        )
    if key in {"left_sleeve", "wearer_left_sleeve"}:
        return (
            " SLEEVE LOCK: Apply design ONLY on the WEARER'S LEFT sleeve (anatomical left). "
            "Opposite/right sleeve must stay blank. Do not mirror/flip. If wrong side, redo."
        )
    return ""


def _build_compact_viewpoint_hint(placement_key: str) -> str:
    key = (placement_key or "").strip()
    if key in {"right_sleeve", "wearer_right_sleeve"}:
        return " Camera: clear right-side 3/4 view; wearer's RIGHT sleeve closest to camera."
    if key in {"left_sleeve", "wearer_left_sleeve"}:
        return " Camera: clear left-side 3/4 view; wearer's LEFT sleeve closest to camera."
    if key == "left_side":
        return " Camera: clear left-side view; left side panel most visible."
    if key == "right_side":
        return " Camera: clear right-side view; right side panel most visible."
    return ""

def build_nanobanana_prompt(inputs: PromptInputs) -> str:
    placement_key = _canonicalize_placement(inputs.placement)
    placement = _placement_hint_for_product(inputs.product_title, placement_key, inputs.source_kind)
    application = APPLICATION_HINTS.get(inputs.application, inputs.application)
    technique_lock_block = _build_technique_lock_block(inputs.application)
    is_sleeve = placement_key in {"wearer_right_sleeve", "wearer_left_sleeve"}
    full_body_block = _build_full_body_framing_block() if _wants_full_body_framing(inputs.scene_mode, inputs.product_title, placement_key) else ""
    product_scope_lock = _build_product_scope_lock(inputs.product_title)
    overlap_avoidance_block = _build_overlap_avoidance_block(inputs.product_title, placement_key)
    foreground_occlusion_block = _build_foreground_occlusion_block(inputs.product_title, placement_key)
    placement_guide_block = _build_placement_guide_block(inputs.has_placement_guide, placement_key)

    if (inputs.speed_mode or "").strip().lower() == "fast":
        # Ultra-compact prompt to reduce model overhead and speed up generation.
        technique_hint = _build_compact_technique_hint(inputs.application)
        fidelity = _build_source_fidelity_block_fast(
            inputs.source_kind,
            inputs.source_text,
            inputs.source_color,
            remove_logo_bg=inputs.remove_logo_bg,
        )
        no_invention = _build_no_invention_block(inputs.source_kind)
        scale_lock = _build_scale_lock_block(placement_key, inputs.source_kind)
        text_layout = _build_text_layout_block(placement_key, inputs.source_kind)
        logo_layout = _build_logo_layout_block(placement_key, inputs.source_kind)
        sleeve_lock = _build_side_disambiguation_block(placement_key) if is_sleeve else ""
        focus = _build_focus_block(placement_key) if is_sleeve else ""
        scene = _build_fast_scene_block(inputs.scene_mode, inputs.model_gender, inputs.product_title, placement_key)
        overlap_hint = _build_compact_overlap_avoidance_hint(inputs.product_title, placement_key)
        occlusion_hint = _build_compact_foreground_occlusion_hint(inputs.product_title, placement_key)
        guide_hint = _build_compact_placement_guide_hint(inputs.has_placement_guide, placement_key)
        garment_lock = """
GARMENT LOCK (CRITICAL):
- Keep the garment/product EXACTLY the same as the first image.
- Do NOT change color, fabric texture, seams, collar, cuffs, hem, buttons, or silhouette.
- Do NOT replace the product with a different one.
""".strip()

        placement_lock = f"""
PLACEMENT LOCK (CRITICAL):
- Place the design ONLY {placement}.
- No duplicates anywhere else (no chest/back/other sleeve).
""".strip()

        logo_priority = ""
        if (inputs.source_kind or "").strip().lower() == "logo":
            logo_priority = """
LOGO PRIORITY (CRITICAL):
- Exact logo fidelity is more important than stylization.
- Do NOT create a "better", cleaner, sharper, or alternative version of the logo.
- Apply the logo once exactly as provided.
""".strip()

        return f"""
Use image 1 as the product reference. Use image 2 as the exact design source.{(' Use image 3 as a placement guide only.' if inputs.has_placement_guide else '')}

TASK:
Apply the provided design as {application} {placement} on the product in image 1 ("{inputs.product_title}").

{technique_hint}

{fidelity}

{logo_priority}

{no_invention}

{scale_lock}

{text_layout}

{logo_layout}

{garment_lock}

{product_scope_lock}

{full_body_block}

{focus}

{sleeve_lock}

{placement_lock}

{scene}

{overlap_hint}

{occlusion_hint}

{guide_hint}

- Photorealistic ecommerce studio photo.
- Output aspect ratio: {inputs.aspect_ratio}.
""".strip()

    scene_block = _build_scene_block(
        scene_mode=inputs.scene_mode,
        model_gender=inputs.model_gender,
        source_kind=inputs.source_kind,
        product_title=inputs.product_title,
        placement_key=placement_key,
    )
    focus_block = _build_focus_block(placement_key)
    side_block = _build_side_disambiguation_block(placement_key)
    material_block = _build_material_block(inputs.application, inputs.source_kind)
    negative_block = _build_negative_block(inputs.source_kind)
    fidelity_block = _build_source_fidelity_block(
        inputs.source_kind,
        inputs.source_text,
        inputs.source_color,
        remove_logo_bg=inputs.remove_logo_bg,
    )
    no_invention_block = _build_no_invention_block(inputs.source_kind)
    surface_block = _build_surface_conformity_block(inputs.source_kind)
    text_layout_block = _build_text_layout_block(placement_key, inputs.source_kind)
    logo_layout_block = _build_logo_layout_block(placement_key, inputs.source_kind)
    scale_lock_block = _build_scale_lock_block(placement_key, inputs.source_kind)
    sleeve_exclusion_block = _build_sleeve_exclusion_block(placement_key)
    position_anchor_block = _build_position_anchor_block(placement_key)

    orientation_priority_block = ""
    if is_sleeve:
        orientation_priority_block = """
SLEEVE ORIENTATION PRIORITY:
- Sleeve placements always refer to the WEARER'S anatomical side.
- Do NOT infer sleeve side from the photo layout, camera angle, framing, mirroring, or “left/right side of the image”.
- Viewer perspective must never override the wearer's true left/right side.
""".strip()

    strict_placement_lock = f"""
PLACEMENT LOCK (CRITICAL):
- Apply the design ONLY {placement}.
- Do NOT place it anywhere else.
- Do NOT add duplicates.
- Do NOT add a second placement on chest/back/sleeves/other sides.
- If any part of the design appears outside the target area, fix it so the entire design stays ONLY in the target area.
""".strip()

    sleeve_extra_lock = ""
    if is_sleeve:
        sleeve_extra_lock = """
SLEEVE-ONLY OUTPUT (CRITICAL):
- The chest/front torso must remain completely blank and unchanged (no design there).
- Full-body framing with the face visible is allowed/expected, but the target sleeve must remain the primary visible surface (closest to camera).
- Do NOT “compromise” by placing the design on the chest because it is more visible.
- Prefer a clear side or 3/4 side pose where the target sleeve is closest to the camera and fully visible.
- Straight front-facing poses are not allowed for sleeve-focused outputs.
""".strip()

    return f"""
Use the first image as the base product reference and the second image as the source design.{(' Use image 3 as a placement guide only.' if inputs.has_placement_guide else '')}

TASK:
Apply the design from the second image EXACTLY as provided as {application} {placement}
on the product in the first image ("{inputs.product_title}").

{fidelity_block}

{no_invention_block}

{scale_lock_block}

{text_layout_block}

{logo_layout_block}

{product_scope_lock}

STRICT EDIT SCOPE:
- Change only what is necessary to place the provided design realistically.
- Do NOT alter the garment design beyond the application itself.
- Do NOT move the design to another area.
- Place the application ONLY {placement}.
- Preserve the wearer's true anatomical left/right side.
- Do NOT interpret sleeve side by viewer perspective alone.
- Do NOT add any extra branding elements.
- Preserve the original product identity and visual structure.

{negative_block}

{scene_block}

{full_body_block}

{focus_block}

{side_block}

{orientation_priority_block}

{position_anchor_block}

{sleeve_exclusion_block}

{placement_guide_block}

{overlap_avoidance_block}

{foreground_occlusion_block}

{technique_lock_block}

{strict_placement_lock}

{sleeve_extra_lock}

{surface_block}

{material_block}

COMPOSITION:
- Output aspect ratio must be {inputs.aspect_ratio}.
- Make the result look like a real premium commercial product photo.
- Keep the placement area clearly visible.
- Preserve realistic scale, realistic perspective, and realistic material behavior.
- Avoid stylized, cartoon, synthetic, fake, over-rendered, or AI-art-looking output.

FINAL OUTPUT RULE:
Return a photorealistic result of the same product from the first image,
with only one intended branding change:
the provided design applied as {application} {placement}.
""".strip()


def build_gpt_image_prompt(inputs: PromptInputs) -> str:
    """
    Compact prompt optimized for GPT Image 1.5 endpoints (strict prompt length limits).
    """
    placement_key = _canonicalize_placement(inputs.placement)
    placement = _placement_hint_for_product(inputs.product_title, placement_key, inputs.source_kind)
    application = APPLICATION_HINTS.get(inputs.application, inputs.application)
    technique_hint = _build_compact_technique_hint(inputs.application)

    kind = (inputs.source_kind or "").strip().lower()
    fidelity = ""
    if kind == "text":
        text = (inputs.source_text or "").strip()
        color_hint = f" Use EXACTLY this text color: {(inputs.source_color or '').strip()}." if (inputs.source_color or "").strip() else ""
        scripts = _detect_text_scripts(text)
        compact = "".join(ch for ch in text if not ch.isspace())
        char_hint = ""
        if compact and len(compact) <= 12:
            quoted_chars = ", ".join(f'"{ch}"' for ch in compact)
            char_hint = f" Exact character order: {quoted_chars}. Do not omit or replace any character."
        script_hint = ""
        if scripts == {"latin"}:
            script_hint = " Use LATIN letters only; never substitute Cyrillic lookalikes."
        elif scripts == {"cyrillic"}:
            script_hint = " Use CYRILLIC letters only; never substitute Latin lookalikes."
        elif scripts == {"latin", "cyrillic"}:
            script_hint = " Preserve the exact mixed Latin/Cyrillic sequence; do not normalize or transliterate it."
        layout_hint = ""
        if placement_key in {"right_sleeve", "wearer_right_sleeve", "left_sleeve", "wearer_left_sleeve"}:
            layout_hint = " Render it as one small upright horizontal wordmark across the upper sleeve. If it does not fit, reduce size instead of rotating it. Do not stack letters vertically."
        fidelity = (
            f"Text must be EXACTLY: {text!r}. Treat image 2 as the exact wordmark artwork and copy it rather than re-typing it. "
            f"Keep it readable (no distorted letters). Do not change alphabet/script or substitute Cyrillic/Latin lookalikes."
            f"{color_hint}{char_hint}{script_hint}{layout_hint}"
        )
    else:
        layout_hint = ""
        if placement_key in {"right_sleeve", "wearer_right_sleeve", "left_sleeve", "wearer_left_sleeve"}:
            layout_hint = (
                " Keep the logo as one intact compact lockup. "
                "Do not split it into separate parts or stray letters. "
                "If it feels too long for the sleeve, scale down the whole logo uniformly instead of cropping or abbreviating it."
            )
        bg_hint = (
            " Remove/cut out any background from image 2 and use ONLY the logo artwork as a clean transparent cutout "
            "(no white box/rectangle, no badge backdrop unless it is part of the logo, no halos)."
        )
        fidelity = (
            "Logo must match image 2 EXACTLY (shape, colors, spacing, proportions, orientation). "
            "Do not redraw/clean up. If exact match is not possible, leave area blank."
            f"{bg_hint}{layout_hint}"
        )

    scene_mode = (inputs.scene_mode or "").strip().lower()
    if scene_mode == "product_only":
        scene = "Keep product-only (no human, no mannequin). Show the FULL product in the frame, so the entire item is visible. Do NOT crop the product."
    else:
        model_text = _human_model_text(inputs.model_gender)
        scene = f"Show the same product worn by a real {model_text} in a simple ecommerce studio photo."

    aspect_ratio = (inputs.aspect_ratio or "").strip() or "3:4"
    framing_hint = _build_compact_framing_hint(inputs.scene_mode, inputs.product_title, placement_key)
    viewpoint = _build_compact_viewpoint_hint(placement_key)
    sleeve_lock = _build_compact_sleeve_lock(placement_key)
    product_scope = _build_compact_product_scope_hint(inputs.product_title)
    overlap_hint = _build_compact_overlap_avoidance_hint(inputs.product_title, placement_key)
    occlusion_hint = _build_compact_foreground_occlusion_hint(inputs.product_title, placement_key)
    guide_hint = _build_compact_placement_guide_hint(inputs.has_placement_guide, placement_key)
    return (
        f"Use image 1 as the base product. Use image 2 as the design source.{(' Use image 3 as a placement guide only.' if inputs.has_placement_guide else '')}\n"
        f"TASK: Apply the design as {application} {placement} on the product in image 1 ({inputs.product_title!r}).\n"
        f"{(technique_hint + chr(10)) if technique_hint else ''}"
        f"{fidelity}\n"
        "EDIT SCOPE: change only what is needed for the application; do not change product color, material, seams, or silhouette.\n"
        "No duplicate placements; do not add extra logos/text.\n"
        f"{scene}{product_scope}{framing_hint}{viewpoint}{sleeve_lock}{overlap_hint}{occlusion_hint}{guide_hint}\n"
        f"Output aspect ratio: {aspect_ratio}."
    ).strip()
