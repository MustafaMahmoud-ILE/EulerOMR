"""Application entry point; bootstraps QApplication, splash screen, and MainWindow."""
import sys
import os
from PySide6.QtCore import Qt

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    import multiprocessing
    multiprocessing.freeze_support()

    # Taskbar Icon Fix for Windows
    if os.name == 'nt':
        import ctypes
        myappid = 'MustafaMahmoud.EulerOMR.v1.1.5' # Unique App ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    from euler_omr.logger import setup_logging
    setup_logging()

    from euler_omr.app import EulerApp
    app = EulerApp(sys.argv)

    if app.is_already_running:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(None, "Euler OMR", "Euler OMR is already running.")
        sys.exit(0)

    # Apply stylesheet
    from euler_omr.ui.style import apply_stylesheet
    apply_stylesheet(app)

    # Load fonts
    from euler_omr.ui.fonts import load_fonts
    font = load_fonts()
    app.setFont(font)

    # Create and show main window
    from euler_omr.ui.main_window import MainWindow
    window = MainWindow()
    
    # Connect signal for opening files from other instances
    def on_file_requested(path):
        window._open_file(path)
        window.setWindowState(window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        window.raise_()
        window.activateWindow()

    app.fileOpenRequested.connect(on_file_requested)

    window.show()

    # Handle initial file if passed
    if len(sys.argv) > 1:
        initial_path = os.path.abspath(sys.argv[1])
        if os.path.exists(initial_path):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, lambda: window._open_file(initial_path))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
