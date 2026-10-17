"""
ChronoDisc: Optical Vinyl Signal Architecture (Rev 1.0.4)
Main Entry Point & Universal CLI / GUI Launcher.
"""

import sys
import os
import argparse
import numpy as np
from PIL import Image

import chronodisc as cd
from chronodisc.metadata import create_png_metadata, read_png_metadata


try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def encode_audio_to_disc(wav_path: str, output_png: str, canvas_size: int = 2000,
                         r0: float = 50.0, pitch: float = 2.0, mode: str = "lossless",
                         add_center_label: bool = True):
    """
    Encodes a stereo 16-bit WAV audio file into a ChronoDisc 32-bit RGBA PNG.
    Maintains backward compatibility with original main.py signature.
    """
    samples_u8, _, meta = cd.load_audio_file(wav_path)
    total_samples = len(samples_u8)

    # Use specified canvas_size or auto-calculate if <= 0
    if canvas_size <= 0:
        actual_size = cd.calculate_recommended_canvas_size(total_samples, r0, pitch)
    else:
        actual_size = canvas_size

    canvas = cd.encode_disc(samples_u8, size=actual_size, r0=r0, pitch=pitch, mode=mode)

    if add_center_label and r0 >= 30:
        title = os.path.splitext(os.path.basename(wav_path))[0]
        canvas = cd.render_center_label(canvas, r0, title=title, style="hologram")

    # Save with embedded lossless metadata
    png_meta = create_png_metadata(
        total_samples=total_samples,
        sample_rate=meta["sample_rate"],
        channels=meta["channels"],
        pitch=pitch,
        r0=r0,
        mode=mode,
        title=os.path.basename(wav_path)
    )

    img = Image.fromarray(canvas, "RGBA")
    img.save(output_png, format="PNG", pnginfo=png_meta)
    print(f"[OK] ChronoDisc PNG produced: {output_png} ({actual_size}x{actual_size}, {total_samples:,} samples)")


def decode_disc_to_audio(png_path: str, output_wav: str,
                         total_samples: int = 0,
                         canvas_size: int = 2000,
                         framerate: int = 44100,
                         r0: float = 50.0,
                         pitch: float = 2.0,
                         mode: str = "lossless"):
    """
    Decodes a ChronoDisc RGBA PNG back into a 16-bit stereo PCM WAV file.
    Maintains backward compatibility with original main.py signature.
    """
    meta = read_png_metadata(png_path)
    if total_samples <= 0:
        total_samples = meta["total_samples"]
    if framerate == 44100 and meta["sample_rate"] > 0:
        framerate = meta["sample_rate"]
    if pitch == 2.0 and meta["pitch"] > 0:
        pitch = meta["pitch"]
    if r0 == 50.0 and meta["r0"] > 0:
        r0 = meta["r0"]
    if mode == "lossless" and "mode" in meta:
        mode = meta["mode"]

    img = Image.open(png_path).convert("RGBA")
    canvas = np.array(img)

    recovered_samples = cd.decode_disc(canvas, total_samples=total_samples, r0=r0, pitch=pitch, mode=mode)
    cd.save_audio_file(output_wav, recovered_samples, sample_rate=framerate)
    print(f"[OK] Audio successfully decoded: {output_wav} ({total_samples:,} samples, {framerate} Hz)")


def launch_gui():
    """
    Launches the PySide6 desktop GUI application.
    """
    from PySide6.QtWidgets import QApplication
    from chronodisc.gui import ChronoDiscMainWindow

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationName("ChronoDisc")

    window = ChronoDiscMainWindow()
    window.show()
    sys.exit(app.exec())


def main():
    parser = argparse.ArgumentParser(
        description="ChronoDisc: Optical Vinyl Signal Architecture (Rev 1.0.4)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: gui
    subparsers.add_parser("gui", help="Launch interactive Virtual Turntable GUI app (Default)")

    # Command: encode
    p_enc = subparsers.add_parser("encode", help="Encode audio WAV/MP3 to ChronoDisc PNG")
    p_enc.add_argument("input", help="Source audio file path")
    p_enc.add_argument("-o", "--output", default="chronodisc.png", help="Output PNG path (default: chronodisc.png)")
    p_enc.add_argument("--size", type=int, default=0, help="Canvas size in px (0 for auto)")
    p_enc.add_argument("--pitch", type=float, default=2.0, help="Track pitch delta r in px (default: 2.0)")
    p_enc.add_argument("--r0", type=float, default=50.0, help="Inner radius in px (default: 50.0)")
    p_enc.add_argument("--mode", choices=["lossless", "reference"], default="lossless", help="Steganography mode")

    # Command: decode
    p_dec = subparsers.add_parser("decode", help="Decode ChronoDisc PNG to audio WAV")
    p_dec.add_argument("input", help="Input ChronoDisc PNG path")
    p_dec.add_argument("-o", "--output", default="decoded.wav", help="Output WAV path (default: decoded.wav)")
    p_dec.add_argument("-n", "--samples", type=int, default=0, help="Total samples (0 to auto-detect from metadata)")
    p_dec.add_argument("--pitch", type=float, default=2.0, help="Track pitch delta r in px (default: 2.0)")
    p_dec.add_argument("--r0", type=float, default=50.0, help="Inner radius in px (default: 50.0)")

    # Command: verify
    p_ver = subparsers.add_parser("verify", help="Verify lossless bit parity between original audio and ChronoDisc PNG")
    p_ver.add_argument("original", help="Original audio WAV file")
    p_ver.add_argument("disc", help="Encoded ChronoDisc PNG")

    args = parser.parse_args()

    if args.command == "encode":
        encode_audio_to_disc(
            wav_path=args.input,
            output_png=args.output,
            canvas_size=args.size,
            r0=args.r0,
            pitch=args.pitch,
            mode=args.mode
        )
    elif args.command == "decode":
        decode_disc_to_audio(
            png_path=args.input,
            output_wav=args.output,
            total_samples=args.samples,
            r0=args.r0,
            pitch=args.pitch
        )
    elif args.command == "verify":
        meta = read_png_metadata(args.disc)
        img = Image.open(args.disc).convert("RGBA")
        canvas = np.array(img)
        rec_samples = cd.decode_disc(canvas, total_samples=meta["total_samples"], r0=meta["r0"], pitch=meta["pitch"], mode=meta["mode"])
        report = cd.verify_lossless(args.original, rec_samples)
        print("=" * 60)
        print("CHRONODISC LOSSLESS FIDELITY REPORT")
        print("=" * 60)
        print(f"Status:            {'[PASS] 100.0% LOSSLESS BIT MATCH' if report['is_identical'] else 'DIFF DETECTED'}")
        print(f"Total Values:      {report['total_values']:,}")
        print(f"Mismatches:        {report['mismatched_values']:,} ({100.0 - report['match_percentage']:.4f}%)")
        print(f"Max Amplitude Err: {report['max_difference']}")
        print(f"SNR:               {report['snr_db']:.2f} dB")
        print(f"PSNR:              {report['psnr_db']:.2f} dB")
        print("=" * 60)
    else:
        # Default action: Launch Desktop GUI
        launch_gui()


if __name__ == "__main__":
    main()