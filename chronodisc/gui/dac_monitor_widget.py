"""
ChronoDisc Optical DAC & Signal Telemetry Widget
Microscopic Optical Sensor View, 32-bit RGBA Byte Demuxer HUD, and Live Stereo Oscilloscope.
Specification Section 2 & 3.
"""

import math
from typing import Optional, Tuple
import numpy as np

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient, QLinearGradient,
    QFont, QImage, QPixmap
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout, QFrame
)

from ..visuals import extract_optical_sensor_patch


class MicroscopeLensWidget(QWidget):
    """
    Renders an enlarged circular optical microscope view of the disc pixels
    under the laser pickup head.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self.sensor_patch: Optional[np.ndarray] = None

    def update_patch(self, patch: np.ndarray):
        self.sensor_patch = patch
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        radius = min(cx, cy) - 6

        # Outer bezel
        bezel_grad = QRadialGradient(cx, cy, radius + 4)
        bezel_grad.setColorAt(0.85, QColor(36, 42, 54))
        bezel_grad.setColorAt(1.0, QColor(14, 16, 22))
        painter.setBrush(QBrush(bezel_grad))
        painter.setPen(QPen(QColor(0, 229, 255, 180), 1.5))
        painter.drawEllipse(QPointF(cx, cy), radius + 4, radius + 4)

        # Lens background
        lens_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.setBrush(QBrush(QColor(5, 7, 10)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(lens_rect)

        # Draw zoomed sensor patch clipped to circle
        if self.sensor_patch is not None:
            painter.save()
            # Set circular clip path
            clip_path = painter.clipPath()
            clip_path.addEllipse(lens_rect)
            painter.setClipPath(clip_path)

            ph, pw, _ = self.sensor_patch.shape
            qimg = QImage(self.sensor_patch.data, pw, ph, pw * 4, QImage.Format.Format_RGBA8888)
            pix = QPixmap.fromImage(qimg)
            painter.drawPixmap(lens_rect.toRect(), pix)
            painter.restore()

        # Laser Target Crosshair & Center Aim
        painter.setPen(QPen(QColor(0, 240, 255, 200), 1))
        painter.drawLine(QPointF(cx - 20, cy), QPointF(cx - 4, cy))
        painter.drawLine(QPointF(cx + 4, cy), QPointF(cx + 20, cy))
        painter.drawLine(QPointF(cx, cy - 20), QPointF(cx, cy - 4))
        painter.drawLine(QPointF(cx, cy + 4), QPointF(cx, cy + 20))

        # Target center ring
        painter.setPen(QPen(QColor(0, 240, 255, 220), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), 5, 5)

        # Lens glare sheen
        glare_grad = QLinearGradient(cx - radius, cy - radius, cx + radius, cy + radius)
        glare_grad.setColorAt(0.0, QColor(255, 255, 255, 45))
        glare_grad.setColorAt(0.35, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(glare_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(lens_rect)

        painter.end()


class OscilloscopeWidget(QWidget):
    """
    Renders real-time vector waveform oscilloscope for Left and Right channels.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.waveform: np.ndarray = np.zeros((256, 2), dtype=np.int16)

    def update_waveform(self, chunk: np.ndarray):
        self.waveform = chunk
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        mid_y = h / 2.0

        # Background grid
        painter.fillRect(0, 0, w, h, QColor(10, 12, 16))
        painter.setPen(QPen(QColor(24, 30, 42), 1, Qt.PenStyle.DotLine))
        painter.drawLine(0, int(mid_y), w, int(mid_y))
        painter.drawLine(0, int(mid_y - h * 0.35), w, int(mid_y - h * 0.35))
        painter.drawLine(0, int(mid_y + h * 0.35), w, int(mid_y + h * 0.35))

        n = len(self.waveform)
        if n < 2:
            painter.end()
            return

        dx = w / float(n - 1)

        # Left Channel Waveform (Neon Cyan)
        painter.setPen(QPen(QColor(0, 229, 255, 220), 1.5))
        for i in range(n - 1):
            y1 = mid_y - (self.waveform[i, 0] / 32768.0) * (mid_y * 0.85)
            y2 = mid_y - (self.waveform[i + 1, 0] / 32768.0) * (mid_y * 0.85)
            painter.drawLine(QPointF(i * dx, y1), QPointF((i + 1) * dx, y2))

        # Right Channel Waveform (Amber Gold)
        painter.setPen(QPen(QColor(255, 180, 0, 200), 1.5))
        for i in range(n - 1):
            y1 = mid_y - (self.waveform[i, 1] / 32768.0) * (mid_y * 0.85)
            y2 = mid_y - (self.waveform[i + 1, 1] / 32768.0) * (mid_y * 0.85)
            painter.drawLine(QPointF(i * dx, y1), QPointF((i + 1) * dx, y2))

        # Channel legends
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(0, 229, 255)))
        painter.drawText(8, 14, "CH-L")
        painter.setPen(QPen(QColor(255, 180, 0)))
        painter.drawText(46, 14, "CH-R")

        painter.end()


