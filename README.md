# ChronoDisc: Optical Vinyl Signal Architecture

[![Specification](https://img.shields.io/badge/Specification-Rev_1.0.4-blue.svg)](file:///c:/Users/Eray/Desktop/Projects/ChronoDisc)
[![Fidelity](https://img.shields.io/badge/Fidelity-100%25_Lossless-brightgreen.svg)](file:///c:/Users/Eray/Desktop/Projects/ChronoDisc)
[![Sample_Rate](https://img.shields.io/badge/Sample_Rate-44.1_kHz_CLV-cyan.svg)](file:///c:/Users/Eray/Desktop/Projects/ChronoDisc)
[![Format](https://img.shields.io/badge/Format-PCM_WAV_↔_32--bit_RGBA-purple.svg)](file:///c:/Users/Eray/Desktop/Projects/ChronoDisc)

**ChronoDisc** is an optical audio storage, visualization, and real-time playback system that losslessly maps dual-channel digital audio signals (PCM WAV) into 32-bit RGBA pixel channels arranged in a 2-dimensional Archimedean spiral geometry exported as PNG.

It synthesizes the continuous spiral track topology of traditional analog vinyl records with the digital precision of optical CD standards via a software-driven **Virtual Optical Needle** engine.

---

## 🌟 Key Features

1. **100% Lossless Visual-to-Audio Steganography**:
   - Stereo 16-bit PCM CD-standard audio ($44.1\text{ kHz}$) is mapped directly to 4 color channels ($R, G, B, A$):
     - **Left Channel (L)**: $R = \text{sample}_L\ \&\ 0\text{xFF}$, $G = \text{sample}_L \gg 8$
     - **Right Channel (R)**: $B = \text{sample}_R\ \&\ 0\text{xFF}$, $A = \text{sample}_R \gg 8$
     - **Temporal Duration**: 1 Pixel = 1 Complete Stereo Sample ($\Delta t = 1 / 44,100\text{ s} \approx 22.67\ \mu s$)
2. **Constant Linear Velocity (CLV) Spiral Geometry**:
   - Polar Trajectory: $r(\theta) = r_0 + b \cdot \theta$, where $b = \Delta r / (2\pi)$
   - Tangential Arc Length: $\Delta s = r \cdot \Delta\theta \approx 1.0\text{ px}$
   - Dynamic Canvas Sizing: $R_{max} = \sqrt{r_0^2 + (N \cdot \text{pitch} / \pi)}$ calculated ahead of rasterization to prevent boundary overflow
3. **Interactive Virtual Turntable Player**:
   - Spinning vinyl platter with realistic anisotropic light reflections and micro-grooves
   - **Virtual Optical Needle**: Animated tonearm with a glowing optical laser pickup head targeting the sample groove
   - **Interactive Needle Dropping**: Click or drag anywhere on the vinyl disc to seek to that exact sample instant in $O(1)$ time
   - Low-latency real-time audio playback powered by `sounddevice`
4. **Optical Decoder DAC Telemetry HUD**:
   - **Microscopic Sensor View**: High-magnification optical lens displaying the individual RGBA pixels sliding under the laser eye
   - **Real-Time Byte Demuxer**: Live byte extraction readout ($R, G, B, A$) and calculated voltage voltages
   - **Live Stereo Vector Oscilloscope & Peak VU Meters**
   - **CLV Telemetry**: Real-time radius $r$, angle $\theta$, current RPM, and linear velocity $v$
5. **Numba JIT Acceleration**:
   - Over 40,000,000 samples/sec rasterization performance (encodes 1,000,000 samples in ~25 ms)
   - Graceful pure Python / NumPy fallback if Numba is unavailable
6. **Embedded PNG Metadata**:
   - Stores sample rate, channels, bit depth, total sample count, pitch, $r_0$, mode, track title, and artist directly in PNG `tEXt` chunks.
7. **YouTube Music Downloader & Optical Importer (yt-dlp based)**:
   - Download audio streams directly from YouTube into lossless WAV, 320k MP3, FLAC, or video formats using `yt-dlp` and `ffmpeg`.
   - Real-time download progress tracking with cleaned speed, ETA, and percentage readouts.
   - 1-click **"Load into Studio"** or **"Directly Spin on Turntable"** workflow to instantly convert downloaded YouTube tracks into ChronoDisc optical vinyl discs!

---

## 🚀 Quick Start

### 1. Launch the Interactive Desktop App
```bash
python main.py
# or
python main.py gui
```

### 2. Command-Line Interface (CLI)

#### Encode Audio to ChronoDisc PNG:
```bash
python main.py encode song.wav -o chronodisc.png --pitch 2.0 --r0 50.0
```

#### Decode ChronoDisc PNG back to Audio WAV:
```bash
python main.py decode chronodisc.png -o decoded.wav
```

#### Verify Bit-for-Bit Parity:
```bash
python main.py verify song.wav chronodisc.png
```

---

## 🐍 Python API Reference

```python
import chronodisc as cd

# Load audio file (supports WAV, MP3, FLAC, etc.)
samples_u8, audio_i16, meta = cd.load_audio_file("song.wav")

# Encode to ChronoDisc RGBA matrix
canvas = cd.encode_disc(samples_u8, r0=50.0, pitch=2.0, mode="lossless")

# Render center holographic label (optional, placed inside r < r0)
canvas = cd.render_center_label(canvas, r0=50.0, title="My Track", style="hologram")

# Decode back to audio
rec_samples = cd.decode_disc(canvas, total_samples=len(samples_u8), r0=50.0, pitch=2.0)

# Verify lossless parity
report = cd.verify_lossless(samples_u8, rec_samples)
print("Is 100% Identical:", report["is_identical"])  # True
print("Mismatches:", report["mismatched_values"])    # 0
print("Max Bit Difference:", report["max_difference"])# 0
print("SNR:", report["snr_db"])                       # inf dB
```

### Backward-Compatible API:
```python
from main import encode_audio_to_disc, decode_disc_to_audio

encode_audio_to_disc("input.wav", "disc.png", canvas_size=2000)
decode_disc_to_audio("disc.png", "output.wav", total_samples=176400)
```

---

## 🧪 Running Tests
```bash
python -m pytest tests/
```

All unit tests verify:
- 100% bit-for-bit lossless roundtrip
- PNG metadata preservation
- Backward-compatible functions
- Reference mode execution

