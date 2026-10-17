"""
Unit tests for YouTube Downloader Tab & Worker.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from chronodisc.gui.downloader_tab import DownloaderTab, DownloadWorker


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_downloader_tab_initialization(qapp):
    tab = DownloaderTab()
    assert tab.url_entry is not None
    assert tab.quality_combo.count() >= 5
    assert "WAV" in tab.quality_combo.itemText(0)
    assert tab.btn_download is not None
    assert tab.progress_bar.value() == 0


def test_download_worker_init():
    worker = DownloadWorker(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        quality_choice="Audio Only (WAV - 16-bit 44.1kHz PCM - Recommended)",
        download_dir=os.path.expanduser("~/Downloads")
    )
    assert worker.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert "WAV" in worker.quality_choice

