"""
ChronoDisc Metadata Engine
Lossless PNG tEXt Chunk Management for Audio Parameters and Stored Metadata.
"""

from typing import Dict, Any, Optional
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import numpy as np


def create_png_metadata(total_samples: int,
                        sample_rate: int = 44100,
                        channels: int = 2,
                        bits_per_sample: int = 16,
                        pitch: float = 2.0,
                        r0: float = 50.0,
                        mode: str = "lossless",
                        title: str = "Untitled Track",
                        artist: str = "Unknown Artist") -> PngInfo:
    """
    Creates a PIL PngInfo object populated with ChronoDisc audio parameters.
    """
    pnginfo = PngInfo()
    pnginfo.add_text("ChronoDisc_Signature", "CHRONODISC_V1")
    pnginfo.add_text("ChronoDisc_Version", "1.0.4")
    pnginfo.add_text("ChronoDisc_SampleRate", str(sample_rate))
    pnginfo.add_text("ChronoDisc_Channels", str(channels))
    pnginfo.add_text("ChronoDisc_BitsPerSample", str(bits_per_sample))
    pnginfo.add_text("ChronoDisc_TotalSamples", str(total_samples))
    pnginfo.add_text("ChronoDisc_Pitch", f"{pitch:.4f}")
    pnginfo.add_text("ChronoDisc_R0", f"{r0:.4f}")
    pnginfo.add_text("ChronoDisc_Mode", str(mode))
    pnginfo.add_text("ChronoDisc_Title", str(title))
    pnginfo.add_text("ChronoDisc_Artist", str(artist))
    return pnginfo


def read_png_metadata(image_path: str) -> Dict[str, Any]:
    """
    Reads metadata from a ChronoDisc PNG image.
    Provides intelligent fallbacks if standard ChronoDisc chunks are missing.
    """
    with Image.open(image_path) as img:
        text = getattr(img, "text", {}) or {}
        width, height = img.size

        # Check for signature
        is_chronodisc = "ChronoDisc_Signature" in text or "ChronoDisc_TotalSamples" in text

        total_samples = int(text.get("ChronoDisc_TotalSamples", 0))
        sample_rate = int(text.get("ChronoDisc_SampleRate", 44100))
        channels = int(text.get("ChronoDisc_Channels", 2))
        bits_per_sample = int(text.get("ChronoDisc_BitsPerSample", 16))
        pitch = float(text.get("ChronoDisc_Pitch", 2.0))
        r0 = float(text.get("ChronoDisc_R0", 50.0))
        mode = text.get("ChronoDisc_Mode", "lossless")
        title = text.get("ChronoDisc_Title", "ChronoDisc Audio Track")
        artist = text.get("ChronoDisc_Artist", "Optical Vinyl Engine")

        # If not tagged, estimate total samples from disc radius
        if total_samples <= 0:
            # Estimate: disc outer radius approx size / 2 - 24
            approx_rmax = max(width // 2 - 24, r0 + 10)
            approx_samples = int((np.pi * (approx_rmax**2 - r0**2)) / pitch)
            total_samples = max(44100, approx_samples)

        return {
            "is_chronodisc": is_chronodisc,
            "version": text.get("ChronoDisc_Version", "1.0.4"),
            "total_samples": total_samples,
            "sample_rate": sample_rate,
            "channels": channels,
            "bits_per_sample": bits_per_sample,
            "pitch": pitch,
            "r0": r0,
            "mode": mode,
            "title": title,
            "artist": artist,
            "width": width,
            "height": height,
            "duration_seconds": total_samples / sample_rate if sample_rate > 0 else 0.0,
        }

