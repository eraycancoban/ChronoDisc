"""
ChronoDisc Turntable Widget
Interactive Vinyl Platter and Virtual Optical Needle Tonearm rendered via QPainter.
"""

import math
from typing import Optional
import numpy as np
from PIL import Image

from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient, QLinearGradient,
    QPixmap, QImage, QPolygonF, QFont
)
from PySide6.QtWidgets import QWidget

from ..core import estimate_sample_from_coordinates, calculate_max_radius


class TurntableWidget(QWidget):
    """
    Renders an interactive spinning vinyl turntable with a software-driven
    Virtual Optical Needle tonearm.
    """
    # Signal emitted when user clicks on disc to seek
    seek_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 420)
        self.setMouseTracking(True)

        self.disc_pixmap: Optional[QPixmap] = None
        self.disc_size: int = 1000
        self.total_samples: int = 0
        self.r0: float = 50.0
        self.pitch: float = 2.0
        self.rmax: float = 300.0

        # State
        self.current_sample_idx: int = 0
        self.is_playing: bool = False
        self.rotation_angle: float = 0.0  # degrees
        self.rpm: float = 33.333

        # Mouse state
        self.is_scrubbing: bool = False

        # Animation timer for platter spinning (60 FPS)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_animation_tick)
        self._anim_timer.start(16)

    def load_disc_image(self, img_array: np.ndarray, total_samples: int,
                        r0: float = 50.0, pitch: float = 2.0):
        """
        Loads an RGBA numpy array into the turntable platter.
        """
        self.disc_size = img_array.shape[0]
        self.total_samples = total_samples
        self.r0 = r0
        self.pitch = pitch
        self.rmax = calculate_max_radius(total_samples, r0, pitch)

        # Convert RGBA numpy array to QImage -> QPixmap
        h, w, ch = img_array.shape
        bytes_per_line = ch * w
        qimg = QImage(img_array.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
        self.disc_pixmap = QPixmap.fromImage(qimg)
        self.update()

    def set_playback_state(self, is_playing: bool, sample_idx: int):
        self.is_playing = is_playing
        self.current_sample_idx = max(0, min(self.total_samples, sample_idx))
        self.update()

    def _on_animation_tick(self):
        if self.is_playing:
            # Platter rotation: approx 33.3 RPM -> ~200 deg/sec -> 3.3 deg per 16ms
            self.rotation_angle = (self.rotation_angle + 1.2) % 360.0
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.total_samples > 0:
            self.is_scrubbing = True
            self._handle_needle_drop(event.position())

    def mouseMoveEvent(self, event):
        if self.is_scrubbing and self.total_samples > 0:
            self._handle_needle_drop(event.position())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_scrubbing = False

    def _handle_needle_drop(self, pos: QPointF):
        w = self.width()
        h = self.height()
        platter_cx = w * 0.44
        platter_cy = h * 0.50
        platter_radius = min(w * 0.42, h * 0.45)

        dx = pos.x() - platter_cx
        dy = pos.y() - platter_cy
        dist_screen = math.sqrt(dx * dx + dy * dy)

        # Convert screen distance to disc pixel coordinates
        scale = self.disc_size / (2.0 * platter_radius)
        r_disc = dist_screen * scale

        sample_idx = estimate_sample_from_coordinates(
            r_disc, 0.0, 0.0, 0.0,
            self.total_samples, self.r0, self.pitch
        )
        self.current_sample_idx = sample_idx
        self.seek_requested.emit(sample_idx)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        # 1. Turntable Chassis Base
        self._draw_chassis(painter, w, h)

        # 2. Vinyl Platter & ChronoDisc
        platter_cx = w * 0.44
        platter_cy = h * 0.50
        platter_radius = min(w * 0.40, h * 0.44)
        self._draw_platter(painter, platter_cx, platter_cy, platter_radius)

        # 3. Virtual Optical Tonearm
        self._draw_tonearm(painter, w, h, platter_cx, platter_cy, platter_radius)

        painter.end()

    def _draw_chassis(self, painter: QPainter, w: int, h: int):
        # Sleek dark brushed metal body
        rect = QRectF(10, 10, w - 20, h - 20)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor(24, 28, 36))
        grad.setColorAt(0.5, QColor(16, 18, 23))
        grad.setColorAt(1.0, QColor(10, 12, 15))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(42, 48, 62), 2))
        painter.drawRoundedRect(rect, 14, 14)

        # Chassis corner screw accents
        for sx, sy in [(22, 22), (w - 22, 22), (22, h - 22), (w - 22, h - 22)]:
            painter.setBrush(QBrush(QColor(40, 45, 55)))
            painter.setPen(QPen(QColor(80, 90, 110), 1))
            painter.drawEllipse(QPointF(sx, sy), 4, 4)

        # Stroboscope speed markings / indicators
        painter.setPen(QPen(QColor(0, 229, 255, 140), 1))
        font = QFont("Consolas", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(26, h - 26, "CHRONODISC CLV")
        painter.setPen(QPen(QColor(160, 175, 195, 160), 8))

    def _draw_platter(self, painter: QPainter, cx: float, cy: float, radius: float):
        # Platter outer beveled metallic rim
        rim_grad = QRadialGradient(cx, cy, radius + 12)
        rim_grad.setColorAt(0.85, QColor(30, 35, 45))
        rim_grad.setColorAt(0.95, QColor(70, 80, 98))
        rim_grad.setColorAt(1.0, QColor(20, 24, 30))
        painter.setBrush(QBrush(rim_grad))
        painter.setPen(QPen(QColor(60, 70, 88), 1.5))
        painter.drawEllipse(QPointF(cx, cy), radius + 10, radius + 10)

        # Strobe dots ring
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(140, 155, 180)))
        n_dots = 48
        for i in range(n_dots):
            ang = math.radians(i * (360.0 / n_dots) + self.rotation_angle)
            dx = cx + (radius + 5) * math.cos(ang)
            dy = cy + (radius + 5) * math.sin(ang)
            painter.drawRect(QRectF(dx - 1.5, dy - 1.5, 3, 3))

        # Vinyl Record Disc Base (Deep Black Polycarbonate)
        vinyl_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.setBrush(QBrush(QColor(8, 9, 12)))
        painter.setPen(QPen(QColor(22, 25, 32), 1))
        painter.drawEllipse(vinyl_rect)

        # Draw ChronoDisc RGBA Spiral Texture if loaded
        if self.disc_pixmap:
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self.rotation_angle)
            painter.translate(-cx, -cy)

            # Draw disc image inside vinyl boundary
            painter.drawPixmap(vinyl_rect.toRect(), self.disc_pixmap)

            # Vinyl Groove Sheen (Anisotropic light reflection cone)
            sheen_grad = QRadialGradient(cx, cy, radius)
            sheen_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            sheen_grad.setColorAt(0.5, QColor(255, 255, 255, 8))
            sheen_grad.setColorAt(0.8, QColor(255, 255, 255, 18))
            sheen_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(sheen_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(vinyl_rect)

            painter.restore()

        # Center Spindle Knob
        spindle_grad = QRadialGradient(cx, cy, 14)
        spindle_grad.setColorAt(0.0, QColor(220, 230, 245))
        spindle_grad.setColorAt(0.6, QColor(100, 110, 130))
        spindle_grad.setColorAt(1.0, QColor(40, 45, 55))
        painter.setBrush(QBrush(spindle_grad))
        painter.setPen(QPen(QColor(30, 35, 45), 1))
        painter.drawEllipse(QPointF(cx, cy), 10, 10)

    def _draw_tonearm(self, painter: QPainter, w: int, h: int,
                      platter_cx: float, platter_cy: float, platter_radius: float):
        # Tonearm gimbal base located top-right
        base_x = w * 0.86
        base_y = h * 0.22

        # Draw gimbal pivot assembly
        base_grad = QRadialGradient(base_x, base_y, 28)
        base_grad.setColorAt(0.0, QColor(60, 70, 85))
        base_grad.setColorAt(0.7, QColor(28, 32, 40))
        base_grad.setColorAt(1.0, QColor(14, 16, 20))
        painter.setBrush(QBrush(base_grad))
        painter.setPen(QPen(QColor(80, 95, 120), 2))
        painter.drawEllipse(QPointF(base_x, base_y), 24, 24)

        # Center metallic pivot screw
        painter.setBrush(QBrush(QColor(180, 195, 215)))
        painter.drawEllipse(QPointF(base_x, base_y), 8, 8)

        # Calculate needle tip position on the disc
        # Track position relative to disc radius
        if self.total_samples > 0:
            scale = platter_radius / (self.disc_size / 2.0 if self.disc_size > 0 else 1.0)
            
            # Theoretical needle radius
            curr_r = math.sqrt(self.r0**2 + (self.current_sample_idx * self.pitch / math.pi))
            needle_r_screen = min(platter_radius, curr_r * scale)
        else:
            needle_r_screen = platter_radius * 0.65

        # Needle head sits at right side of disc along the track
        # Give needle an angle relative to disc center
        needle_angle = math.radians(28.0)
        tip_x = platter_cx + needle_r_screen * math.cos(needle_angle)
        tip_y = platter_cy + needle_r_screen * math.sin(needle_angle)

        # Counterweight behind pivot
        dx_arm = tip_x - base_x
        dy_arm = tip_y - base_y
        arm_len = math.sqrt(dx_arm * dx_arm + dy_arm * dy_arm)
        if arm_len > 0:
            dir_x = dx_arm / arm_len
            dir_y = dy_arm / arm_len
            cw_x = base_x - dir_x * 28
            cw_y = base_y - dir_y * 28

            painter.setBrush(QBrush(QColor(35, 40, 50)))
            painter.setPen(QPen(QColor(110, 125, 150), 2))
            painter.drawEllipse(QPointF(cw_x, cw_y), 14, 14)

        # Tonearm Rod (Sleek brushed titanium curved arm)
        # Control point for curved arm
        ctrl_x = (base_x + tip_x) / 2.0 + 18
        ctrl_y = (base_y + tip_y) / 2.0 - 18

        arm_path = QPolygonF([QPointF(base_x, base_y), QPointF(ctrl_x, ctrl_y), QPointF(tip_x, tip_y)])
        painter.setPen(QPen(QColor(190, 205, 225), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(arm_path)

        # Optical Sensor Head Cartridge
        painter.setBrush(QBrush(QColor(22, 26, 34)))
        painter.setPen(QPen(QColor(0, 229, 255), 1.5))
        cartridge_rect = QRectF(tip_x - 7, tip_y - 12, 14, 24)
        painter.drawRoundedRect(cartridge_rect, 3, 3)

        # Glowing Optical Laser Spot
        laser_color = QColor(0, 240, 255, 240 if self.is_playing else 140)
        painter.setBrush(QBrush(laser_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(tip_x, tip_y), 3.5, 3.5)

        # Laser beam outer glow ring
        glow_grad = QRadialGradient(tip_x, tip_y, 14)
        glow_grad.setColorAt(0.0, QColor(0, 240, 255, 160 if self.is_playing else 60))
        glow_grad.setColorAt(0.4, QColor(0, 200, 255, 80 if self.is_playing else 20))
        glow_grad.setColorAt(1.0, QColor(0, 200, 255, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.drawEllipse(QPointF(tip_x, tip_y), 14, 14)

        # Laser crosshair target reticle when playing or hovering
        painter.setPen(QPen(QColor(0, 229, 255, 120), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(tip_x - 10, tip_y), QPointF(tip_x + 10, tip_y))
        painter.drawLine(QPointF(tip_x, tip_y - 10), QPointF(tip_x, tip_y + 10))

