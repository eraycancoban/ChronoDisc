"""
ChronoDisc YouTube Music Downloader & Optical Importer Tab
Based on yt-dlp-ui architecture, adapted for PySide6 and integrated with ChronoDisc.
"""

import os
import re
import shutil
import subprocess
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QClipboard
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QProgressBar, QGroupBox, QFileDialog, QMessageBox,
    QFrame, QApplication, QTextEdit
)
import yt_dlp


class DownloadWorker(QThread):
    """
    Background worker thread running yt-dlp to download and extract audio/video.
    Emits progress and completion signals safely to the Qt GUI thread.
    """
    progress_updated = Signal(float, str)
    log_message = Signal(str)
    download_finished = Signal(bool, str, str, str)  # success, message, filepath, title

    def __init__(self, url: str, quality_choice: str, download_dir: str):
        super().__init__()
        self.url = url
        self.quality_choice = quality_choice
        self.download_dir = download_dir
        self.downloaded_filepath: str = ""
        self.track_title: str = ""

    def progress_hook(self, d):
        if d.get("status") == "downloading":
            try:
                # Remove ANSI escape sequences from percentage string (from yt-dlp-ui base)
                percent_str = d.get("_percent_str", "0.0%").strip()
                percent_str = re.sub(r"\x1b\[[0-9;]*m", "", percent_str)
                cleaned_percent = percent_str.replace("%", "").strip()
                percent = float(cleaned_percent) / 100.0 if cleaned_percent else 0.0

                speed_str = d.get("_speed_str", "N/A")
                speed_str = re.sub(r"\x1b\[[0-9;]*m", "", speed_str).strip()

                eta_str = d.get("_eta_str", "N/A")
                eta_str = re.sub(r"\x1b\[[0-9;]*m", "", eta_str).strip()

                msg = f"Downloading... {percent_str} (Speed: {speed_str}, ETA: {eta_str})"
                self.progress_updated.emit(percent, msg)
            except Exception:
                pass
        elif d.get("status") == "finished":
            self.progress_updated.emit(1.0, "Download Finished! Processing audio with FFmpeg...")

    def postprocessor_hook(self, d):
        if d.get("status") == "finished":
            fp = d.get("info_dict", {}).get("filepath") or d.get("filepath")
            if fp and os.path.exists(fp):
                self.downloaded_filepath = fp

    def run(self):
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            self.download_finished.emit(
                False, "FFmpeg was not found in system PATH. Please ensure FFmpeg is installed.", "", ""
            )
            return

        # Format mappings based on yt-dlp-ui with ChronoDisc audio-first enhancements
        is_audio = "Audio" in self.quality_choice
        postprocessors = []

        if "WAV" in self.quality_choice:
            format_str = "bestaudio/best"
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            })
            target_ext = "wav"
        elif "MP3" in self.quality_choice:
            format_str = "bestaudio/best"
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            })
            target_ext = "mp3"
        elif "FLAC" in self.quality_choice:
            format_str = "bestaudio/best"
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "flac",
            })
            target_ext = "flac"
        elif "M4A" in self.quality_choice:
            format_str = "bestaudio/best"
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            })
            target_ext = "m4a"
        elif "1080p" in self.quality_choice:
            format_str = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best"
            target_ext = "mp4"
        elif "720p" in self.quality_choice:
            format_str = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best"
            target_ext = "mp4"
        else:
            # Best (Video + Audio)
            format_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            target_ext = "mp4"

        # Out template
        outtmpl = os.path.join(self.download_dir, "%(title)s.%(ext)s")

        ydl_opts = {
            "format": format_str,
            "outtmpl": outtmpl,
            "progress_hooks": [self.progress_hook],
            "postprocessor_hooks": [self.postprocessor_hook],
            "nocheckcertificate": True,
            "js_runtimes": {"node": {}},
            "ffmpeg_location": os.path.dirname(ffmpeg_path) if os.path.isfile(ffmpeg_path) else ffmpeg_path,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        if postprocessors:
            ydl_opts["postprocessors"] = postprocessors

        try:
            self.log_message.emit(f"Connecting to YouTube via yt-dlp: {self.url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                self.track_title = info.get("title", "Unknown Track")

                # Detect final file path
                if not self.downloaded_filepath or not os.path.exists(self.downloaded_filepath):
                    # Check base filename with target extension
                    base_fn = ydl.prepare_filename(info)
                    candidate = os.path.splitext(base_fn)[0] + "." + target_ext
                    if os.path.exists(candidate):
                        self.downloaded_filepath = candidate
                    elif os.path.exists(base_fn):
                        self.downloaded_filepath = base_fn

            if self.downloaded_filepath and os.path.exists(self.downloaded_filepath):
                self.log_message.emit(f"✓ Successfully processed: {self.downloaded_filepath}")
                self.download_finished.emit(
                    True,
                    f"Download and Processing Complete! ({os.path.basename(self.downloaded_filepath)})",
                    self.downloaded_filepath,
                    self.track_title
                )
            else:
                self.download_finished.emit(
                    True,
                    "Download and Processing Complete!",
                    "",
                    self.track_title
                )
        except Exception as e:
            self.log_message.emit(f"Error during download: {str(e)}")
            self.download_finished.emit(False, f"Error: {str(e)}", "", "")


class DownloaderTab(QWidget):
    """
    YouTube Music Downloader tab embedded inside ChronoDisc.
    Allows downloading tracks directly from YouTube and importing them into
    ChronoDisc Studio (Encoder) or spinning directly on the Virtual Turntable.
    """
    # Signals to communicate with ChronoDisc main window
    load_into_studio_requested = Signal(str, str)     # file_path, track_title
    direct_turntable_requested = Signal(str, str)     # file_path, track_title

    def __init__(self, parent=None):
        super().__init__(parent)
        self.download_path = os.path.expanduser("~/Downloads")
        self.last_downloaded_file: Optional[str] = None
        self.last_track_title: str = ""
        self.worker: Optional[DownloadWorker] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # 1. Header Banner
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #12151C; border-radius: 8px; padding: 10px 14px;")
        h_layout = QVBoxLayout(header_frame)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(4)

        title = QLabel("YOUTUBE MUSIC DOWNLOADER & OPTICAL IMPORTER")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #00E5FF; letter-spacing: 0.5px;")
        h_layout.addWidget(title)

        subtitle = QLabel("Fetch tracks directly from YouTube using yt-dlp & FFmpeg, then encode losslessly into ChronoDisc.")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #94A3B8;")
        h_layout.addWidget(subtitle)
        layout.addWidget(header_frame)

        # 2. Main Parameters Box
        input_group = QGroupBox("DOWNLOAD CONFIGURATION (YT-DLP)")
        input_layout = QVBoxLayout(input_group)
        input_layout.setContentsMargins(14, 16, 14, 14)
        input_layout.setSpacing(12)

        # URL Input Row with Paste & Clear buttons
        url_label = QLabel("Video / Audio Stream URL:")
        url_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        input_layout.addWidget(url_label)

        url_row = QHBoxLayout()
        url_row.setSpacing(8)

        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_entry.setFixedHeight(36)
        url_row.addWidget(self.url_entry, stretch=1)

        self.btn_paste = QPushButton("📋 Paste")
        self.btn_paste.setFixedHeight(36)
        self.btn_paste.clicked.connect(self._on_paste_url)
        url_row.addWidget(self.btn_paste)

        self.btn_clear = QPushButton("✖ Clear")
        self.btn_clear.setFixedHeight(36)
        self.btn_clear.clicked.connect(lambda: self.url_entry.clear())
        url_row.addWidget(self.btn_clear)

        input_layout.addLayout(url_row)

        # Format / Quality Selector
        q_row = QHBoxLayout()
        q_row.setSpacing(12)

        q_lbl = QLabel("Format / Quality:")
        q_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        q_row.addWidget(q_lbl)

        self.quality_combo = QComboBox()
        self.quality_combo.setFixedHeight(34)
        self.quality_combo.addItems([
            "Audio Only (WAV - 16-bit 44.1kHz PCM - Recommended)",
            "Audio Only (MP3 - 320 kbps High Quality)",
            "Audio Only (FLAC - Lossless)",
            "Audio Only (M4A / AAC)",
            "Best (Video + Audio)",
            "1080p Video",
            "720p Video",
        ])
        q_row.addWidget(self.quality_combo, stretch=1)
        input_layout.addLayout(q_row)

        # Download Directory Selection
        path_row = QHBoxLayout()
        path_row.setSpacing(10)

        self.path_label = QLabel(f"Save to: {self.download_path}")
        self.path_label.setStyleSheet("color: #94A3B8; font-family: Consolas; font-size: 11px;")
        path_row.addWidget(self.path_label, stretch=1)

        self.btn_browse = QPushButton("📁 Browse Folder")
        self.btn_browse.clicked.connect(self._on_select_path)
        path_row.addWidget(self.btn_browse)

        self.btn_open_folder = QPushButton("📂 Open Folder")
        self.btn_open_folder.clicked.connect(self._on_open_download_folder)
        path_row.addWidget(self.btn_open_folder)

        input_layout.addLayout(path_row)

        # Download Button
        self.btn_download = QPushButton("⬇ Start Download & Extraction")
        self.btn_download.setObjectName("accentButton")
        self.btn_download.setFixedHeight(42)
        self.btn_download.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_download.clicked.connect(self._on_start_download)
        input_layout.addWidget(self.btn_download)

        layout.addWidget(input_group)

        # 3. Progress & Status
        prog_group = QGroupBox("DOWNLOAD & EXTRACTION STATUS")
        prog_layout = QVBoxLayout(prog_group)
        prog_layout.setContentsMargins(14, 16, 14, 14)
        prog_layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        prog_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to download.")
        self.status_label.setFont(QFont("Consolas", 10))
        self.status_label.setStyleSheet("color: #94A3B8;")
        prog_layout.addWidget(self.status_label)

        layout.addWidget(prog_group)

        # 4. Post-Download ChronoDisc Actions Box (Enabled once downloaded)
        self.action_group = QGroupBox("CHRONODISC INTEGRATION ACTIONS")
        self.action_group.setEnabled(False)
        act_layout = QVBoxLayout(self.action_group)
        act_layout.setContentsMargins(14, 14, 14, 14)
        act_layout.setSpacing(10)

        self.lbl_completed_info = QLabel("Download a track to unlock optical vinyl actions.")
        self.lbl_completed_info.setStyleSheet("color: #64748B; font-weight: bold;")
        act_layout.addWidget(self.lbl_completed_info)

        act_btn_row = QHBoxLayout()
        act_btn_row.setSpacing(12)

        self.btn_to_studio = QPushButton("💿 Load into Studio (Encoder)")
        self.btn_to_studio.setObjectName("accentButton")
        self.btn_to_studio.setFixedHeight(38)
        self.btn_to_studio.clicked.connect(self._on_load_into_studio)
        act_btn_row.addWidget(self.btn_to_studio)

        self.btn_to_turntable = QPushButton("🎧 Directly Spin on Turntable")
        self.btn_to_turntable.setObjectName("playButton")
        self.btn_to_turntable.setFixedHeight(38)
        self.btn_to_turntable.clicked.connect(self._on_send_to_turntable)
        act_btn_row.addWidget(self.btn_to_turntable)

        self.btn_show_file = QPushButton("🔍 Show File in Explorer")
        self.btn_show_file.setFixedHeight(38)
        self.btn_show_file.clicked.connect(self._on_show_file_in_explorer)
        act_btn_row.addWidget(self.btn_show_file)

        act_layout.addLayout(act_btn_row)
        layout.addWidget(self.action_group)

        # 5. Collapsible Log Console
        log_group = QGroupBox("ACTIVITY LOG")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 10, 10, 10)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(90)
        self.log_console.setStyleSheet("background-color: #0A0C10; color: #00E5FF; font-family: Consolas; font-size: 11px;")
        log_layout.addWidget(self.log_console)

        layout.addWidget(log_group)
        layout.addStretch()

    def _on_paste_url(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.url_entry.setText(text)

    def _on_select_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.download_path)
        if folder:
            self.download_path = folder
            self.path_label.setText(f"Save to: {self.download_path}")

    def _on_open_download_folder(self):
        if os.path.exists(self.download_path):
            os.startfile(self.download_path)

    def _on_start_download(self):
        url = self.url_entry.text().strip()
        if not url:
            self.status_label.setText("Please enter a valid video/audio URL.")
            self.status_label.setStyleSheet("color: #EF4444; font-weight: bold;")
            return

        choice = self.quality_combo.currentText()

        self.btn_download.setEnabled(False)
        self.status_label.setText("Starting download...")
        self.status_label.setStyleSheet("color: #00E5FF; font-weight: bold;")
        self.progress_bar.setValue(0)
        self.action_group.setEnabled(False)

        # Launch background QThread
        self.worker = DownloadWorker(url, choice, self.download_path)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.log_message.connect(self._on_log_message)
        self.worker.download_finished.connect(self._on_download_finished)
        self.worker.start()

    def _on_progress_updated(self, percent: float, text: str):
        val = int(percent * 100)
        self.progress_bar.setValue(val)
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: #00E5FF;")

    def _on_log_message(self, msg: str):
        self.log_console.append(msg)

    def _on_download_finished(self, success: bool, message: str, filepath: str, title: str):
        self.btn_download.setEnabled(True)
        if success:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #10B981; font-weight: bold;")
            self.progress_bar.setValue(100)

            if filepath and os.path.exists(filepath):
                self.last_downloaded_file = filepath
                self.last_track_title = title or os.path.splitext(os.path.basename(filepath))[0]
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                self.lbl_completed_info.setText(
                    f"✓ Ready: <b>{os.path.basename(filepath)}</b> ({size_mb:.2f} MB)"
                )
                self.lbl_completed_info.setStyleSheet("color: #10B981;")
                self.action_group.setEnabled(True)
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #EF4444; font-weight: bold;")
            self.progress_bar.setValue(0)

    def _on_load_into_studio(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            self.load_into_studio_requested.emit(self.last_downloaded_file, self.last_track_title)

    def _on_send_to_turntable(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            self.direct_turntable_requested.emit(self.last_downloaded_file, self.last_track_title)

    def _on_show_file_in_explorer(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            subprocess.run(["explorer", "/select,", os.path.normpath(self.last_downloaded_file)])

