"""
ChronoDisc Main Window
Master application window integrating the Virtual Turntable Player,
Encoder Studio, and Decoder/Verifier Suite.
"""

import os
import math
from typing import Optional
import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QSlider, QFrame, QFileDialog, QMessageBox
)

from ..player import ChronoDiscPlayer
from ..core import decode_disc, estimate_sample_from_coordinates
from ..metadata import read_png_metadata
from .turntable_widget import TurntableWidget
from .dac_monitor_widget import DacMonitorWidget
from .encoder_view import EncoderView
from .decoder_view import DecoderView
from .downloader_tab import DownloaderTab
from .styles import DARK_THEME_QSS
import chronodisc as cd


class ChronoDiscMainWindow(QMainWindow):
    """
    Top-level application window for ChronoDisc.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChronoDisc: Optical Vinyl Signal Architecture (Rev 1.0.4)")
        self.resize(1180, 780)
        self.setMinimumSize(960, 640)

        # Apply dark cyber-vinyl stylesheet
        self.setStyleSheet(DARK_THEME_QSS)

        # Core player engine
        self.player = ChronoDiscPlayer(sample_rate=44100)
        self.player.on_playback_end = self._on_playback_ended

        # Active disc state
        self.current_disc_canvas: Optional[np.ndarray] = None
        self.current_r0: float = 50.0
        self.current_pitch: float = 2.0
        self.current_total_samples: int = 0
        self.current_title: str = "ChronoDisc Track"

        self._init_ui()

        # Telemetry update timer (30 Hz for smooth HUD refresh)
        self.hud_timer = QTimer(self)
        self.hud_timer.timeout.connect(self._update_hud_telemetry)
        self.hud_timer.start(33)

        # Auto-load demo disc if available
        self._try_load_demo_on_startup()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        # Top Header Bar
        header = QFrame()
        header.setStyleSheet("background-color: #12151C; border-radius: 8px; padding: 6px 12px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(6, 4, 6, 4)

        title_lbl = QLabel("CHRONODISC")
        title_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #00E5FF; letter-spacing: 1px;")
        h_layout.addWidget(title_lbl)

        sub_lbl = QLabel("OPTICAL VINYL SIGNAL ARCHITECTURE (PCM WAV ↔ 32-BIT RGBA)")
        sub_lbl.setFont(QFont("Consolas", 10))
        sub_lbl.setStyleSheet("color: #64748B;")
        h_layout.addWidget(sub_lbl)

        h_layout.addStretch()

        btn_demo = QPushButton("💿 Quick Load Demo Disc")
        btn_demo.clicked.connect(self._on_quick_load_demo)
        h_layout.addWidget(btn_demo)

        root_layout.addWidget(header)

        # Main Tab Widget
        self.tabs = QTabWidget(self)

        # Tab 1: Virtual Turntable Player
        self.tab_player = QWidget()
        self._init_player_tab(self.tab_player)
        self.tabs.addTab(self.tab_player, "🎧 Virtual Turntable Deck")

        # Tab 2: ChronoDisc Studio (Encoder)
        self.encoder_view = EncoderView(self)
        self.encoder_view.send_to_turntable.connect(self._on_load_disc_into_turntable)
        self.tabs.addTab(self.encoder_view, "💿 ChronoDisc Studio (Encoder)")

        # Tab 3: Optical Decoder & Verifier
        self.decoder_view = DecoderView(self)
        self.decoder_view.send_to_turntable.connect(self._on_load_disc_into_turntable)
        self.tabs.addTab(self.decoder_view, "🔍 Decoder & Lossless Verifier")

        # Tab 4: YouTube Downloader
        self.downloader_tab = DownloaderTab(self)
        self.downloader_tab.load_into_studio_requested.connect(self._on_downloader_load_into_studio)
        self.downloader_tab.direct_turntable_requested.connect(self._on_downloader_direct_turntable)
        self.tabs.addTab(self.downloader_tab, "📥 YouTube Downloader")

        root_layout.addWidget(self.tabs)

    def _init_player_tab(self, parent_widget: QWidget):
        tab_layout = QHBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(14)

        # Left Column: Turntable Platter + Transport Controls
        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        # Interactive Turntable Platter
        self.turntable = TurntableWidget(self)
        self.turntable.seek_requested.connect(self._on_turntable_seek)
        left_col.addWidget(self.turntable, stretch=1)

        # Transport Controls Panel
        ctrl_panel = QFrame()
        ctrl_panel.setStyleSheet("background-color: #12151C; border-radius: 8px; padding: 10px;")
        cp_layout = QVBoxLayout(ctrl_panel)
        cp_layout.setSpacing(6)

        # Timeline Seekbar & Timestamp Row
        seek_row = QHBoxLayout()
        self.lbl_time_cur = QLabel("00:00.00")
        self.lbl_time_cur.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.lbl_time_cur.setStyleSheet("color: #00E5FF;")
        seek_row.addWidget(self.lbl_time_cur)

        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.sliderMoved.connect(self._on_slider_seek)
        seek_row.addWidget(self.slider_seek, stretch=1)

        self.lbl_time_total = QLabel("00:00.00")
        self.lbl_time_total.setFont(QFont("Consolas", 10))
        self.lbl_time_total.setStyleSheet("color: #64748B;")
        seek_row.addWidget(self.lbl_time_total)
        cp_layout.addLayout(seek_row)

        # Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_play = QPushButton("▶ PLAY")
        self.btn_play.setObjectName("playButton")
        self.btn_play.setFixedSize(100, 36)
        self.btn_play.clicked.connect(self._on_play_toggle)
        btn_row.addWidget(self.btn_play)

        self.btn_stop = QPushButton("⏹ STOP")
        self.btn_stop.setFixedSize(80, 36)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        btn_row.addWidget(self.btn_stop)

        self.lbl_track_title = QLabel("No Disc Loaded")
        self.lbl_track_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_track_title.setStyleSheet("color: #F1F5F9;")
        btn_row.addWidget(self.lbl_track_title, stretch=1)

        # Volume control
        btn_row.addWidget(QLabel("Vol:"))
        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(100)
        self.slider_vol.setFixedWidth(80)
        self.slider_vol.valueChanged.connect(self._on_volume_changed)
        btn_row.addWidget(self.slider_vol)

        # Loop button
        self.btn_loop = QPushButton("🔁 Loop")
        self.btn_loop.setCheckable(True)
        self.btn_loop.toggled.connect(self._on_loop_toggled)
        btn_row.addWidget(self.btn_loop)

        cp_layout.addLayout(btn_row)
        left_col.addWidget(ctrl_panel)

        tab_layout.addLayout(left_col, stretch=5)

        # Right Column: Optical DAC HUD
        right_col = QVBoxLayout()
        self.dac_monitor = DacMonitorWidget(self)
        right_col.addWidget(self.dac_monitor)
        tab_layout.addLayout(right_col, stretch=4)

    def _on_load_disc_into_turntable(self, canvas: np.ndarray, total_samples: int,
                                     r0: float, pitch: float, title: str):
        """
        Loads a ChronoDisc into the Turntable Deck and prepares playback.
        """
        self.current_disc_canvas = canvas
        self.current_total_samples = total_samples
        self.current_r0 = r0
        self.current_pitch = pitch
        self.current_title = title

        # Decode disc samples for audio playback
        out_samples = decode_disc(canvas, total_samples=total_samples, r0=r0, pitch=pitch)
        self.player.load(out_samples, sample_rate=44100)

        # Update Turntable widget
        self.turntable.load_disc_image(canvas, total_samples=total_samples, r0=r0, pitch=pitch)
        self.lbl_track_title.setText(f"💿 {title}")

        # Update time total
        dur = total_samples / 44100.0
        mins = int(dur // 60)
        secs = dur % 60
        self.lbl_time_total.setText(f"{mins:02d}:{secs:05.2f}")

        # Switch to Turntable Tab
        self.tabs.setCurrentIndex(0)
        self.btn_play.setText("▶ PLAY")

    def _on_quick_load_demo(self):
        demo_disc_path = os.path.abspath("demo_disc.png")
        if os.path.exists(demo_disc_path):
            self._load_disc_from_file(demo_disc_path)
        else:
            QMessageBox.information(self, "No Demo", "demo_disc.png was not found. You can generate one in the Studio tab!")

    def _try_load_demo_on_startup(self):
        demo_disc_path = os.path.abspath("demo_disc.png")
        if os.path.exists(demo_disc_path):
            self._load_disc_from_file(demo_disc_path)

    def _load_disc_from_file(self, path: str):
        from PIL import Image
        meta = read_png_metadata(path)
        img = Image.open(path).convert("RGBA")
        canvas = np.array(img)
        self._on_load_disc_into_turntable(
            canvas=canvas,
            total_samples=meta["total_samples"],
            r0=meta["r0"],
            pitch=meta["pitch"],
            title=meta.get("title", "Demo Track")
        )

    def _on_play_toggle(self):
        if self.player.is_playing:
            self.player.pause()
            self.btn_play.setText("▶ PLAY")
            self.turntable.set_playback_state(False, self.player.position)
        else:
            self.player.play()
            self.btn_play.setText("⏸ PAUSE")
            self.turntable.set_playback_state(True, self.player.position)

    def _on_stop_clicked(self):
        self.player.stop()
        self.btn_play.setText("▶ PLAY")
        self.turntable.set_playback_state(False, 0)
        self.slider_seek.setValue(0)
        self.lbl_time_cur.setText("00:00.00")

    def _on_turntable_seek(self, sample_idx: int):
        self.player.seek_sample(sample_idx)
        self.turntable.set_playback_state(self.player.is_playing, sample_idx)

    def _on_slider_seek(self, value: int):
        if self.current_total_samples > 0:
            target_idx = int((value / 1000.0) * self.current_total_samples)
            self.player.seek_sample(target_idx)
            self.turntable.set_playback_state(self.player.is_playing, target_idx)

    def _on_volume_changed(self, value: int):
        self.player.set_volume(value / 100.0)

    def _on_loop_toggled(self, checked: bool):
        self.player.set_loop(checked)

    def _on_playback_ended(self):
        self.btn_play.setText("▶ PLAY")
        self.turntable.set_playback_state(False, 0)

    def _update_hud_telemetry(self):
        if self.current_total_samples <= 0:
            return

        tele = self.player.get_current_telemetry()
        pos = tele["position"]
        dur = tele["duration_sec"]
        cur_t = tele["time_sec"]

        # Update Turntable
        self.turntable.set_playback_state(tele["is_playing"], pos)

        # Update Seek slider
        if dur > 0 and not self.slider_seek.isSliderDown():
            norm_val = int((pos / float(self.current_total_samples)) * 1000)
            self.slider_seek.setValue(norm_val)

        # Update time label
        mins = int(cur_t // 60)
        secs = cur_t % 60
        self.lbl_time_cur.setText(f"{mins:02d}:{secs:05.2f}")

        # Update DAC HUD
        self.dac_monitor.update_telemetry(
            telemetry=tele,
            disc_canvas=self.current_disc_canvas,
            r0=self.current_r0,
            pitch=self.current_pitch
        )

    def _on_downloader_load_into_studio(self, filepath: str, title: str):
        self.encoder_view.load_audio_file_path(filepath, title=title)
        self.tabs.setCurrentWidget(self.encoder_view)

    def _on_downloader_direct_turntable(self, filepath: str, title: str):
        try:
            samples_u8, _, meta = cd.load_audio_file(filepath)
            n = len(samples_u8)
            r0 = 50.0
            pitch = 2.0
            size = cd.calculate_recommended_canvas_size(n, r0, pitch)
            canvas = cd.encode_disc(samples_u8, size=size, r0=r0, pitch=pitch, mode="lossless")
            canvas = cd.render_center_label(canvas, r0, title=title or "YouTube Stream", style="hologram")

            self._on_load_disc_into_turntable(canvas, n, r0, pitch, title or "YouTube Stream")
            self.player.play()
            self.btn_play.setText("⏸ PAUSE")
            self.tabs.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "Turntable Load Error", f"Failed to encode and play track: {str(e)}")

