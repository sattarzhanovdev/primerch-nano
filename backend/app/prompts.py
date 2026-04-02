from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptInputs:
    product_title: str
    application: str  # embroidery, screen_print, dtf, patch, engraving, sublimation
    placement: str  # wearer_right_sleeve, wearer_left_sleeve, chest, back, front, belly, mug_left, mug_right, mug_wrap
    aspect_ratio: str = "3:4"
    scene_mode: str = "on_model"  # product_only | on_model
    model_gender: str = "neutral"  # male | female | neutral
    source_kind: str = "logo"  # logo | text
    source_text: str = ""  # used when source_kind=text


PLACEMENT_HINTS: dict[str, str] = {
    "right_sleeve": "ONLY on the wearer's right sleeve panel, in the upper-mid sleeve area, below the shoulder seam and above the sleeve cuff",
    "left_sleeve": "ONLY on the wearer's left sleeve panel, in the upper-mid sleeve area, below the shoulder seam and above the sleeve cuff",
    "wearer_right_sleeve": "ONLY on the wearer's right sleeve panel, in the upper-mid sleeve area, below the shoulder seam and above the sleeve cuff",
    "wearer_left_sleeve": "ONLY on the wearer's left sleeve panel, in the upper-mid sleeve area, below the shoulder seam and above the sleeve cuff",
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
    "print": "ultra-realistic print",
    "embroidery": "ultra-realistic premium embroidery",
    "screen_print": "ultra-realistic screen print",
    "dtf": "ultra-realistic DTF transfer print",
    "dtg": "ultra-realistic DTG direct-to-garment print",
    "heat_transfer": "ultra-realistic heat transfer (thermotransfer) print",
    "patch": "ultra-realistic sewn fabric patch",
    "engraving": "ultra-realistic laser engraving",
    "sublimation": "ultra-realistic sublimation print",
    "flex": "ultra-realistic flex vinyl heat transfer",
    "flock": "ultra-realistic flock vinyl (velvety) heat transfer",
    "puff_print": "ultra-realistic puff print (raised ink)",
    "high_density": "ultra-realistic high-density print (thick raised ink)",
    "reflective": "ultra-realistic reflective print (retroreflective, subtle shine)",
    "foil": "ultra-realistic foil print (metallic foil transfer)",
    "glitter": "ultra-realistic glitter print (sparkly particles)",
    "neon": "ultra-realistic neon ink print (very bright colors)",
    "glow": "ultra-realistic glow-in-the-dark print (photoluminescent ink)",
    "rubber_print": "ultra-realistic rubber print (soft-touch raised ink)",
    "water_based": "ultra-realistic water-based ink print (matte, absorbed)",
    "plastisol": "ultra-realistic plastisol ink print (slight thickness, opaque)",
}


def _build_scene_block(scene_mode: str, model_gender: str, source_kind: str) -> str:
    if scene_mode == "product_only":
        return """
SCENE RULES:
- Keep the first image as a product-only image.
- Do NOT add a person, model, mannequin, arms, hands, or body.
- Preserve the original framing, product shape, and product presentation.
- Do NOT redesign the scene.
- Keep the target placement area clearly visible.
""".strip()

    gender_map = {
        "male": "male fashion model",
        "female": "female fashion model",
        "neutral": "fashion model",
    }
    model_text = gender_map.get(model_gender, "fashion model")

    extra_text_rules = ""
    if (source_kind or "").strip().lower() == "text":
        extra_text_rules = """
- Keep the pose simple and natural so the applied text remains readable.
- Avoid extreme folds, twisting, stretching, or aggressive fabric distortion over the design area.
- Do NOT sacrifice text readability for realism.
""".strip()

    base = f"""
SCENE RULES:
- Present the product worn by a realistic {model_text}.
- The result must look like a real commercial fashion photograph, not AI art.
- Keep the garment itself consistent with the first image.
- Do NOT redesign the garment, and do NOT change the cut, fit, silhouette, sleeve shape, collar, hem, or material.
- Use professional studio lighting, soft realistic shadows, clean styling, and natural body proportions.
- Frame the subject like an ecommerce apparel photoshoot.
- Keep the target placement area clearly visible and unobstructed.
- Do NOT crop out the application area.
- Preserve realistic posture, fabric drape, and clothing tension on the body.
""".strip()

    if extra_text_rules:
        return base + "\n" + extra_text_rules
    return base


