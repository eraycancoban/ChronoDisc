"""
ChronoDisc Audio Engine
Audio I/O, resampling, 16-bit PCM formatting, and Lossless Fidelity Verification.
"""

import os
import wave
from typing import Tuple, Dict, Any, Union
import numpy as np

# Optional PyAV for multi-format decoding (MP3, FLAC, AAC, etc.)
try:
    import av
    HAS_AV = True
except ImportError:
    HAS_AV = False

try:
    import scipy.signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def load_audio_file(file_path: str, target_sr: int = 44100) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Loads any audio file (WAV, MP3, FLAC, etc.) and formats it as CD-standard
    44.1 kHz 16-bit Stereo Signed PCM.

    Returns:
        samples_u8: np.ndarray shape (N, 4) uint8 (R, G, B, A)
        audio_i16: np.ndarray shape (N, 2) int16
        metadata: Dict with original & output parameters
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    # Fast path for 16-bit stereo WAV via standard wave module
    if ext == ".wav":
        try:
            with wave.open(file_path, "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_bytes = wf.readframes(n_frames)

            if n_channels == 2 and sampwidth == 2 and framerate == target_sr:
                audio_i16 = np.frombuffer(raw_bytes, dtype="<i2").reshape(-1, 2)
                samples_u8 = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(-1, 4)
                meta = {
                    "sample_rate": framerate,
                    "channels": 2,
                    "bits": 16,
                    "total_samples": len(audio_i16),
                    "duration_sec": len(audio_i16) / framerate,
                    "resampled": False
                }
                return samples_u8, audio_i16, meta
        except Exception:
            # Fall through to PyAV or scipy fallback
            pass

    # Universal audio reader via PyAV
    if HAS_AV:
        container = av.open(file_path)
        stream = next(s for s in container.streams if s.type == "audio")
        
        # Resampler to target_sr, stereo, s16 format
        resampler = av.AudioResampler(format="s16", layout="stereo", rate=target_sr)
        
        frames_data = []
        for packet in container.demux(stream):
            for frame in packet.decode():
                resampled_frames = resampler.resample(frame)
                for rf in resampled_frames:
                    frames_data.append(rf.to_ndarray().tobytes())
        
        raw_bytes = b"".join(frames_data)
        audio_i16 = np.frombuffer(raw_bytes, dtype="<i2").reshape(-1, 2)
        samples_u8 = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(-1, 4)
        
        meta = {
            "sample_rate": target_sr,
            "channels": 2,
            "bits": 16,
            "total_samples": len(audio_i16),
            "duration_sec": len(audio_i16) / target_sr,
            "resampled": stream.rate != target_sr or stream.channels != 2
        }
        return samples_u8, audio_i16, meta

    # Fallback for WAV using wave module + scipy resample if needed
    with wave.open(file_path, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)

    # Convert to float array
    if sampwidth == 2:
        raw_audio = np.frombuffer(raw_bytes, dtype="<i2").reshape(-1, n_channels).astype(np.float32) / 32768.0
    elif sampwidth == 1:
        raw_audio = (np.frombuffer(raw_bytes, dtype=np.uint8).reshape(-1, n_channels).astype(np.float32) - 128.0) / 128.0
    elif sampwidth == 4:
        raw_audio = np.frombuffer(raw_bytes, dtype="<i4").reshape(-1, n_channels).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    # Channel conversion to stereo
    if n_channels == 1:
        stereo_audio = np.column_stack([raw_audio, raw_audio])
    elif n_channels >= 2:
        stereo_audio = raw_audio[:, :2]

    # Resample if sample rate doesn't match
    if framerate != target_sr and HAS_SCIPY:
        num_target_samples = int(len(stereo_audio) * target_sr / framerate)
        stereo_audio = scipy.signal.resample(stereo_audio, num_target_samples)
    
    # Quantize to 16-bit
    clipped = np.clip(stereo_audio, -1.0, 1.0)
    audio_i16 = (clipped * 32767.0).astype(np.int16)
    raw_bytes = audio_i16.tobytes()
    samples_u8 = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(-1, 4)

    meta = {
        "sample_rate": target_sr,
        "channels": 2,
        "bits": 16,
        "total_samples": len(audio_i16),
        "duration_sec": len(audio_i16) / target_sr,
        "resampled": framerate != target_sr
    }
    return samples_u8, audio_i16, meta


def save_audio_file(file_path: str, samples: Union[np.ndarray, bytes], sample_rate: int = 44100):
    """
    Saves audio data to a standard 16-bit stereo PCM WAV file.
    Accepts:
        samples: np.ndarray shape (N, 4) uint8, (N, 2) int16, or raw bytes.
    """
    if isinstance(samples, np.ndarray):
        if samples.dtype == np.uint8 and samples.ndim == 2 and samples.shape[1] == 4:
            pcm_bytes = samples.tobytes()
        elif samples.dtype == np.int16 and samples.ndim == 2 and samples.shape[1] == 2:
            pcm_bytes = samples.tobytes()
        else:
            pcm_bytes = samples.astype(np.int16).tobytes()
    else:
        pcm_bytes = bytes(samples)

    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)


