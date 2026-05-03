"""QApplication subclass; global exception handler; single-instance guard."""
import sys
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QSharedMemory
from PySide6.QtGui import QIcon
import os

from euler_omr.constants import APP_NAME, ORG_NAME


class EulerApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName(APP_NAME)
        self.setOrganizationName(ORG_NAME)

        # Set app icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Single-instance guard via QLocalServer
        from PySide6.QtNetwork import QLocalServer, QLocalSocket
        server_name = "EulerOMR_SingleInstance_Server"
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        if socket.waitForConnected(500):
            self._is_running = True
        else:
            QLocalServer.removeServer(server_name)
            self._local_server = QLocalServer()
            self._local_server.listen(server_name)
            self._is_running = False

        # If it's not already running, play the startup sound
        if not self._is_running:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PySide6.QtCore import QUrl
            sound_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sounds", "open.mp3")
            if os.path.exists(sound_path):
                self._player = QMediaPlayer()
                self._audio_output = QAudioOutput()
                self._player.setAudioOutput(self._audio_output)
                self._player.setSource(QUrl.fromLocalFile(sound_path))
                self._audio_output.setVolume(1.0)
                self._player.play()

        # Global exception handler
        sys.excepthook = self._exception_hook

    @property
    def is_already_running(self) -> bool:
        return self._is_running

    @staticmethod
    def _exception_hook(exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(tb, file=sys.stderr)
        try:
            msg = QMessageBox()
            msg.setWindowTitle("Unexpected Error")
            msg.setText("An unexpected error occurred.")
            msg.setDetailedText(tb)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.exec()
        except Exception:
            pass
