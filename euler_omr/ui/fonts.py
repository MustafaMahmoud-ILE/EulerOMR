"""Fixedsys font loader (bundled TTF fallback if system font absent)."""
import os
from PySide6.QtGui import QFontDatabase, QFont


def load_fonts() -> QFont:
    """Load bundled Fixedsys font and return the application font."""
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "fonts")
    if os.path.isdir(fonts_dir):
        for f in os.listdir(fonts_dir):
            if f.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(fonts_dir, f))

    # Try Fixedsys variants
    for name in ["Fixedsys Excelsior", "Fixedsys", "FSEX300"]:
        font = QFont(name, 10)
        if font.exactMatch() or QFontDatabase.hasFamily(name):
            return font

    # Fallback
    return QFont("Courier New", 10)