def _build_material_block(application: str, source_kind: str) -> str:
    kind = (source_kind or "").strip().lower()

    if application == "embroidery":
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

    if application in {
        "screen_print",
        "dtf",
        "dtg",
        "heat_transfer",
        "sublimation",
        "flex",
        "flock",
        "puff_print",
        "high_density",
        "reflective",
        "foil",
        "glitter",
        "neon",
        "glow",
        "rubber_print",
        "water_based",
        "plastisol",
    }:
        if kind == "text":
            return f"""
PRINT TEXT REALISM:
- Make the {application} look physically realistic for the garment material.
- Keep the text fully readable at normal viewing distance.
- Apply only mild believable warping over the text area.
- Preserve realistic lighting, fabric texture, and shadow interaction.
- Avoid smeared, melted, detached, distorted, or unreadable text.
- Use strong contrast between text and garment.
""".strip()

        return f"""
PRINT REALISM:
- Make the {application} look physically realistic for the garment material.
- The design must conform to folds, curvature, stretching, and fabric tension.
- Slightly warp the design with the garment surface in a believable real-world way.
- Preserve realistic lighting, surface texture, and shadow interaction.
- Avoid floating, sticker-like, or detached appearance.
""".strip()

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
- Make this a close-up shot focused ONLY on the target sleeve area.
- Do NOT show the full body. Avoid showing the face. Avoid showing the whole torso.
- The sleeve should fill most of the frame.
- The application must sit below the shoulder seam and above the sleeve cuff.
- The application must NOT touch the collar/neckline.
- Do NOT mirror, flip, or swap garment/person orientation.
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
- If the model is facing the camera, the wearer's right sleeve will usually appear on the LEFT side of the image.
- Preserve the wearer's true anatomical side.
- The non-target sleeve must remain blank.
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
- If the model is facing the camera, the wearer's left sleeve will usually appear on the RIGHT side of the image.
- Preserve the wearer's true anatomical side.
- The non-target sleeve must remain blank.
""".strip()

    return ""


def _build_source_fidelity_block(source_kind: str, source_text: str) -> str:
    if (source_kind or "").strip().lower() == "text":
        st = (source_text or "").strip()

        return f"""
STRICT TEXT FIDELITY (CRITICAL):
- The text to apply is EXACTLY: "{st}"
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
- Do NOT generate fake letters or approximate letter-like shapes.
- Do NOT merge letters into abstract forms.
- The text must be fully legible at normal viewing distance.

COLOR & VISIBILITY:
- The text color must clearly contrast with the garment.
- If the garment is white or light, use black or near-black thread/ink.
- If the garment is dark, use white or light gray thread/ink.
- NEVER use same-color-on-same-color.
- Ensure strong visual separation between text and fabric.

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

    return """
STRICT LOGO FIDELITY:
- Do NOT modify, redraw, restyle, reinterpret, simplify, enhance, replace, or regenerate the logo.
- Preserve the exact shape, spacing, layout, colors, proportions, edges, and all design details.
- Use the provided logo only.
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
- Keep the entire text inside the sleeve panel boundaries.
""".strip()

    if placement_key in {"left_sleeve", "wearer_left_sleeve"}:
        return """
POSITION ANCHOR:
- Anchor the design at the center of the wearer's left sleeve panel.
- Keep a clear margin from the shoulder seam above and the cuff below.
- Keep the entire text inside the sleeve panel boundaries.
""".strip()

    return ""

def build_nanobanana_prompt(inputs: PromptInputs) -> str:
    placement = PLACEMENT_HINTS.get(inputs.placement, inputs.placement)
    application = APPLICATION_HINTS.get(inputs.application, inputs.application)

    scene_block = _build_scene_block(
        scene_mode=inputs.scene_mode,
        model_gender=inputs.model_gender,
        source_kind=inputs.source_kind,
    )
    focus_block = _build_focus_block(inputs.placement)
    side_block = _build_side_disambiguation_block(inputs.placement)
    material_block = _build_material_block(inputs.application, inputs.source_kind)
    negative_block = _build_negative_block(inputs.source_kind)
    fidelity_block = _build_source_fidelity_block(inputs.source_kind, inputs.source_text)
    surface_block = _build_surface_conformity_block(inputs.source_kind)
    sleeve_exclusion_block = _build_sleeve_exclusion_block(inputs.placement)

    orientation_priority_block = ""
    if inputs.placement in {"right_sleeve", "left_sleeve"}:
        orientation_priority_block = """
SLEEVE ORIENTATION PRIORITY:
- Sleeve placements always refer to the WEARER'S anatomical side.
- Viewer perspective must never override the wearer's true left/right side.
""".strip()

    return f"""
Use the first image as the base product reference and the second image as the source design.

TASK:
Apply the design from the second image EXACTLY as provided as {application} {placement}
on the product in the first image ("{inputs.product_title}").

{fidelity_block}

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

{focus_block}

{side_block}

{orientation_priority_block}

{sleeve_exclusion_block}

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
