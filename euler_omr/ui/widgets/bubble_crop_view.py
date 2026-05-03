"""Read-only QLabel with QPixmap crop display for Review Page dialogue."""
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
import numpy as np


class BubbleCropView(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("QLabel { background-color: #052221; border: 1px solid #385550; padding: 4px; }")
        self.setMinimumHeight(60)
        self.setText("No crop available")

    def set_crop(self, img: np.ndarray):
        """Set crop from numpy array (BGR or grayscale)."""
        if len(img.shape) == 2:
            h, w = img.shape
            qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            h, w, ch = img.shape
            if ch == 3:
                import cv2
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                qimg = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
            else:
                qimg = QImage(img.data, w, h, w * 4, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimg.copy())
        scaled = pixmap.scaledToHeight(min(120, h), Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled)
