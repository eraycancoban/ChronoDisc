"""
ChronoDisc Futuristic Dark Vinyl Theme Stylesheet (QSS)
"""

DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #0F1115;
    color: #E2E8F0;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}

QWidget {
    background-color: #0F1115;
    color: #E2E8F0;
    font-size: 13px;
}

/* Tab Bar */
QTabWidget::pane {
    border: 1px solid #1E232E;
    background-color: #12151C;
    border-radius: 8px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #161A22;
    color: #8C98A8;
    padding: 10px 22px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #232936;
    border-bottom: none;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #12151C;
    color: #00E5FF;
    border-top: 2px solid #00E5FF;
    border-bottom: 1px solid #12151C;
}

QTabBar::tab:hover:!selected {
    background-color: #1A202C;
    color: #CBD5E1;
}

/* Group Boxes & Panels */
QGroupBox {
    border: 1px solid #222834;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    background-color: #151820;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    color: #00E5FF;
    font-size: 12px;
    letter-spacing: 0.5px;
}

/* Push Buttons */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E2430, stop:1 #171B24);
    border: 1px solid #2E3646;
    border-radius: 6px;
    color: #E2E8F0;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 18px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2A3242, stop:1 #1E2430);
    border: 1px solid #00E5FF;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #11141B;
    border: 1px solid #00B4D8;
}

QPushButton#accentButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00B4D8, stop:1 #0077B6);
    border: 1px solid #00E5FF;
    color: #FFFFFF;
    font-weight: bold;
}

QPushButton#accentButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00E5FF, stop:1 #0096C7);
    border: 1px solid #90E0EF;
}

QPushButton#playButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10B981, stop:1 #059669);
    border: 1px solid #34D399;
    color: #FFFFFF;
    border-radius: 20px;
    font-size: 16px;
    font-weight: bold;
}

QPushButton#playButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34D399, stop:1 #10B981);
}

/* Sliders */
QSlider::groove:horizontal {
    border: 1px solid #2A303C;
    height: 6px;
    background: #171A21;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0077B6, stop:1 #00E5FF);
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #E2E8F0;
    border: 2px solid #00E5FF;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #FFFFFF;
    border: 2px solid #38BDF8;
}

/* Labels */
QLabel {
    color: #CBD5E1;
}

QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel#metaValue {
    color: #00E5FF;
    font-family: "Consolas", monospace;
    font-weight: bold;
}

/* Line Edit & ComboBox */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #151821;
    border: 1px solid #28303F;
    border-radius: 5px;
    color: #F1F5F9;
    padding: 6px 10px;
    selection-background-color: #00E5FF;
    selection-color: #000000;
    min-height: 20px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #00E5FF;
    background-color: #181D28;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #28303F;
}

/* Scroll Area */
QScrollArea {
    border: none;
    background-color: transparent;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #262D3A;
    border-radius: 4px;
    background-color: #151821;
    text-align: center;
    color: #E2E8F0;
    font-weight: bold;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0096C7, stop:1 #00E5FF);
    border-radius: 3px;
}
"""