class DacMonitorWidget(QWidget):
    """
    Main Telemetry HUD: Microscope + Byte Demuxer Readout + Oscilloscope.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # 1. Top Section: Microscope Lens + Byte Demuxer Table
        top_group = QGroupBox("OPTICAL DECODER DAC (SECTION 2 SPEC)")
        top_layout = QHBoxLayout(top_group)
        top_layout.setContentsMargins(10, 14, 10, 10)

        self.lens = MicroscopeLensWidget(self)
        top_layout.addWidget(self.lens)

        # Byte Mapping Grid
        demux_box = QFrame()
        demux_box.setStyleSheet("background-color: #0E1015; border-radius: 6px; padding: 6px;")
        grid = QGridLayout(demux_box)
        grid.setSpacing(6)

        header_font = QFont("Consolas", 8)
        val_font = QFont("Consolas", 10, QFont.Weight.Bold)

        # Row 0: Headers
        for col, title in enumerate(["CHANNEL", "LOW BYTE", "HIGH BYTE", "16-BIT VOLTAGE"]):
            lbl = QLabel(title)
            lbl.setFont(header_font)
            lbl.setStyleSheet("color: #64748B; font-weight: bold;")
            grid.addWidget(lbl, 0, col)

        # Row 1: Left Channel (R & G)
        lbl_l = QLabel("LEFT (L)")
        lbl_l.setStyleSheet("color: #00E5FF; font-weight: bold;")
        lbl_l.setFont(val_font)
        grid.addWidget(lbl_l, 1, 0)

        self.val_r = QLabel("R: 0x00")
        self.val_r.setStyleSheet("color: #EF4444; font-weight: bold;")
        self.val_r.setFont(val_font)
        grid.addWidget(self.val_r, 1, 1)

        self.val_g = QLabel("G: 0x00")
        self.val_g.setStyleSheet("color: #10B981; font-weight: bold;")
        self.val_g.setFont(val_font)
        grid.addWidget(self.val_g, 1, 2)

        self.val_v_l = QLabel("0 V")
        self.val_v_l.setStyleSheet("color: #00E5FF; font-weight: bold;")
        self.val_v_l.setFont(val_font)
        grid.addWidget(self.val_v_l, 1, 3)

        # Row 2: Right Channel (B & A)
        lbl_r = QLabel("RIGHT (R)")
        lbl_r.setStyleSheet("color: #FFB300; font-weight: bold;")
        lbl_r.setFont(val_font)
        grid.addWidget(lbl_r, 2, 0)

        self.val_b = QLabel("B: 0x00")
        self.val_b.setStyleSheet("color: #3B82F6; font-weight: bold;")
        self.val_b.setFont(val_font)
        grid.addWidget(self.val_b, 2, 1)

        self.val_a = QLabel("A: 0x00")
        self.val_a.setStyleSheet("color: #A855F7; font-weight: bold;")
        self.val_a.setFont(val_font)
        grid.addWidget(self.val_a, 2, 2)

        self.val_v_r = QLabel("0 V")
        self.val_v_r.setStyleSheet("color: #FFB300; font-weight: bold;")
        self.val_v_r.setFont(val_font)
        grid.addWidget(self.val_v_r, 2, 3)

        top_layout.addWidget(demux_box, stretch=1)
        layout.addWidget(top_group)

        # 2. Oscilloscope Section
        osc_group = QGroupBox("REAL-TIME STEREO OSCILLOSCOPE")
        osc_layout = QVBoxLayout(osc_group)
        osc_layout.setContentsMargins(10, 14, 10, 10)

        self.oscilloscope = OscilloscopeWidget(self)
        osc_layout.addWidget(self.oscilloscope)
        layout.addWidget(osc_group)

        # 3. CLV Telemetry Footer
        tele_group = QGroupBox("CLV SPIRAL TELEMETRY (SECTION 4)")
        tele_layout = QHBoxLayout(tele_group)
        tele_layout.setContentsMargins(10, 10, 10, 10)

        self.lbl_radius = QLabel("Radius r: 50.0 px")
        self.lbl_radius.setFont(QFont("Consolas", 9))
        self.lbl_radius.setStyleSheet("color: #94A3B8;")

        self.lbl_theta = QLabel("Theta: 0.0 rad")
        self.lbl_theta.setFont(QFont("Consolas", 9))
        self.lbl_theta.setStyleSheet("color: #94A3B8;")

        self.lbl_clv_speed = QLabel("Linear Arc ds: 1.0 px")
        self.lbl_clv_speed.setFont(QFont("Consolas", 9))
        self.lbl_clv_speed.setStyleSheet("color: #00E5FF;")

        self.lbl_sample_rate = QLabel("Clock: 44,100 S/s")
        self.lbl_sample_rate.setFont(QFont("Consolas", 9))
        self.lbl_sample_rate.setStyleSheet("color: #10B981;")

        tele_layout.addWidget(self.lbl_radius)
        tele_layout.addWidget(self.lbl_theta)
        tele_layout.addWidget(self.lbl_clv_speed)
        tele_layout.addWidget(self.lbl_sample_rate)
        layout.addWidget(tele_group)

    def update_telemetry(self, telemetry: dict, disc_canvas: Optional[np.ndarray] = None,
                         r0: float = 50.0, pitch: float = 2.0):
        """
        Updates HUD values from player telemetry dictionary.
        """
        r, g, b, a = telemetry["rgba"]
        vl = telemetry["sample_left"]
        vr = telemetry["sample_right"]
        pos = telemetry["position"]

        self.val_r.setText(f"R: 0x{r:02X}")
        self.val_g.setText(f"G: 0x{g:02X}")
        self.val_b.setText(f"B: 0x{b:02X}")
        self.val_a.setText(f"A: 0x{a:02X}")

        self.val_v_l.setText(f"{vl:+6d}")
        self.val_v_r.setText(f"{vr:+6d}")

        self.oscilloscope.update_waveform(telemetry["waveform"])

        # Compute CLV polar stats
        b_coeff = pitch / (2.0 * math.pi)
        curr_r = math.sqrt(r0**2 + (pos * pitch / math.pi))
        curr_theta = (curr_r - r0) / b_coeff

        self.lbl_radius.setText(f"Radius r: {curr_r:.1f} px")
        self.lbl_theta.setText(f"Theta: {curr_theta:.1f} rad ({curr_theta / (2 * math.pi):.1f} rev)")

        # Update microscope sensor patch if canvas available
        if disc_canvas is not None:
            size = disc_canvas.shape[0]
            cx = size / 2.0
            cy = size / 2.0
            x = int(round(cx + curr_r * math.cos(curr_theta)))
            y = int(round(cy + curr_r * math.sin(curr_theta)))
            patch = extract_optical_sensor_patch(disc_canvas, x, y, patch_radius=12, zoom=4)
            self.lens.update_patch(patch)

