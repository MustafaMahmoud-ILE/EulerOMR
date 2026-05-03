"""ReviewPageDialog: left nav with color-coded issues; right panel with crops and corrections."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from euler_omr.constants import VERSION_LETTERS, OPTION_LETTERS
from euler_omr.models.scan_result import ScanResult, Issue, IssueType, PageState


class ReviewPageDialog(QDialog):
    def __init__(self, result: ScanResult, active_questions: int,
                 active_options: int, active_versions: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Review Page {result.page_no}")
        self.setMinimumSize(700, 500)
        self._result = ScanResult(
            page_no=result.page_no,
            student_id=result.student_id,
            version=result.version,
            answers=list(result.answers),
            state=result.state,
            issues=[Issue(i.issue_type, i.field_name, i.detail, i.resolved, i.resolution) for i in result.issues],
            crop_regions=dict(result.crop_regions),
        )
        self.active_questions = active_questions
        self.active_options = active_options
        self.active_versions = active_versions
        self._corrections = {}
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        # === Left Nav ===
        self.nav_list = QListWidget()
        self.nav_list.setMaximumWidth(180)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        # Build nav items
        items = ["ID and Written Data", "Version"]
        for i in range(self.active_questions):
            items.append(f"Q{i + 1}")

        issue_fields = {i.field_name for i in self._result.issues}
        resolved_fields = {i.field_name for i in self._result.issues if i.resolved}

        for idx, text in enumerate(items):
            item = QListWidgetItem(text)
            # Determine color
            field = self._get_field_for_nav(idx)
            if any(f in issue_fields and f not in resolved_fields for f in (field if isinstance(field, list) else [field])):
                item.setForeground(QColor("#ffb703"))
            elif any(f in resolved_fields for f in (field if isinstance(field, list) else [field])):
                item.setForeground(QColor("#09a964"))
            self.nav_list.addItem(item)

        layout.addWidget(self.nav_list)

        # === Right Panel (Stacked) ===
        self.stack = QStackedWidget()

        # ID page
        id_page = QWidget()
        id_layout = QVBoxLayout(id_page)
        id_layout.addWidget(QLabel("Student ID:"))
        self.txt_id = QLineEdit(self._result.student_id)
        self.txt_id.setMaxLength(len(self._result.student_id) if self._result.student_id else 14)
        id_layout.addWidget(self.txt_id)
        id_layout.addStretch()
        self.stack.addWidget(id_page)

        # Version page
        ver_page = QWidget()
        ver_layout = QVBoxLayout(ver_page)
        ver_layout.addWidget(QLabel("Exam Version:"))
        self.cmb_version = QComboBox()
        self.cmb_version.addItem("")
        for i in range(self.active_versions):
            self.cmb_version.addItem(VERSION_LETTERS[i])
        if self._result.version:
            idx = VERSION_LETTERS.index(self._result.version) + 1 if self._result.version in VERSION_LETTERS else 0
            self.cmb_version.setCurrentIndex(idx)
        ver_layout.addWidget(self.cmb_version)
        ver_layout.addStretch()
        self.stack.addWidget(ver_page)

        # Question pages
        self._question_combos = []
        for q_idx in range(self.active_questions):
            q_page = QWidget()
            q_layout = QVBoxLayout(q_page)
            q_layout.addWidget(QLabel(f"Question {q_idx + 1}:"))
            cmb = QComboBox()
            cmb.addItem("BLANK")
            for o_idx in range(self.active_options):
                cmb.addItem(OPTION_LETTERS[o_idx])
            ans = self._result.answers[q_idx] if q_idx < len(self._result.answers) else ""
            if ans and ans in OPTION_LETTERS[:self.active_options]:
                cmb.setCurrentIndex(OPTION_LETTERS.index(ans) + 1)
            else:
                cmb.setCurrentIndex(0)
            q_layout.addWidget(cmb)
            q_layout.addStretch()
            self._question_combos.append(cmb)
            self.stack.addWidget(q_page)

        layout.addWidget(self.stack, 1)

        # Buttons at bottom
        btn_layout = QVBoxLayout()
        btn_layout.addStretch()
        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("Save Changes")
        self.btn_save.clicked.connect(self._save)
        btn_row.addWidget(self.btn_save)
        self.btn_ignore = QPushButton("Ignore Changes")
        self.btn_ignore.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_ignore)
        btn_layout.addLayout(btn_row)
        layout.addLayout(btn_layout)

        self.nav_list.setCurrentRow(0)

    def _get_field_for_nav(self, idx):
        if idx == 0:
            return [f"id_digit_{i}" for i in range(14)]
        elif idx == 1:
            return ["version"]
        else:
            return [f"q_{idx - 1}"]

    def _on_nav_changed(self, row):
        self.stack.setCurrentIndex(row)

    def _save(self):
        # Apply corrections
        new_id = self.txt_id.text()
        self._result.student_id = new_id

        ver = self.cmb_version.currentText()
        self._result.version = ver

        for q_idx, cmb in enumerate(self._question_combos):
            text = cmb.currentText()
            if text == "BLANK":
                if q_idx < len(self._result.answers):
                    self._result.answers[q_idx] = ""
            else:
                if q_idx < len(self._result.answers):
                    self._result.answers[q_idx] = text

        # Mark issues as resolved
        for issue in self._result.issues:
            if issue.issue_type in (IssueType.MISSING_DIGIT, IssueType.MULTI_DIGIT):
                col = int(issue.field_name.split("_")[-1])
                if col < len(new_id) and new_id[col] != "*":
                    issue.resolved = True
                    issue.resolution = new_id[col]
            elif issue.issue_type in (IssueType.MISSING_VERSION, IssueType.MULTI_VERSION):
                if ver:
                    issue.resolved = True
                    issue.resolution = ver
            elif issue.issue_type in (IssueType.MISSING_ANSWER, IssueType.MULTI_ANSWER):
                q_num = int(issue.field_name.split("_")[1])
                q_idx = q_num - 1
                if q_idx < len(self._question_combos):
                    issue.resolved = True
                    issue.resolution = self._question_combos[q_idx].currentText()

        self._result.update_state()
        self.accept()

    def get_result(self) -> ScanResult:
        return self._result
