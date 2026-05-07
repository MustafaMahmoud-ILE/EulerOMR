"""TinyTexInstallDialog: explanation, download & install button, progress, log."""
import os, tempfile
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar
from PySide6.QtCore import QThreadPool
from euler_omr.workers.base_worker import BaseWorker
from euler_omr.ui.widgets.log_panel import LogPanel


class _DownloadWorker(BaseWorker):
    def __init__(self):
        super().__init__()

    def run(self):
        try:
            import pytinytex
            self._log("Starting TinyTeX download and installation...", "INFO")
            
            # variation=2 is the extended set and uses .zip on Windows
            pytinytex.download_tinytex(
                variation=2, 
                progress_callback=self._progress_hook
            )
            
            pdflatex_path = pytinytex.get_pdflatex_engine()
            
            if pdflatex_path:
                self._log("TinyTeX installed successfully!", "INFO")
                self.signals.result.emit(pdflatex_path)
            else:
                self._log("TinyTeX installed but pdflatex engine could not be located.", "WARNING")
            
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))

    def _progress_hook(self, downloaded, total):
        if total > 0:
            pct = min(int(downloaded / total * 100), 100)
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

        self.btn_download = QPushButton("Download and Extract TinyTeX")
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
        worker = _DownloadWorker()
        worker.signals.progress.connect(lambda c, t: self.progress.setValue(c))
        worker.signals.log.connect(self.log_panel.append_log)
        worker.signals.result.connect(self._on_downloaded)
        worker.signals.error.connect(lambda e: self.log_panel.append_log(f"Error: {e}", "ERROR"))
        worker.signals.finished.connect(lambda: self.btn_download.setEnabled(True))
        QThreadPool.globalInstance().start(worker)

    def _on_downloaded(self, path):
        self.log_panel.append_log(f"TinyTeX is ready at {path}. You can close this dialog.", "INFO")

