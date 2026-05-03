"""
WizardFixerDialog: step-by-step resolution of issues across all problematic scan results with crops.
"""
import os
import cv2
import pypdfium2 as pdfium
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QScrollArea, QWidget, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap

from euler_omr.constants import VERSION_LETTERS, OPTION_LETTERS
from euler_omr.models.scan_result import ScanResult, Issue, IssueType, PageState
from euler_omr.core.scan_reader import ScanReader


class WizardFixerDialog(QDialog):
    def __init__(self, problematic_results: list[ScanResult],
                 active_questions: int, active_options: int,
                 active_versions: int, scans_pdf_path=None,
                 scans_pdf_bytes=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wizard Fixer")
        self.setMinimumSize(850, 700)

        self._scans_pdf_path = scans_pdf_path
        self._scans_pdf_bytes = scans_pdf_bytes

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
        self.id_layout = QVBoxLayout(self.id_group)
        self.txt_id = QLineEdit()
        self.id_layout.addWidget(self.txt_id)
        self.panel_layout.addWidget(self.id_group)

        # Version editor
        self.ver_group = QGroupBox("Correct Exam Version")
        self.ver_layout = QVBoxLayout(self.ver_group)
        self.cmb_version = QComboBox()
        self.cmb_version.addItem("")
        for i in range(self._active_versions):
            self.cmb_version.addItem(VERSION_LETTERS[i])
        self.ver_layout.addWidget(self.cmb_version)
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

    def _get_page_image(self, page_no):
        img_bgr = None
        if self._scans_pdf_path and os.path.exists(self._scans_pdf_path):
            try:
                img_bgr = ScanReader.load_pdf_page(self._scans_pdf_path, page_no - 1)
            except Exception as e:
                print(f"Failed to extract page image from file: {e}")
        elif self._scans_pdf_bytes:
            try:
                doc = pdfium.PdfDocument(self._scans_pdf_bytes)
                page = doc[page_no - 1]
                bitmap = page.render(scale=200 / 72.0)
                img = bitmap.to_numpy()
                if img.shape[2] == 4:
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                elif img.shape[2] == 3:
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                doc.close()
            except Exception as e:
                print(f"Failed to extract page image from bytes: {e}")

        # Correct orientation and apply perspective transformation to the page
        if img_bgr is not None:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            sr = ScanReader(14, 4, self._active_questions, self._active_options, self._active_versions)
            marks = sr._find_corner_marks(gray)
            if marks is not None:
                rotation = sr._detect_orientation(marks)
                if rotation != 0:
                    gray = sr._rotate_image(gray, rotation)
                    img_bgr = sr._rotate_image(img_bgr, rotation)
                    marks = sr._find_corner_marks(gray)
                if marks is not None:
                    img_bgr = sr._perspective_correct(img_bgr, marks)
        return img_bgr

    def _np_to_pixmap(self, img_bgr):
        if img_bgr is None:
            return QPixmap()
        h, w, ch = img_bgr.shape
        new_w = int(w * 0.75)
        new_h = int(h * 0.75)
        img_bgr = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        h, w, ch = img_bgr.shape

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(img_rgb.data, w, h, w * ch, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg)

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

        # Clear previous crops from layouts
        if hasattr(self, "lbl_table_crop") and self.lbl_table_crop:
            self.lbl_table_crop.deleteLater()
            self.lbl_table_crop = None
        if hasattr(self, "lbl_id_crop") and self.lbl_id_crop:
            self.lbl_id_crop.deleteLater()
            self.lbl_id_crop = None
        if hasattr(self, "lbl_ver_crop") and self.lbl_ver_crop:
            self.lbl_ver_crop.deleteLater()
            self.lbl_ver_crop = None

        # Extract current page image for cropping
        page_img = self._get_page_image(r.page_no)

        if page_img is not None:
            h, w = page_img.shape[:2]

            # Tight Table crop: [433:688, 157:805]
            table_crop = page_img[433:688, 157:805]
            self.lbl_table_crop = QLabel()
            self.lbl_table_crop.setPixmap(self._np_to_pixmap(table_crop))
            self.lbl_table_crop.setStyleSheet("border: none; background: transparent;")
            self.id_layout.insertWidget(0, self.lbl_table_crop)

            # Dynamic Tight ID crop based on digits
            id_digits = len(r.student_id) if r.student_id else 14
            id_x_start = 1479 - (id_digits - 1) * 47.24
            id_x_min = int(max(0, id_x_start - 35))
            id_x_max = int(min(w, 1515))

            id_crop = page_img[268:660, id_x_min:id_x_max]
            self.lbl_id_crop = QLabel()
            self.lbl_id_crop.setPixmap(self._np_to_pixmap(id_crop))
            self.lbl_id_crop.setStyleSheet("border: none; background: transparent;")
            self.id_layout.insertWidget(1, self.lbl_id_crop)

            # Tight Version crop: [755:820, 157:565]
            ver_crop = page_img[755:820, 157:565]
            self.lbl_ver_crop = QLabel()
            self.lbl_ver_crop.setPixmap(self._np_to_pixmap(ver_crop))
            self.lbl_ver_crop.setStyleSheet("border: none; background: transparent;")
            self.ver_layout.insertWidget(0, self.lbl_ver_crop)

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

            # Show crop for this question if it exists in the regions dictionary
            if page_img is not None and str(q_idx) in r.crop_regions:
                rect = r.crop_regions[str(q_idx)]
                cy_start, cy_end = rect.get("y_start", 0), rect.get("y_end", 0)
                cx_start, cx_end = rect.get("x_start", 0), rect.get("x_end", 0)
                if cy_end > cy_start and cx_end > cx_start:
                    q_crop = page_img[cy_start:cy_end, cx_start:cx_end]
                    lbl_q_crop = QLabel()
                    lbl_q_crop.setPixmap(self._np_to_pixmap(q_crop))
                    lbl_q_crop.setStyleSheet("border: none; background: transparent;")
                    q_layout.addWidget(lbl_q_crop)
            elif page_img is not None and q_idx in r.crop_regions:
                rect = r.crop_regions[q_idx]
                cy_start, cy_end = rect.get("y_start", 0), rect.get("y_end", 0)
                cx_start, cx_end = rect.get("x_start", 0), rect.get("x_end", 0)
                if cy_end > cy_start and cx_end > cx_start:
                    q_crop = page_img[cy_start:cy_end, cx_start:cx_end]
                    lbl_q_crop = QLabel()
                    lbl_q_crop.setPixmap(self._np_to_pixmap(q_crop))
                    lbl_q_crop.setStyleSheet("border: none; background: transparent;")
                    q_layout.addWidget(lbl_q_crop)

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
