"""
ChronoDisc Visuals Engine
Artistic vinyl record textures, center label generation, and optical sensor patch extraction.
"""

import math
from typing import Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def render_center_label(canvas: np.ndarray,
                        r0: float,
                        title: str = "ChronoDisc Track",
                        artist: str = "Optical Vinyl",
                        style: str = "hologram") -> np.ndarray:
    """
    Renders an authentic center label inside the unused inner circle (r < r0 - 2).
    Because data strictly begins at r >= r0, this has ZERO impact on audio fidelity.
    """
    size = canvas.shape[0]
    cx = size // 2
    cy = size // 2

    # If r0 is too small, skip drawing
    if r0 < 25:
        return canvas

    img = Image.fromarray(canvas, "RGBA")
    draw = ImageDraw.Draw(img)

    label_radius = int(r0 - 2)

    if style == "hologram":
        # Outer border metallic ring
        draw.ellipse([cx - label_radius, cy - label_radius,
                      cx + label_radius, cy + label_radius],
                     fill=(16, 20, 28, 255), outline=(0, 230, 255, 220), width=2)
        
        # Inner decorative gold/cyan accent rings
        r_mid = int(label_radius * 0.75)
        draw.ellipse([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid],
                     outline=(255, 200, 50, 160), width=1)
        
        r_inner = int(label_radius * 0.45)
        draw.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
                     fill=(10, 12, 16, 255), outline=(0, 230, 255, 120), width=1)

        # Center spindle hole
        spindle_r = max(4, int(min(label_radius * 0.15, 8)))
        draw.ellipse([cx - spindle_r, cy - spindle_r,
                      cx + spindle_r, cy + spindle_r],
                     fill=(0, 0, 0, 0), outline=(220, 220, 220, 255), width=1)

        # Micro-text label if radius is large enough
        if label_radius >= 45:
            try:
                font = ImageFont.load_default()
                text_top = "CHRONODISC"
                bbox = draw.textbbox((0, 0), text_top, font=font)
                tw = bbox[2] - bbox[0]
                draw.text((cx - tw // 2, cy - int(label_radius * 0.62)), text_top, fill=(0, 240, 255, 240), font=font)

                text_sub = "44.1k CLV"
                bbox_sub = draw.textbbox((0, 0), text_sub, font=font)
                tw_sub = bbox_sub[2] - bbox_sub[0]
                draw.text((cx - tw_sub // 2, cy + int(label_radius * 0.48)), text_sub, fill=(255, 210, 80, 220), font=font)
            except Exception:
                pass

    elif style == "minimal":
        draw.ellipse([cx - label_radius, cy - label_radius,
                      cx + label_radius, cy + label_radius],
                     fill=(24, 24, 26, 255), outline=(120, 120, 120, 255), width=2)
        spindle_r = 6
        draw.ellipse([cx - spindle_r, cy - spindle_r,
                      cx + spindle_r, cy + spindle_r],
                     fill=(0, 0, 0, 0), outline=(180, 180, 180, 255), width=1)

    return np.array(img)


def extract_optical_sensor_patch(canvas: np.ndarray,
                                 x: int, y: int,
                                 patch_radius: int = 16,
                                 zoom: int = 8) -> np.ndarray:
    """
    Extracts a zoomed patch of pixels centered at (x, y) for the Virtual Optical Needle HUD.
    """
    size = canvas.shape[0]
    x_min = max(0, x - patch_radius)
    x_max = min(size, x + patch_radius + 1)
    y_min = max(0, y - patch_radius)
    y_max = min(size, y + patch_radius + 1)

    # Pad if outside boundaries
    crop_w = patch_radius * 2 + 1
    crop = np.zeros((crop_w, crop_w, 4), dtype=np.uint8)

    src_w = x_max - x_min
    src_h = y_max - y_min

    dest_x = (x_min - (x - patch_radius))
    dest_y = (y_min - (y - patch_radius))

    if src_w > 0 and src_h > 0:
        crop[dest_y:dest_y + src_h, dest_x:dest_x + src_w] = canvas[y_min:y_max, x_min:x_max]

    # Nearest neighbor upscale for pixel-art clarity
    if zoom > 1:
        img = Image.fromarray(crop, "RGBA")
        img = img.resize((crop_w * zoom, crop_w * zoom), Image.Resampling.NEAREST)
        return np.array(img)

    return crop

