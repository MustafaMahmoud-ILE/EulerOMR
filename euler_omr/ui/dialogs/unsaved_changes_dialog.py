"""Reusable unsaved changes dialog: Save / Discard / Cancel."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class UnsavedChangesDialog(QDialog):
    SAVE = 1
    DISCARD = 2
    CANCEL = 0

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Unsaved Changes")
        self.setMinimumWidth(400)
        self._result = self.CANCEL
        layout = QVBoxLayout(self)

        msg = QLabel(f"'{name}' has unsaved changes. Do you want to save before closing?")
        msg.setWordWrap(True)
        layout.addWidget(msg)

        btns = QHBoxLayout()
        btns.addStretch()

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_save)

        btn_discard = QPushButton("Discard")
        btn_discard.setStyleSheet("QPushButton { background-color: #e63946; } QPushButton:hover { background-color: #f25c69; }")
        btn_discard.clicked.connect(self._on_discard)
        btns.addWidget(btn_discard)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        layout.addLayout(btns)

    def _on_save(self):
        self._result = self.SAVE
        self.accept()

    def _on_discard(self):
        self._result = self.DISCARD
        self.accept()

    def get_result(self) -> int:
        return self._result
