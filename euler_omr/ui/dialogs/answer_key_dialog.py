"""AnswerKeyDialog: version tabs; question rows with option checkboxes; save/ignore."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QScrollArea,
    QPushButton, QCheckBox, QLabel, QGridLayout, QGroupBox
)
from PySide6.QtCore import Qt
from euler_omr.constants import VERSION_LETTERS, OPTION_LETTERS
from euler_omr.models.answer_key import AnswerKey


class AnswerKeyDialog(QDialog):
    def __init__(self, active_versions, active_questions, active_options,
                 answer_key: AnswerKey | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Answer Keys")
        self.setMinimumSize(600, 500)
        self.active_versions = active_versions
        self.active_questions = active_questions
        self.active_options = active_options
        self._answer_key = answer_key or AnswerKey()
        self._checkboxes: dict[str, dict[int, list[QCheckBox]]] = {}
        self._error_labels: dict[str, dict[int, QLabel]] = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        for v_idx in range(self.active_versions):
            ver = VERSION_LETTERS[v_idx]
            tab = self._create_version_tab(ver)
            self.tabs.addTab(tab, f"Version {ver}")
        layout.addWidget(self.tabs)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_save = QPushButton("Save Answer Keys")
        self.btn_save.clicked.connect(self._validate_and_save)
        btns.addWidget(self.btn_save)
        self.btn_ignore = QPushButton("Ignore")
        self.btn_ignore.clicked.connect(self.reject)
        btns.addWidget(self.btn_ignore)
        layout.addLayout(btns)

    def _create_version_tab(self, version: str) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(4)

        self._checkboxes[version] = {}
        self._error_labels[version] = {}

        # Header
        grid.addWidget(QLabel("Q#"), 0, 0)
        for o_idx in range(self.active_options):
            lbl = QLabel(OPTION_LETTERS[o_idx])
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl, 0, o_idx + 1)

        existing = self._answer_key.get_version_keys(version)

        for q_idx in range(self.active_questions):
            row = q_idx + 1
            grid.addWidget(QLabel(f"Q{q_idx + 1}"), row, 0)
            cbs = []
            prev_answers = existing.get(q_idx, set())
            for o_idx in range(self.active_options):
                cb = QCheckBox()
                if OPTION_LETTERS[o_idx] in prev_answers:
                    cb.setChecked(True)
                grid.addWidget(cb, row, o_idx + 1, alignment=Qt.AlignmentFlag.AlignCenter)
                cbs.append(cb)
            self._checkboxes[version][q_idx] = cbs

            err = QLabel()
            err.setObjectName("error_label")
            err.hide()
            grid.addWidget(err, row, self.active_options + 1)
            self._error_labels[version][q_idx] = err

        scroll.setWidget(content)
        return scroll

    def _validate_and_save(self):
        valid = True
        for ver, questions in self._checkboxes.items():
            for q_idx, cbs in questions.items():
                selected = [OPTION_LETTERS[i] for i, cb in enumerate(cbs) if cb.isChecked()]
                err_lbl = self._error_labels[ver][q_idx]
                if not selected:
                    err_lbl.setText("Select at least one")
                    err_lbl.show()
                    valid = False
                else:
                    err_lbl.hide()
        if valid:
            self.accept()

    def get_answer_key(self) -> AnswerKey:
        ak = AnswerKey()
        for ver, questions in self._checkboxes.items():
            for q_idx, cbs in questions.items():
                selected = {OPTION_LETTERS[i] for i, cb in enumerate(cbs) if cb.isChecked()}
                if selected:
                    ak.set_answer(ver, q_idx, selected)
        return ak
