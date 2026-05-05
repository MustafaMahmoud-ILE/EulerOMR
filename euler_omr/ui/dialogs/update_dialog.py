import os
import tempfile
import requests
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar, QHBoxLayout, QTextEdit
from PySide6.QtCore import QThreadPool, Signal

from euler_omr.workers.base_worker import BaseWorker

class DownloadUpdateWorker(BaseWorker):
    def __init__(self, url, dest):
        super().__init__()
        self.url = url
        self.dest = dest

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            with open(self.dest, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = min(int(downloaded / total_size * 100), 100)
                            self.signals.progress.emit(pct, 100)
                            
            self.signals.result.emit(self.dest)
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))

class UpdateDialog(QDialog):
    def __init__(self, version, release_notes, download_url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Available")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.download_url = download_url
        self.dest_path = os.path.join(tempfile.gettempdir(), f"EulerOMR_Setup_{version}.exe")
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"<h2>A new version ({version}) is available!</h2>"))
        
        notes_edit = QTextEdit()
        notes_edit.setReadOnly(True)
        notes_edit.setMarkdown(release_notes)
        layout.addWidget(notes_edit)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        layout.addWidget(self.progress)
        
        self.lbl_status = QLabel("Do you want to download and install this update?")
        layout.addWidget(self.lbl_status)
        
        btn_layout = QHBoxLayout()
        self.btn_update = QPushButton("Download and Install")
        self.btn_update.clicked.connect(self._start_download)
        self.btn_cancel = QPushButton("Remind Me Later")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_update)
        layout.addLayout(btn_layout)
        
    def _start_download(self):
        self.btn_update.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.lbl_status.setText("Downloading update...")
        
        worker = DownloadUpdateWorker(self.download_url, self.dest_path)
        worker.signals.progress.connect(lambda c, t: self.progress.setValue(c))
        worker.signals.result.connect(self._on_downloaded)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)
        
    def _on_error(self, error):
        self.lbl_status.setText(f"Download failed: {error}")
        self.btn_update.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        
    def _on_downloaded(self, path):
        self.lbl_status.setText("Download complete! Launching installer...")
        import subprocess
        import sys
        try:
            subprocess.Popen([path], shell=True)
            self.accept()
            sys.exit(0)
        except Exception as e:
            self.lbl_status.setText(f"Failed to launch installer: {e}")
            self.btn_cancel.setEnabled(True)
