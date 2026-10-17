"""
ChronoDisc: Optical Vinyl Signal Architecture
System Engineering and Data Mapping Specification (Rev 1.0.4)
"""

from .core import (
    encode_disc,
    decode_disc,
    calculate_recommended_canvas_size,
    calculate_max_radius,
    estimate_sample_from_coordinates,
    get_trajectory_point
)
from .audio import (
    load_audio_file,
    save_audio_file,
    verify_lossless,
    samples_u8_to_audio_i16,
    audio_i16_to_samples_u8
)
from .metadata import (
    create_png_metadata,
    read_png_metadata
)
from .player import ChronoDiscPlayer
from .visuals import (
    render_center_label,
    extract_optical_sensor_patch
)

__version__ = "1.0.4"
__author__ = "ChronoDisc Team"

__all__ = [
    "encode_disc",
    "decode_disc",
    "calculate_recommended_canvas_size",
    "calculate_max_radius",
    "estimate_sample_from_coordinates",
    "get_trajectory_point",
    "load_audio_file",
    "save_audio_file",
    "verify_lossless",
    "samples_u8_to_audio_i16",
    "audio_i16_to_samples_u8",
    "create_png_metadata",
    "read_png_metadata",
    "ChronoDiscPlayer",
    "render_center_label",
    "extract_optical_sensor_patch",
]

