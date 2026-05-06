"""Application entry point; bootstraps QApplication, splash screen, and MainWindow."""
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    import multiprocessing
    multiprocessing.freeze_support()
    
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
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
