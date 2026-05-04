"""Application entry point; bootstraps QApplication, splash screen, and MainWindow."""
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from euler_omr.logger import setup_logging
    setup_logging()

    from euler_omr.app import EulerApp
    app = EulerApp(sys.argv)

    if app.is_already_running:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(None, "Euler OMR", "Euler OMR is already running.")
        sys.exit(0)

    # ── Splash Screen ──
    from PySide6.QtWidgets import QSplashScreen
    from PySide6.QtGui import QPixmap
    from PySide6.QtCore import Qt

    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(base_dir, "leonhard.png")
    splash = None
    if os.path.exists(img_path):
        pixmap = QPixmap(img_path)
        if pixmap.width() > 500 or pixmap.height() > 500:
            pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        splash = QSplashScreen(pixmap, Qt.WindowType.SplashScreen)
        splash.show()
        app.processEvents()

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
    
    if splash:
        splash.finish(window)
        splash.close()
        
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
