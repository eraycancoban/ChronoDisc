"""
Unit and Integration Tests for ChronoDisc
Tests 100% Lossless Roundtrip, PNG Metadata, CLI & Reference Mode.
"""

import os
import sys
import tempfile
import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chronodisc as cd
from main import encode_audio_to_disc, decode_disc_to_audio


def test_lossless_roundtrip_synthetic():
    """
    Verifies that 100,000 random audio samples are losslessly preserved
    with 0 mismatches and 0 amplitude difference.
    """
    total_samples = 100000
    r0 = 50.0
    pitch = 2.0

    # Random stereo 16-bit audio
    audio_orig = np.random.randint(-32768, 32767, (total_samples, 2), dtype=np.int16)
    samples_u8 = cd.audio_i16_to_samples_u8(audio_orig)

    # Encode
    canvas = cd.encode_disc(samples_u8, r0=r0, pitch=pitch, mode="lossless")

    # Decode
    samples_rec_u8 = cd.decode_disc(canvas, total_samples=total_samples, r0=r0, pitch=pitch, mode="lossless")
    audio_rec = cd.samples_u8_to_audio_i16(samples_rec_u8)

    # Verify bit-for-bit identity
    assert np.array_equal(audio_orig, audio_rec), "Lossless roundtrip failed to produce identical audio!"

    report = cd.verify_lossless(audio_orig, audio_rec)
    assert report["is_identical"] is True
    assert report["mismatched_values"] == 0
    assert report["max_difference"] == 0


def test_png_metadata_roundtrip():
    """
    Verifies PNG metadata embedding and auto-detection.
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        samples_u8 = np.random.randint(0, 256, (10000, 4), dtype=np.uint8)
        canvas = cd.encode_disc(samples_u8, r0=40.0, pitch=2.5, mode="lossless")
        meta = cd.create_png_metadata(
            total_samples=10000,
            sample_rate=44100,
            channels=2,
            pitch=2.5,
            r0=40.0,
            mode="lossless",
            title="Test Track"
        )
        img = Image.fromarray(canvas, "RGBA")
        img.save(tmp_path, format="PNG", pnginfo=meta)

        read_meta = cd.read_png_metadata(tmp_path)
        assert read_meta["total_samples"] == 10000
        assert read_meta["sample_rate"] == 44100
        assert abs(read_meta["pitch"] - 2.5) < 1e-3
        assert abs(read_meta["r0"] - 40.0) < 1e-3
        assert read_meta["mode"] == "lossless"
        assert read_meta["title"] == "Test Track"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_backward_compatible_functions():
    """
    Verifies that main.py functions encode_audio_to_disc and decode_disc_to_audio work as expected.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = os.path.join(tmpdir, "input.wav")
        png_path = os.path.join(tmpdir, "disc.png")
        out_wav = os.path.join(tmpdir, "output.wav")

        # Create dummy WAV
        sr = 44100
        t = np.linspace(0, 0.2, int(sr * 0.2), endpoint=False)
        sig = (np.sin(2 * np.pi * 440 * t) * 20000).astype(np.int16)
        stereo = np.column_stack([sig, sig])
        cd.save_audio_file(wav_path, stereo, sample_rate=sr)

        # Run encode
        encode_audio_to_disc(wav_path, png_path, canvas_size=0)
        assert os.path.exists(png_path)

        # Run decode
        decode_disc_to_audio(png_path, out_wav)
        assert os.path.exists(out_wav)

        # Verify
        report = cd.verify_lossless(wav_path, out_wav)
        assert report["is_identical"] is True


def test_reference_mode_execution():
    """
    Verifies that Section 5 reference mode executes correctly.
    """
    samples_u8 = np.random.randint(0, 256, (5000, 4), dtype=np.uint8)
    canvas = cd.encode_disc(samples_u8, r0=50.0, pitch=2.0, mode="reference")
    rec = cd.decode_disc(canvas, total_samples=5000, r0=50.0, pitch=2.0, mode="reference")
    assert rec.shape == (5000, 4)
