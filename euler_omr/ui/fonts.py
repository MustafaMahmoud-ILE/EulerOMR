"""Fixedsys font loader (bundled TTF fallback if system font absent)."""
import os
from PySide6.QtGui import QFontDatabase, QFont


def load_fonts() -> QFont:
    """Load bundled Fixedsys font and return the application font."""
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "fonts")
    ttf_loaded = False
    if os.path.isdir(fonts_dir):
        for f in os.listdir(fonts_dir):
            if f.lower().endswith((".ttf", ".otf")):
                result = QFontDatabase.addApplicationFont(os.path.join(fonts_dir, f))
                if result != -1:
                    ttf_loaded = True

    # Only attempt Fixedsys variants if a TTF was actually registered.
    # "Fixedsys" on Windows is a bitmap/raster font; DirectWrite cannot render
    # it and emits noisy CreateFontFaceFromHDC() errors.  Skip it unless we
    # loaded a proper TrueType replacement (e.g. Fixedsys Excelsior).
    if ttf_loaded:
        for name in ["Fixedsys Excelsior", "FSEX300", "Fixedsys Excelsior 3.01"]:
            if QFontDatabase.hasFamily(name):
                return QFont(name, 10)

    # Safe fallback — always available, proper TrueType, no DirectWrite warnings.
    return QFont("Courier New", 10)
