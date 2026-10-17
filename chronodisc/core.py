"""
ChronoDisc Core Engine
Implementation of the Archimedean Constant Linear Velocity (CLV) Spiral
Rasterizer and Lossless 32-bit RGBA Audio Steganography Engine.
Specification Revision: 1.0.4
"""

import math
from typing import Tuple, Optional, Callable
import numpy as np

# Optional Numba acceleration
try:
    import numba
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False


def calculate_max_radius(total_samples: int, r0: float = 50.0, pitch: float = 2.0) -> float:
    """
    Computes theoretical maximum outer radius R_max based on track length and pitch.
    Formula: R_max = sqrt(r0^2 + (N * pitch / pi))
    """
    if total_samples <= 0:
        return r0
    return float(np.sqrt(r0**2 + (total_samples * pitch / np.pi)))


def calculate_recommended_canvas_size(total_samples: int, r0: float = 50.0, pitch: float = 2.0, margin: int = 24) -> int:
    """
    Computes minimum square canvas dimension (size x size) to avoid clipping.
    Ensures size is an even integer.
    """
    rmax = calculate_max_radius(total_samples, r0, pitch)
    size = int(math.ceil((rmax + margin) * 2))
    if size % 2 != 0:
        size += 1
    return max(size, 256)


def estimate_sample_from_coordinates(x: float, y: float, cx: float, cy: float,
                                    total_samples: int, r0: float = 50.0, pitch: float = 2.0) -> int:
    """
    O(1) analytical inverse mapping from disc Cartesian coordinates (x, y)
    to audio sample index n for interactive needle dropping / scrubbing.
    """
    dx = x - cx
    dy = y - cy
    r = math.sqrt(dx * dx + dy * dy)

    if r <= r0:
        return 0

    # From CLV relation: n = pi * (r^2 - r0^2) / pitch
    approx_n = int((np.pi * (r * r - r0 * r0)) / pitch)
    return max(0, min(total_samples - 1, approx_n))


# ---------------------------------------------------------------------------
# Numba JIT accelerated rasterizers
# ---------------------------------------------------------------------------

if HAS_NUMBA:
    @numba.njit(fastmath=True)
    def _encode_disc_lossless_jit(samples: np.ndarray, canvas: np.ndarray,
                                  size: int, r0: float, pitch: float):
        cx = size // 2
        cy = size // 2
        b = pitch / (2.0 * np.pi)
        theta = 0.0
        n = len(samples)
        prev_x = -999999
        prev_y = -999999

        for i in range(n):
            r = r0 + b * theta
            x = int(np.round(cx + r * np.cos(theta)))
            y = int(np.round(cy + r * np.sin(theta)))

            while x == prev_x and y == prev_y:
                theta += 0.5 / (r if r > 1.0 else 1.0)
                r = r0 + b * theta
                x = int(np.round(cx + r * np.cos(theta)))
                y = int(np.round(cy + r * np.sin(theta)))

            prev_x = x
            prev_y = y

            if 0 <= x < size and 0 <= y < size:
                canvas[y, x, 0] = samples[i, 0]
                canvas[y, x, 1] = samples[i, 1]
                canvas[y, x, 2] = samples[i, 2]
                canvas[y, x, 3] = samples[i, 3]

            theta += 1.0 / (r if r > 1.0 else 1.0)

    @numba.njit(fastmath=True)
    def _decode_disc_lossless_jit(canvas: np.ndarray, out_samples: np.ndarray,
                                  size: int, r0: float, pitch: float):
        cx = size // 2
        cy = size // 2
        b = pitch / (2.0 * np.pi)
        theta = 0.0
        n = len(out_samples)
        prev_x = -999999
        prev_y = -999999

        for i in range(n):
            r = r0 + b * theta
            x = int(np.round(cx + r * np.cos(theta)))
            y = int(np.round(cy + r * np.sin(theta)))

            while x == prev_x and y == prev_y:
                theta += 0.5 / (r if r > 1.0 else 1.0)
                r = r0 + b * theta
                x = int(np.round(cx + r * np.cos(theta)))
                y = int(np.round(cy + r * np.sin(theta)))

            prev_x = x
            prev_y = y

            if 0 <= x < size and 0 <= y < size:
                out_samples[i, 0] = canvas[y, x, 0]
                out_samples[i, 1] = canvas[y, x, 1]
                out_samples[i, 2] = canvas[y, x, 2]
                out_samples[i, 3] = canvas[y, x, 3]

            theta += 1.0 / (r if r > 1.0 else 1.0)

    @numba.njit(fastmath=True)
    def _encode_disc_reference_jit(samples: np.ndarray, canvas: np.ndarray,
                                   size: int, r0: float, pitch: float):
        cx = size // 2
        cy = size // 2
        b = pitch / (2.0 * np.pi)
        theta = 0.0
        n = len(samples)

        for i in range(n):
            r = r0 + b * theta
            x = int(cx + r * np.cos(theta))
            y = int(cy + r * np.sin(theta))
            if 0 <= x < size and 0 <= y < size:
                canvas[y, x, 0] = samples[i, 0]
                canvas[y, x, 1] = samples[i, 1]
                canvas[y, x, 2] = samples[i, 2]
                canvas[y, x, 3] = samples[i, 3]
            theta += 1.0 / (r if r > 1.0 else 1.0)

    @numba.njit(fastmath=True)
    def _decode_disc_reference_jit(canvas: np.ndarray, out_samples: np.ndarray,
                                   size: int, r0: float, pitch: float):
        cx = size // 2
        cy = size // 2
        b = pitch / (2.0 * np.pi)
        theta = 0.0
        n = len(out_samples)

        for i in range(n):
            r = r0 + b * theta
            x = int(cx + r * np.cos(theta))
            y = int(cy + r * np.sin(theta))
            if 0 <= x < size and 0 <= y < size:
                out_samples[i, 0] = canvas[y, x, 0]
                out_samples[i, 1] = canvas[y, x, 1]
                out_samples[i, 2] = canvas[y, x, 2]
                out_samples[i, 3] = canvas[y, x, 3]
            theta += 1.0 / (r if r > 1.0 else 1.0)


