"""
WizardFixerDialog: step-by-step resolution of issues across all problematic scan results.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QScrollArea, QWidget, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from euler_omr.constants import VERSION_LETTERS, OPTION_LETTERS
from euler_omr.models.scan_result import ScanResult, Issue, IssueType, PageState


class WizardFixerDialog(QDialog):
    def __init__(self, problematic_results: list[ScanResult],
                 active_questions: int, active_options: int,
                 active_versions: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wizard Fixer")
        self.setMinimumSize(800, 600)

        # Clone each problematic scan result so the user can back out if cancelled
        self._results = []
        for r in problematic_results:
            self._results.append(ScanResult(
                page_no=r.page_no,
                student_id=r.student_id,
                version=r.version,
                answers=list(r.answers),
                state=r.state,
                issues=[Issue(i.issue_type, i.field_name, i.detail, i.resolved, i.resolution) for i in r.issues],
                crop_regions=dict(r.crop_regions),
            ))

        self._active_questions = active_questions
        self._active_options = active_options
        self._active_versions = active_versions

        self._current_index = 0
        self._build_ui()
        self._load_current_page()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # === Upper/Header Info ===
        self.lbl_progress = QLabel("Problematic 1 of 1")
        self.lbl_progress.setStyleSheet("font-size: 16px; font-weight: bold; color: #2eb891;")
        main_layout.addWidget(self.lbl_progress)

        # === Issue Panel / Decision Area (Scrollable) ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #385550; background-color: #041010; }")

        panel = QWidget()
        self.panel_layout = QVBoxLayout(panel)
        self.panel_layout.setContentsMargins(16, 16, 16, 16)
        self.panel_layout.setSpacing(16)

        # Header for issues on page
        self.issues_group = QGroupBox("Issues Identified")
        self.issues_group.setStyleSheet("QGroupBox { font-weight: bold; color: #ffb703; }")
        self.issues_layout = QVBoxLayout(self.issues_group)
        self.panel_layout.addWidget(self.issues_group)

        # ID editor
        self.id_group = QGroupBox("Correct Student ID")
        id_layout = QVBoxLayout(self.id_group)
        self.txt_id = QLineEdit()
        id_layout.addWidget(self.txt_id)
        self.panel_layout.addWidget(self.id_group)

        # Version editor
        self.ver_group = QGroupBox("Correct Exam Version")
        ver_layout = QVBoxLayout(self.ver_group)
        self.cmb_version = QComboBox()
        self.cmb_version.addItem("")
        for i in range(self._active_versions):
            self.cmb_version.addItem(VERSION_LETTERS[i])
        ver_layout.addWidget(self.cmb_version)
        self.panel_layout.addWidget(self.ver_group)

        # Answers editor
        self.ans_group = QGroupBox("Correct Answer Responses")
        self.ans_layout = QVBoxLayout(self.ans_group)
        self.panel_layout.addWidget(self.ans_group)

        scroll.setWidget(panel)
        main_layout.addWidget(scroll, 1)

        # === Lower Control Panel (Back, Next/Finish, Cancel) ===
        nav_layout = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_back.clicked.connect(self._on_back)
        nav_layout.addWidget(self.btn_back)

        nav_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("background-color: #3d0c11; color: #f0f6f6; border-color: #e63946;")
        self.btn_cancel.clicked.connect(self.reject)
        nav_layout.addWidget(self.btn_cancel)

        self.btn_next = QPushButton("Next")
        self.btn_next.setStyleSheet("background-color: #05604b; color: #f0f6f6; border-color: #2eb891;")
        self.btn_next.clicked.connect(self._on_next)
        nav_layout.addWidget(self.btn_next)

        main_layout.addLayout(nav_layout)

    def _load_current_page(self):
        if not self._results:
            return

        r = self._results[self._current_index]

        # Update progress header
        self.lbl_progress.setText(f"Correcting Scan Issue: {self._current_index + 1} of {len(self._results)} (Page {r.page_no})")

        # Clear old issues list
        for i in reversed(range(self.issues_layout.count())):
            self.issues_layout.itemAt(i).widget().deleteLater()

        # Add current issues
        for issue in r.issues:
            lbl = QLabel(f"• {issue.detail} in '{issue.field_name}'")
            lbl.setStyleSheet("color: #ffb703; font-size: 13px;")
            self.issues_layout.addWidget(lbl)

        # Populate ID
        self.txt_id.setText(r.student_id)
        self.txt_id.setMaxLength(len(r.student_id) if r.student_id else 14)

        # Populate Version
        if r.version and r.version in VERSION_LETTERS[:self._active_versions]:
            idx = VERSION_LETTERS.index(r.version) + 1
            self.cmb_version.setCurrentIndex(idx)
        else:
            self.cmb_version.setCurrentIndex(0)

        # Populate Questions & Choices
        for i in reversed(range(self.ans_layout.count())):
            self.ans_layout.itemAt(i).widget().deleteLater()

        self._question_combos = []
        # Let's filter to only those questions with issues for clean, targeted decision taking
        # or list all of them but color-code those with issues.
        issue_fields = {i.field_name for i in r.issues}

        for q_idx in range(self._active_questions):
            q_field = f"q_{q_idx + 1}"
            is_problematic = q_field in issue_fields

            q_layout = QHBoxLayout()
            lbl = QLabel(f"Question {q_idx + 1}:")
            if is_problematic:
                lbl.setStyleSheet("color: #ffb703; font-weight: bold;")
            q_layout.addWidget(lbl)

            cmb = QComboBox()
            cmb.addItem("BLANK")
            for o_idx in range(self._active_options):
                cmb.addItem(OPTION_LETTERS[o_idx])

            # Set current value
            ans = r.answers[q_idx] if q_idx < len(r.answers) else ""
            if ans and ans in OPTION_LETTERS[:self._active_options]:
                cmb.setCurrentIndex(OPTION_LETTERS.index(ans) + 1)
            else:
                cmb.setCurrentIndex(0)

            q_layout.addWidget(cmb)
            self._question_combos.append(cmb)

            row_widget = QWidget()
            row_widget.setLayout(q_layout)
            self.ans_layout.addWidget(row_widget)

        # Navigation controls availability
        self.btn_back.setEnabled(self._current_index > 0)
        if self._current_index == len(self._results) - 1:
            self.btn_next.setText("Finish")
        else:
            self.btn_next.setText("Next")

    def _save_current_page(self):
        r = self._results[self._current_index]

        # Read ID corrections
        new_id = self.txt_id.text().strip()
        r.student_id = new_id

        # Read Version corrections
        ver = self.cmb_version.currentText()
        r.version = ver

        # Read Question corrections
        for q_idx, cmb in enumerate(self._question_combos):
            text = cmb.currentText()
            if text == "BLANK":
                if q_idx < len(r.answers):
                    r.answers[q_idx] = ""
            else:
                if q_idx < len(r.answers):
                    r.answers[q_idx] = text

        # Update resolution flags
        for issue in r.issues:
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

        r.update_state()

    def _on_back(self):
        if self._current_index > 0:
            self._save_current_page()
            self._current_index -= 1
            self._load_current_page()

    def _on_next(self):
        self._save_current_page()
        if self._current_index < len(self._results) - 1:
            self._current_index += 1
            self._load_current_page()
        else:
            self.accept()

    def get_results(self) -> list[ScanResult]:
        return self._results
