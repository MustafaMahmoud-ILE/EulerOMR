"""TinyTexInstallDialog: explanation, download & install button, progress, log."""
import os, tempfile
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar
from PySide6.QtCore import QThreadPool
from euler_omr.constants import TINYTEX_DOWNLOAD_URL
from euler_omr.workers.base_worker import BaseWorker
from euler_omr.ui.widgets.log_panel import LogPanel


class _DownloadWorker(BaseWorker):
    def __init__(self, url, dest):
        super().__init__()
        self.url = url
        self.dest = dest

    def run(self):
        try:
            import urllib.request
            self._log(f"Downloading from {self.url}...", "INFO")
            urllib.request.urlretrieve(self.url, self.dest, self._progress_hook)
            self.signals.result.emit(self.dest)
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))

    def _progress_hook(self, block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            pct = min(int(downloaded / total_size * 100), 100)
            self.signals.progress.emit(pct, 100)


class TinyTexInstallDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LaTeX Compiler Not Found")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "pdflatex not found. Install TinyTeX to enable template compilation.\n"
            "TinyTeX is a minimal LaTeX distribution (~200 MB)."
        ))

        self.btn_download = QPushButton("Download and Install TinyTeX")
        self.btn_download.clicked.connect(self._download)
        layout.addWidget(self.btn_download)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        self.log_panel = LogPanel()
        layout.addWidget(self.log_panel)

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

    def _download(self):
        self.btn_download.setEnabled(False)
        dest = os.path.join(tempfile.gettempdir(), "TinyTeX-installer.exe")
        worker = _DownloadWorker(TINYTEX_DOWNLOAD_URL, dest)
        worker.signals.progress.connect(lambda c, t: self.progress.setValue(c))
        worker.signals.log.connect(self.log_panel.append_log)
        worker.signals.result.connect(self._on_downloaded)
        worker.signals.error.connect(lambda e: self.log_panel.append_log(f"Error: {e}", "ERROR"))
        worker.signals.finished.connect(lambda: self.btn_download.setEnabled(True))
        QThreadPool.globalInstance().start(worker)

    def _on_downloaded(self, path):
        self.log_panel.append_log(f"Downloaded to {path}", "INFO")
        self.log_panel.append_log("Running installer...", "INFO")
        import subprocess
        try:
            subprocess.Popen([path], shell=True)
            self.log_panel.append_log("Installer launched. Please restart after installation.", "INFO")
        except Exception as e:
            self.log_panel.append_log(f"Failed to run installer: {e}", "ERROR")