# ---------------------------------------------------------------------------
# Pure Python / NumPy fallbacks
# ---------------------------------------------------------------------------

def _encode_disc_lossless_py(samples: np.ndarray, canvas: np.ndarray,
                             size: int, r0: float, pitch: float,
                             progress_callback: Optional[Callable[[float], None]] = None):
    cx = size // 2
    cy = size // 2
    b = pitch / (2.0 * math.pi)
    theta = 0.0
    n = len(samples)
    prev_pos = None
    step_report = max(1, n // 100)

    for i in range(n):
        r = r0 + b * theta
        x = int(round(cx + r * math.cos(theta)))
        y = int(round(cy + r * math.sin(theta)))

        while (x, y) == prev_pos:
            theta += 0.5 / max(r, 1.0)
            r = r0 + b * theta
            x = int(round(cx + r * math.cos(theta)))
            y = int(round(cy + r * math.sin(theta)))

        prev_pos = (x, y)
        if 0 <= x < size and 0 <= y < size:
            canvas[y, x] = samples[i]

        theta += 1.0 / max(r, 1.0)
        if progress_callback and i % step_report == 0:
            progress_callback(i / n)


def _decode_disc_lossless_py(canvas: np.ndarray, out_samples: np.ndarray,
                             size: int, r0: float, pitch: float,
                             progress_callback: Optional[Callable[[float], None]] = None):
    cx = size // 2
    cy = size // 2
    b = pitch / (2.0 * math.pi)
    theta = 0.0
    n = len(out_samples)
    prev_pos = None
    step_report = max(1, n // 100)

    for i in range(n):
        r = r0 + b * theta
        x = int(round(cx + r * math.cos(theta)))
        y = int(round(cy + r * math.sin(theta)))

        while (x, y) == prev_pos:
            theta += 0.5 / max(r, 1.0)
            r = r0 + b * theta
            x = int(round(cx + r * math.cos(theta)))
            y = int(round(cy + r * math.sin(theta)))

        prev_pos = (x, y)
        if 0 <= x < size and 0 <= y < size:
            out_samples[i] = canvas[y, x]

        theta += 1.0 / max(r, 1.0)
        if progress_callback and i % step_report == 0:
            progress_callback(i / n)


def _encode_disc_reference_py(samples: np.ndarray, canvas: np.ndarray,
                              size: int, r0: float, pitch: float,
                              progress_callback: Optional[Callable[[float], None]] = None):
    cx = size // 2
    cy = size // 2
    b = pitch / (2.0 * math.pi)
    theta = 0.0
    n = len(samples)
    step_report = max(1, n // 100)

    for i in range(n):
        r = r0 + b * theta
        x = int(cx + r * math.cos(theta))
        y = int(cy + r * math.sin(theta))
        if 0 <= x < size and 0 <= y < size:
            canvas[y, x] = samples[i]
        theta += 1.0 / max(r, 1.0)
        if progress_callback and i % step_report == 0:
            progress_callback(i / n)


def _decode_disc_reference_py(canvas: np.ndarray, out_samples: np.ndarray,
                              size: int, r0: float, pitch: float,
                              progress_callback: Optional[Callable[[float], None]] = None):
    cx = size // 2
    cy = size // 2
    b = pitch / (2.0 * math.pi)
    theta = 0.0
    n = len(out_samples)
    step_report = max(1, n // 100)

    for i in range(n):
        r = r0 + b * theta
        x = int(cx + r * math.cos(theta))
        y = int(cy + r * math.sin(theta))
        if 0 <= x < size and 0 <= y < size:
            out_samples[i] = canvas[y, x]
        theta += 1.0 / max(r, 1.0)
        if progress_callback and i % step_report == 0:
            progress_callback(i / n)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def encode_disc(samples: np.ndarray,
                size: Optional[int] = None,
                r0: float = 50.0,
                pitch: float = 2.0,
                mode: str = "lossless",
                progress_callback: Optional[Callable[[float], None]] = None) -> np.ndarray:
    """
    Renders 16-bit stereo PCM audio samples into a 32-bit RGBA disc image.
    
    Args:
        samples: np.ndarray of shape (N, 4) with uint8 data (R, G, B, A)
        size: Dimension of square canvas. If None, auto-calculated.
        r0: Initial inner radius in pixels.
        pitch: Radial track pitch (delta r) in pixels (>= 2.0).
        mode: "lossless" (default, 100% collision-free) or "reference" (Spec Rev 1.0.4 loop).
        progress_callback: Optional callback receiving float progress in [0, 1].

    Returns:
        np.ndarray: (size, size, 4) uint8 RGBA image canvas.
    """
    n = len(samples)
    if size is None:
        size = calculate_recommended_canvas_size(n, r0, pitch)

    canvas = np.zeros((size, size, 4), dtype=np.uint8)

    if HAS_NUMBA:
        if mode == "reference":
            _encode_disc_reference_jit(samples, canvas, size, float(r0), float(pitch))
        else:
            _encode_disc_lossless_jit(samples, canvas, size, float(r0), float(pitch))
        if progress_callback:
            progress_callback(1.0)
    else:
        if mode == "reference":
            _encode_disc_reference_py(samples, canvas, size, float(r0), float(pitch), progress_callback)
        else:
            _encode_disc_lossless_py(samples, canvas, size, float(r0), float(pitch), progress_callback)

    return canvas


def decode_disc(canvas: np.ndarray,
                total_samples: int,
                r0: float = 50.0,
                pitch: float = 2.0,
                mode: str = "lossless",
                progress_callback: Optional[Callable[[float], None]] = None) -> np.ndarray:
    """
    Decodes an RGBA disc image back into uint8 (N, 4) audio samples.
    """
    size = canvas.shape[0]
    out_samples = np.zeros((total_samples, 4), dtype=np.uint8)

    if HAS_NUMBA:
        if mode == "reference":
            _decode_disc_reference_jit(canvas, out_samples, size, float(r0), float(pitch))
        else:
            _decode_disc_lossless_jit(canvas, out_samples, size, float(r0), float(pitch))
        if progress_callback:
            progress_callback(1.0)
    else:
        if mode == "reference":
            _decode_disc_reference_py(canvas, out_samples, size, float(r0), float(pitch), progress_callback)
        else:
            _decode_disc_lossless_py(canvas, out_samples, size, float(r0), float(pitch), progress_callback)

    return out_samples


def get_trajectory_point(index: int, total_samples: int,
                         size: int, r0: float = 50.0, pitch: float = 2.0,
                         mode: str = "lossless") -> Tuple[float, float, float, float]:
    """
    Computes polar (r, theta) and Cartesian (x, y) coordinates for a given sample index.
    Returns: (r, theta, x, y)
    """
    cx = size / 2.0
    cy = size / 2.0
    b = pitch / (2.0 * math.pi)

    # For fast needle trajectory animation, analytical formula gives exact/near-exact location
    r = math.sqrt(r0**2 + (index * pitch / math.pi))
    theta = (r - r0) / b
    x = cx + r * math.cos(theta)
    y = cy + r * math.sin(theta)
    return r, theta, x, y

