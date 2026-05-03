"""QPlainTextEdit subclass styled as a terminal; color-coded by log level."""
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtGui import QTextCharFormat, QColor, QFont
from PySide6.QtCore import Qt, Slot


LOG_COLORS = {
    "DEBUG": "#6c7f7d",
    "INFO": "#f0f6f6",
    "WARNING": "#ffb703",
    "ERROR": "#e63946",
    "CRITICAL": "#e63946",
}


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 2, 0, 2)
        toolbar.setSpacing(6)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedHeight(28)
        self.btn_clear.setMinimumWidth(85)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_copy = QPushButton("Copy")
        self.btn_copy.setFixedHeight(28)
        self.btn_copy.setMinimumWidth(85)
        self.btn_copy.clicked.connect(self._copy)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_clear)
        toolbar.addWidget(self.btn_copy)
        layout.addLayout(toolbar)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(5000)
        self.text_edit.setStyleSheet(
            "QPlainTextEdit { background-color: #041010; color: #f0f6f6; "
            "border: 1px solid #385550; font-family: 'Courier New', monospace; font-size: 11px; }"
        )
        layout.addWidget(self.text_edit)

    @Slot(str, str)
    def append_log(self, message: str, level: str = "INFO"):
        fmt = QTextCharFormat()
        color = LOG_COLORS.get(level.upper(), "#f0f6f6")
        fmt.setForeground(QColor(color))
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(message + "\n", fmt)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    def _clear(self):
        self.text_edit.clear()

    def _copy(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.text_edit.toPlainText())
