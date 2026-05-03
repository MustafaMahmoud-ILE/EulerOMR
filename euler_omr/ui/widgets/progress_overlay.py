"""Semi-transparent overlay widget with QProgressBar and cancel button."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor


class ProgressOverlay(QWidget):
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("Processing...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #f0f6f6; font-size: 16px; font-weight: bold; background: transparent;")
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setMinimumWidth(300)
        self.progress.setMaximumWidth(400)
        self.progress.setMinimumHeight(24)
        layout.addWidget(self.progress)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setMaximumWidth(100)
        self.btn_cancel.clicked.connect(self.cancelled.emit)
        layout.addWidget(self.btn_cancel, alignment=Qt.AlignmentFlag.AlignCenter)

        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(4, 16, 16, 180))
        super().paintEvent(event)

    def show_indeterminate(self, text="Processing..."):
        self.label.setText(text)
        self.progress.setRange(0, 0)
        self.resize(self.parentWidget().size() if self.parentWidget() else self.size())
        self.show()
        self.raise_()

    def show_progress(self, current, total, text=None):
        if text:
            self.label.setText(text)
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.resize(self.parentWidget().size() if self.parentWidget() else self.size())
        self.show()
        self.raise_()

    def hide_overlay(self):
        self.hide()
