"""QApplication subclass; global exception handler; single-instance guard."""
import sys
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QSharedMemory
from PySide6.QtGui import QIcon
import os

from euler_omr.constants import APP_NAME, ORG_NAME


from PySide6.QtCore import QSharedMemory, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

class EulerApp(QApplication):
    fileOpenRequested = Signal(str)

    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName(APP_NAME)
        self.setOrganizationName(ORG_NAME)

        # Single-instance guard via QLocalServer
        self.server_name = "EulerOMR_SingleInstance_Server"
        self._is_running = False
        
        # Try to connect to an existing server
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if socket.waitForConnected(500):
            self._is_running = True
            # If we have a file argument, send it to the existing instance
            if len(sys.argv) > 1:
                path = os.path.abspath(sys.argv[1])
                socket.write(path.encode('utf-8'))
                socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        else:
            # Not running, so we become the server
            QLocalServer.removeServer(self.server_name)
            self._local_server = QLocalServer()
            self._local_server.newConnection.connect(self._on_new_connection)
            self._local_server.listen(self.server_name)

        # If it's not already running, play the startup sound
        if not self._is_running:
            from euler_omr.core.sound_manager import SoundManager
            SoundManager.play_open()

        # ... (rest of the init remains similar, but using sys.argv logic)
        from euler_omr.core.path_utils import get_asset_path
        
        if os.name == 'nt':
            import ctypes
            myappid = f'{ORG_NAME}.{APP_NAME}.1.1.6'.replace(" ", "")
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        # Set app icon
        icon_path = get_asset_path("icons", "app.ico")
        if not os.path.exists(icon_path):
            icon_path = get_asset_path("logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Monkeypatch QPushButton and QMessageBox to add automatic sounds
        from PySide6.QtWidgets import QPushButton, QMessageBox
        old_btn_press = QPushButton.mousePressEvent
        def new_btn_press(btn_self, event):
            from euler_omr.core.sound_manager import SoundManager
            SoundManager.play_click()
            old_btn_press(btn_self, event)
        QPushButton.mousePressEvent = new_btn_press

        def _play_alert_sound():
            from euler_omr.core.sound_manager import SoundManager
            SoundManager.play_alert()

        # Patch instance methods
        old_msg_exec = QMessageBox.exec
        def new_msg_exec(msg_self, *args, **kwargs):
            _play_alert_sound()
            return old_msg_exec(msg_self, *args, **kwargs)
        QMessageBox.exec = new_msg_exec
        QMessageBox.exec_ = new_msg_exec # Cover both

        # Patch static methods
        for name in ["information", "warning", "critical", "question", "about"]:
            old_static = getattr(QMessageBox, name)
            def wrapper(old_func):
                def wrapped(*args, **kwargs):
                    _play_alert_sound()
                    return old_func(*args, **kwargs)
                return wrapped
            setattr(QMessageBox, name, wrapper(old_static))

        # Global exception handler
        sys.excepthook = self._exception_hook

    @property
    def is_already_running(self) -> bool:
        return self._is_running

    def _on_new_connection(self):
        socket = self._local_server.nextPendingConnection()
        if socket.waitForReadyRead(1000):
            path = bytes(socket.readAll().data()).decode('utf-8')
            if os.path.exists(path):
                self.fileOpenRequested.emit(path)
        socket.disconnectFromServer()

    @staticmethod
    def _exception_hook(exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(tb, file=sys.stderr)
        
        # Avoid showing dialogs during shutdown or before app is ready
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            return

        try:
            msg = QMessageBox()
            msg.setWindowTitle("Unexpected Error")
            msg.setText("An unexpected error occurred.")
            msg.setDetailedText(tb)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.exec()
        except Exception:
            # Fallback to console if GUI is already partially destroyed
            pass
