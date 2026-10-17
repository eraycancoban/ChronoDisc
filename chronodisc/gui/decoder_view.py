"""
ChronoDisc Decoder & Lossless Verification Suite View
Optical Matrix Decoding, WAV Audio Reconstruction, and Mathematical Parity Verification.
"""

import os
import time
from typing import Optional
import numpy as np
from PIL import Image

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QGroupBox, QSpinBox, QDoubleSpinBox, QProgressBar, QMessageBox,
    QFrame, QSplitter, QGridLayout
)

from ..core import decode_disc
from ..audio import save_audio_file, verify_lossless, samples_u8_to_audio_i16
from ..metadata import read_png_metadata
from ..player import ChronoDiscPlayer


class DecoderView(QWidget):
    """
    Panel for decoding ChronoDisc PNGs back into WAV audio and verifying lossless parity.
    """
    send_to_turntable = Signal(np.ndarray, int, float, float, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.disc_path: Optional[str] = None
        self.disc_canvas: Optional[np.ndarray] = None
        self.decoded_samples: Optional[np.ndarray] = None
        self.metadata: Optional[dict] = None

        self.audio_player = ChronoDiscPlayer()

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---------------- LEFT PANEL: Decoder & Verification ----------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # 1. Load ChronoDisc Image
        file_group = QGroupBox("CHRONODISC PNG SOURCE")
        file_layout = QVBoxLayout(file_group)

        row_btn = QHBoxLayout()
        self.btn_open_png = QPushButton("📁 Open ChronoDisc PNG...")
        self.btn_open_png.clicked.connect(self._on_open_png)
        row_btn.addWidget(self.btn_open_png)

        self.btn_open_demo_png = QPushButton("💿 Open Demo Disc")
        self.btn_open_demo_png.clicked.connect(self._on_open_demo_png)
        row_btn.addWidget(self.btn_open_demo_png)
        file_layout.addLayout(row_btn)

        self.lbl_disc_name = QLabel("No ChronoDisc PNG loaded.")
        self.lbl_disc_name.setStyleSheet("color: #94A3B8;")
        file_layout.addWidget(self.lbl_disc_name)

        left_layout.addWidget(file_group)

        # 2. Detected Metadata Table
        meta_group = QGroupBox("DETECTED OPTICAL METADATA")
        grid = QGridLayout(meta_group)
        grid.setSpacing(8)

        lbl_font = QFont("Consolas", 9)
        val_font = QFont("Consolas", 10, QFont.Weight.Bold)

        labels = [
            ("Track Title:", "title", 0, 0),
            ("Sample Rate:", "sample_rate", 0, 2),
            ("Total Samples:", "total_samples", 1, 0),
            ("Track Pitch Δr:", "pitch", 1, 2),
            ("Start Radius r0:", "r0", 2, 0),
            ("Stego Mode:", "mode", 2, 2),
            ("Duration:", "duration", 3, 0),
            ("Matrix Size:", "size", 3, 2),
        ]

        self.meta_labels = {}
        for title, key, r, c in labels:
            t_lbl = QLabel(title)
            t_lbl.setFont(lbl_font)
            t_lbl.setStyleSheet("color: #64748B;")
            grid.addWidget(t_lbl, r, c)

            v_lbl = QLabel("-")
            v_lbl.setFont(val_font)
            v_lbl.setStyleSheet("color: #00E5FF;")
            self.meta_labels[key] = v_lbl
            grid.addWidget(v_lbl, r, c + 1)

        left_layout.addWidget(meta_group)

        # 3. Decode Actions
        action_group = QGroupBox("OPTICAL DECODING & AUDIO EXPORT")
        act_layout = QVBoxLayout(action_group)

        self.btn_decode = QPushButton("⚡ Decode to Audio (WAV)")
        self.btn_decode.setObjectName("accentButton")
        self.btn_decode.setFixedHeight(38)
        self.btn_decode.setEnabled(False)
        self.btn_decode.clicked.connect(self._on_decode_clicked)
        act_layout.addWidget(self.btn_decode)

        export_row = QHBoxLayout()
        self.btn_export_wav = QPushButton("💾 Export 16-bit WAV...")
        self.btn_export_wav.setEnabled(False)
        self.btn_export_wav.clicked.connect(self._on_export_wav)
        export_row.addWidget(self.btn_export_wav)

        self.btn_to_turntable = QPushButton("🎧 Send to Turntable")
        self.btn_to_turntable.setEnabled(False)
        self.btn_to_turntable.setObjectName("playButton")
        self.btn_to_turntable.clicked.connect(self._on_send_to_turntable)
        export_row.addWidget(self.btn_to_turntable)
        act_layout.addLayout(export_row)

        self.lbl_decode_status = QLabel("")
        self.lbl_decode_status.setStyleSheet("color: #10B981; font-weight: bold;")
        act_layout.addWidget(self.lbl_decode_status)

        left_layout.addWidget(action_group)

        # 4. Lossless Verification Suite
        verif_group = QGroupBox("100% LOSSLESS VERIFICATION SUITE")
        v_layout = QVBoxLayout(verif_group)

        self.btn_verify = QPushButton("🔬 Compare with Original Audio File (Verify Bit Parity)...")
        self.btn_verify.setEnabled(False)
        self.btn_verify.clicked.connect(self._on_verify_lossless)
        v_layout.addWidget(self.btn_verify)

        self.badge_box = QFrame()
        self.badge_box.setStyleSheet("background-color: #0E1015; border-radius: 6px; padding: 10px;")
        b_layout = QVBoxLayout(self.badge_box)
        self.lbl_badge = QLabel("Awaiting verification test...")
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_badge.setStyleSheet("color: #64748B;")
        b_layout.addWidget(self.lbl_badge)

        self.lbl_verif_stats = QLabel("")
        self.lbl_verif_stats.setFont(QFont("Consolas", 9))
        self.lbl_verif_stats.setStyleSheet("color: #94A3B8;")
        b_layout.addWidget(self.lbl_verif_stats)

        v_layout.addWidget(self.badge_box)
        left_layout.addWidget(verif_group)

        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # ---------------- RIGHT PANEL: Matrix Preview ----------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_group = QGroupBox("LOADED DISC MATRIX")
        p_layout = QVBoxLayout(preview_group)
        p_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_preview = QLabel("Open a ChronoDisc PNG to view disc matrix.")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet("color: #64748B; border: 2px dashed #242B38; border-radius: 8px; min-width: 400px; min-height: 400px;")
        p_layout.addWidget(self.lbl_preview)

        right_layout.addWidget(preview_group)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 5)
        main_layout.addWidget(splitter)

    def _on_open_png(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open ChronoDisc PNG", "", "PNG Image (*.png);;All Files (*.*)"
        )
        if path:
            self._load_disc_file(path)

    def _on_open_demo_png(self):
        demo_path = os.path.abspath("demo_disc.png")
        if os.path.exists(demo_path):
            self._load_disc_file(demo_path)
        else:
            QMessageBox.warning(self, "Demo Not Found", "demo_disc.png was not found in the workspace.")

    def _load_disc_file(self, path: str):
        try:
            self.disc_path = path
            meta = read_png_metadata(path)
            self.metadata = meta

            # Read image array
            img = Image.open(path).convert("RGBA")
            self.disc_canvas = np.array(img)

            self.lbl_disc_name.setText(f"Loaded: <b>{os.path.basename(path)}</b>")
            self.meta_labels["title"].setText(str(meta["title"]))
            self.meta_labels["sample_rate"].setText(f"{meta['sample_rate']:,} Hz")
            self.meta_labels["total_samples"].setText(f"{meta['total_samples']:,}")
            self.meta_labels["pitch"].setText(f"{meta['pitch']:.2f} px")
            self.meta_labels["r0"].setText(f"{meta['r0']:.1f} px")
            self.meta_labels["mode"].setText(str(meta["mode"]))
            self.meta_labels["duration"].setText(f"{meta['duration_seconds']:.2f}s")
            self.meta_labels["size"].setText(f"{meta['width']} x {meta['height']}")

            self.btn_decode.setEnabled(True)
            self.btn_to_turntable.setEnabled(True)

            # Update preview
            h, w, ch = self.disc_canvas.shape
            qimg = QImage(self.disc_canvas.data, w, h, ch * w, QImage.Format.Format_RGBA8888)
            pix = QPixmap.fromImage(qimg)
            scaled_pix = pix.scaled(440, 440, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_preview.setPixmap(scaled_pix)

            self.lbl_decode_status.setText("ChronoDisc loaded. Ready to decode.")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load ChronoDisc PNG: {str(e)}")

    def _on_decode_clicked(self):
        if self.disc_canvas is None or self.metadata is None:
            return

        total_samples = self.metadata["total_samples"]
        r0 = self.metadata["r0"]
        pitch = self.metadata["pitch"]
        mode = self.metadata.get("mode", "lossless")

        t0 = time.perf_counter()
        out_samples = decode_disc(
            self.disc_canvas,
            total_samples=total_samples,
            r0=r0,
            pitch=pitch,
            mode=mode
        )
        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000.0

        self.decoded_samples = out_samples
        self.btn_export_wav.setEnabled(True)
        self.btn_verify.setEnabled(True)

        self.lbl_decode_status.setText(
            f"✓ Decoded {total_samples:,} samples in {elapsed_ms:.1f} ms! (Audio ready)"
        )

    def _on_export_wav(self):
        if self.decoded_samples is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Audio WAV", "decoded_audio.wav", "WAV Audio (*.wav)"
        )
        if not path:
            return

        sr = self.metadata.get("sample_rate", 44100) if self.metadata else 44100
        save_audio_file(path, self.decoded_samples, sample_rate=sr)
        QMessageBox.information(self, "Exported", f"Decoded audio saved to:\n{path}")

    def _on_verify_lossless(self):
        if self.decoded_samples is None:
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Original Audio to Compare", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*.*)"
        )
        if not path:
            return

        try:
            report = verify_lossless(path, self.decoded_samples)

            if report["is_identical"]:
                self.lbl_badge.setText("🏆 100.0% LOSSLESS VERIFIED (BIT-FOR-BIT IDENTICAL)")
                self.lbl_badge.setStyleSheet("color: #10B981; font-weight: bold;")
            elif report["match_percentage"] > 95.0:
                self.lbl_badge.setText(f"✓ HIGH FIDELITY MATCH ({report['match_percentage']:.2f}%)")
                self.lbl_badge.setStyleSheet("color: #00E5FF; font-weight: bold;")
            else:
                self.lbl_badge.setText(f"⚠ DIFFERENCE DETECTED ({report['match_percentage']:.2f}% match)")
                self.lbl_badge.setStyleSheet("color: #F59E0B; font-weight: bold;")

            self.lbl_verif_stats.setText(
                f"Mismatches: {report['mismatched_values']:,} / {report['total_values']:,}  |  "
                f"Max Bit Diff: {report['max_difference']}  |  "
                f"SNR: {report['snr_db']:.1f} dB  |  PSNR: {report['psnr_db']:.1f} dB"
            )
        except Exception as e:
            QMessageBox.critical(self, "Verification Error", f"Comparison failed: {str(e)}")

    def _on_send_to_turntable(self):
        if self.disc_canvas is not None and self.metadata is not None:
            r0 = self.metadata["r0"]
            pitch = self.metadata["pitch"]
            total_samples = self.metadata["total_samples"]
            title = self.metadata.get("title", "Decoded Track")
            self.send_to_turntable.emit(self.disc_canvas, total_samples, r0, pitch, title)

