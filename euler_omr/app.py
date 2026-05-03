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

        # Single-instance guard
        self._shared_mem = QSharedMemory("EulerOMR_SingleInstance")
        if self._shared_mem.attach():
            self._is_running = True
        else:
            self._shared_mem.create(1)
            self._is_running = False

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
