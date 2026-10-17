"""
ChronoDisc Encoder View (ChronoDisc Studio)
Audio to Lossless 32-bit RGBA Archimedean Spiral Rasterizer Studio.
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
    QGroupBox, QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit, QCheckBox,
    QProgressBar, QMessageBox, QFrame, QSplitter
)

from ..audio import load_audio_file
from ..core import encode_disc, calculate_recommended_canvas_size, calculate_max_radius
from ..metadata import create_png_metadata
from ..visuals import render_center_label


class EncoderView(QWidget):
    """
    Studio panel for converting digital audio into ChronoDisc optical vinyl PNGs.
    """
    # Signal emitted when user wants to play newly encoded disc on the Turntable
    send_to_turntable = Signal(np.ndarray, int, float, float, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_path: Optional[str] = None
        self.samples_u8: Optional[np.ndarray] = None
        self.audio_meta: Optional[dict] = None
        self.encoded_canvas: Optional[np.ndarray] = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---------------- LEFT PANEL: Controls ----------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # 1. Source Audio File
        audio_group = QGroupBox("SOURCE AUDIO FILE")
        audio_layout = QVBoxLayout(audio_group)

        browse_row = QHBoxLayout()
        self.btn_browse = QPushButton("📁 Browse Audio (WAV / MP3 / FLAC)...")
        self.btn_browse.clicked.connect(self._on_browse_audio)
        browse_row.addWidget(self.btn_browse)

        self.btn_load_demo = QPushButton("🎵 Load Demo Track")
        self.btn_load_demo.clicked.connect(self._on_load_demo)
        browse_row.addWidget(self.btn_load_demo)
        audio_layout.addLayout(browse_row)

        self.lbl_file_info = QLabel("No audio file loaded.")
        self.lbl_file_info.setStyleSheet("color: #94A3B8; font-size: 12px;")
        audio_layout.addWidget(self.lbl_file_info)

        left_layout.addWidget(audio_group)

        # 2. Geometric & Optical Parameters
        params_group = QGroupBox("GEOMETRIC MODEL & CLV PARAMETERS")
        params_layout = QVBoxLayout(params_group)

        # Pitch
        p_row = QHBoxLayout()
        p_row.addWidget(QLabel("Track Pitch (Δr ≥ 2.0 px):"))
        self.spin_pitch = QDoubleSpinBox()
        self.spin_pitch.setRange(2.0, 10.0)
        self.spin_pitch.setSingleStep(0.1)
        self.spin_pitch.setValue(2.0)
        self.spin_pitch.valueChanged.connect(self._update_sizing_preview)
        p_row.addWidget(self.spin_pitch)
        params_layout.addLayout(p_row)

        # R0
        r_row = QHBoxLayout()
        r_row.addWidget(QLabel("Initial Radius (r0):"))
        self.spin_r0 = QDoubleSpinBox()
        self.spin_r0.setRange(20.0, 500.0)
        self.spin_r0.setSingleStep(5.0)
        self.spin_r0.setValue(50.0)
        self.spin_r0.valueChanged.connect(self._update_sizing_preview)
        r_row.addWidget(self.spin_r0)
        params_layout.addLayout(r_row)

        # Mode
        m_row = QHBoxLayout()
        m_row.addWidget(QLabel("Steganography Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Lossless Strict (100% Collision-Free)", "Reference CLV (Spec Rev 1.0.4)"])
        m_row.addWidget(self.combo_mode)
        params_layout.addLayout(m_row)

        # Canvas Size
        self.chk_auto_size = QCheckBox("Dynamic Canvas Sizing (R_max calculation)")
        self.chk_auto_size.setChecked(True)
        self.chk_auto_size.toggled.connect(self._update_sizing_preview)
        params_layout.addWidget(self.chk_auto_size)

        self.lbl_sizing_calc = QLabel("Canvas Dimensions: 0 x 0 px")
        self.lbl_sizing_calc.setStyleSheet("color: #00E5FF; font-family: Consolas;")
        params_layout.addWidget(self.lbl_sizing_calc)

        # Center Label Style
        cl_row = QHBoxLayout()
        cl_row.addWidget(QLabel("Center Label Style:"))
        self.combo_label_style = QComboBox()
        self.combo_label_style.addItems(["Holographic Vinyl Badge", "Minimal Dark", "None (Transparent)"])
        cl_row.addWidget(self.combo_label_style)
        params_layout.addLayout(cl_row)

        left_layout.addWidget(params_group)

        # 3. Track Metadata
        meta_group = QGroupBox("PNG EMBEDDED METADATA")
        meta_layout = QVBoxLayout(meta_group)

        t_row = QHBoxLayout()
        t_row.addWidget(QLabel("Title:"))
        self.txt_title = QLineEdit("ChronoDisc Master Track")
        t_row.addWidget(self.txt_title)
        meta_layout.addLayout(t_row)

        a_row = QHBoxLayout()
        a_row.addWidget(QLabel("Artist:"))
        self.txt_artist = QLineEdit("Optical Vinyl Engine")
        a_row.addWidget(self.txt_artist)
        meta_layout.addLayout(a_row)

        left_layout.addWidget(meta_group)

        # 4. Action Buttons
        self.btn_encode = QPushButton("⚡ Generate ChronoDisc PNG")
        self.btn_encode.setObjectName("accentButton")
        self.btn_encode.setFixedHeight(40)
        self.btn_encode.clicked.connect(self._on_encode_clicked)
        left_layout.addWidget(self.btn_encode)

        act_row = QHBoxLayout()
        self.btn_save = QPushButton("💾 Save Lossless PNG...")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._on_save_png)
        act_row.addWidget(self.btn_save)

        self.btn_to_turntable = QPushButton("🎧 Send to Turntable")
        self.btn_to_turntable.setEnabled(False)
        self.btn_to_turntable.setObjectName("playButton")
        self.btn_to_turntable.clicked.connect(self._on_send_to_turntable)
        act_row.addWidget(self.btn_to_turntable)
        left_layout.addLayout(act_row)

        self.lbl_encode_status = QLabel("")
        self.lbl_encode_status.setStyleSheet("color: #10B981; font-weight: bold;")
        left_layout.addWidget(self.lbl_encode_status)

        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # ---------------- RIGHT PANEL: Image Preview ----------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_group = QGroupBox("CHRONODISC PREVIEW (32-BIT RGBA MATRIX)")
        p_layout = QVBoxLayout(preview_group)
        p_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_preview = QLabel("Encode an audio file to view the ChronoDisc matrix.")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet("color: #64748B; border: 2px dashed #242B38; border-radius: 8px; min-width: 400px; min-height: 400px;")
        p_layout.addWidget(self.lbl_preview)

        right_layout.addWidget(preview_group)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 5)
        main_layout.addWidget(splitter)

    def _on_browse_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a);;All Files (*.*)"
        )
        if path:
            self._load_audio(path)

    def _on_load_demo(self):
        demo_path = os.path.abspath("demo_track.wav")
        if os.path.exists(demo_path):
            self._load_audio(demo_path)
        else:
            QMessageBox.warning(self, "Demo Not Found", "demo_track.wav was not found in the workspace.")

    def _load_audio(self, path: str):
        try:
            self.samples_u8, _, self.audio_meta = load_audio_file(path)
            self.audio_path = path
            fname = os.path.basename(path)
            dur = self.audio_meta["duration_sec"]
            n = self.audio_meta["total_samples"]

            self.lbl_file_info.setText(
                f"Loaded: <b>{fname}</b> | Duration: {dur:.2f}s | "
                f"Samples: {n:,} (44.1 kHz 16-bit Stereo)"
            )
            self._update_sizing_preview()
            self.lbl_encode_status.setText("Audio loaded. Ready to encode.")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load audio: {str(e)}")

    def load_audio_file_path(self, path: str, title: Optional[str] = None):
        self._load_audio(path)
        if title:
            self.txt_title.setText(title)

    def _update_sizing_preview(self):
        if self.samples_u8 is None:
            return

        n = len(self.samples_u8)
        pitch = self.spin_pitch.value()
        r0 = self.spin_r0.value()

        rmax = calculate_max_radius(n, r0, pitch)
        size = calculate_recommended_canvas_size(n, r0, pitch)

        self.lbl_sizing_calc.setText(
            f"Canvas: {size} x {size} px  |  R_max: {rmax:.1f} px  |  Data Pixels: {n:,}"
        )

    def _on_encode_clicked(self):
        if self.samples_u8 is None:
            QMessageBox.warning(self, "No Audio", "Please load an audio file first.")
            return

        n = len(self.samples_u8)
        pitch = self.spin_pitch.value()
        r0 = self.spin_r0.value()
        size = calculate_recommended_canvas_size(n, r0, pitch)
        mode = "reference" if self.combo_mode.currentIndex() == 1 else "lossless"

        t0 = time.perf_counter()
        canvas = encode_disc(self.samples_u8, size=size, r0=r0, pitch=pitch, mode=mode)

        # Center label styling
        label_choice = self.combo_label_style.currentIndex()
        if label_choice == 0:
            canvas = render_center_label(canvas, r0, self.txt_title.text(), self.txt_artist.text(), style="hologram")
        elif label_choice == 1:
            canvas = render_center_label(canvas, r0, self.txt_title.text(), self.txt_artist.text(), style="minimal")

        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000.0

        self.encoded_canvas = canvas
        self.btn_save.setEnabled(True)
        self.btn_to_turntable.setEnabled(True)

        self.lbl_encode_status.setText(
            f"✓ ChronoDisc generated in {elapsed_ms:.1f} ms! ({size}x{size} RGBA)"
        )

        # Update preview
        h, w, ch = canvas.shape
        qimg = QImage(canvas.data, w, h, ch * w, QImage.Format.Format_RGBA8888)
        pix = QPixmap.fromImage(qimg)
        scaled_pix = pix.scaled(440, 440, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.lbl_preview.setPixmap(scaled_pix)

    def _on_save_png(self):
        if self.encoded_canvas is None or self.samples_u8 is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save ChronoDisc PNG", "chronodisc_output.png",
            "PNG Image (*.png)"
        )
        if not path:
            return

        pitch = self.spin_pitch.value()
        r0 = self.spin_r0.value()
        mode = "reference" if self.combo_mode.currentIndex() == 1 else "lossless"

        meta = create_png_metadata(
            total_samples=len(self.samples_u8),
            pitch=pitch,
            r0=r0,
            mode=mode,
            title=self.txt_title.text(),
            artist=self.txt_artist.text()
        )

        img = Image.fromarray(self.encoded_canvas, "RGBA")
        img.save(path, format="PNG", pnginfo=meta)
        QMessageBox.information(self, "Saved", f"ChronoDisc saved losslessly to:\n{path}")

    def _on_send_to_turntable(self):
        if self.encoded_canvas is not None and self.samples_u8 is not None:
            pitch = self.spin_pitch.value()
            r0 = self.spin_r0.value()
            title = self.txt_title.text()
            self.send_to_turntable.emit(self.encoded_canvas, len(self.samples_u8), r0, pitch, title)