def samples_u8_to_audio_i16(samples_u8: np.ndarray) -> np.ndarray:
    """
    Losslessly converts uint8 (N, 4) RGBA pixel samples to int16 (N, 2) stereo audio.
    """
    return np.frombuffer(samples_u8.tobytes(), dtype="<i2").reshape(-1, 2)


def audio_i16_to_samples_u8(audio_i16: np.ndarray) -> np.ndarray:
    """
    Losslessly converts int16 (N, 2) stereo audio into uint8 (N, 4) RGBA pixel samples.
    """
    return np.frombuffer(audio_i16.tobytes(), dtype=np.uint8).reshape(-1, 4)


def verify_lossless(original: Union[np.ndarray, bytes, str],
                    decoded: Union[np.ndarray, bytes, str]) -> Dict[str, Any]:
    """
    Performs full scientific and bit-for-bit fidelity verification between
    the original audio and the decoded ChronoDisc stream.
    """
    # Load original
    if isinstance(original, str):
        _, orig_i16, _ = load_audio_file(original)
    elif isinstance(original, bytes):
        orig_i16 = np.frombuffer(original, dtype="<i2").reshape(-1, 2)
    elif isinstance(original, np.ndarray) and original.dtype == np.uint8:
        orig_i16 = samples_u8_to_audio_i16(original)
    else:
        orig_i16 = original

    # Load decoded
    if isinstance(decoded, str):
        _, dec_i16, _ = load_audio_file(decoded)
    elif isinstance(decoded, bytes):
        dec_i16 = np.frombuffer(decoded, dtype="<i2").reshape(-1, 2)
    elif isinstance(decoded, np.ndarray) and decoded.dtype == np.uint8:
        dec_i16 = samples_u8_to_audio_i16(decoded)
    else:
        dec_i16 = decoded

    # Align lengths
    n_compare = min(len(orig_i16), len(dec_i16))
    orig_comp = orig_i16[:n_compare]
    dec_comp = dec_i16[:n_compare]

    diff = np.abs(orig_comp.astype(np.int32) - dec_comp.astype(np.int32))
    max_diff = int(np.max(diff)) if n_compare > 0 else 0
    mismatches = int(np.sum(diff > 0))
    total_elements = n_compare * 2

    is_identical = (mismatches == 0) and (len(orig_i16) == len(dec_i16))

    # Signal to Noise Ratio
    signal_power = np.mean(orig_comp.astype(np.float64)**2)
    noise_power = np.mean(diff.astype(np.float64)**2)

    if noise_power == 0:
        snr_db = float("inf")
        psnr_db = float("inf")
    else:
        snr_db = float(10.0 * np.log10(max(signal_power, 1e-12) / noise_power))
        peak_val = 32767.0
        psnr_db = float(20.0 * np.log10(peak_val / np.sqrt(noise_power)))

    return {
        "is_identical": is_identical,
        "total_samples": n_compare,
        "mismatched_values": mismatches,
        "total_values": total_elements,
        "match_percentage": 100.0 * (1.0 - mismatches / max(1, total_elements)),
        "max_difference": max_diff,
        "snr_db": snr_db,
        "psnr_db": psnr_db,
        "length_orig": len(orig_i16),
        "length_dec": len(dec_i16)
    }

