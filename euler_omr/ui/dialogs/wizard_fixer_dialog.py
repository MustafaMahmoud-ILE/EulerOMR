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
                 active_versions: int, num_questions=None, scans_pdf_path=None,
                 scans_pdf_bytes=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wizard Fixer")
        self.setMinimumSize(640, 525)

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
        self._num_questions = num_questions if num_questions is not None else active_questions

        self._current_index = 0
        self._pdf_doc = None
        self._last_img_cache = (None, None) # (page_no, img)
        
        if self._scans_pdf_bytes:
            try:
                self._pdf_doc = pdfium.PdfDocument(self._scans_pdf_bytes)
            except Exception as e:
                print(f"WizardFixer: Failed to open PDF from bytes: {e}")
        elif self._scans_pdf_path and os.path.exists(self._scans_pdf_path):
            try:
                self._pdf_doc = pdfium.PdfDocument(self._scans_pdf_path)
            except Exception as e:
                print(f"WizardFixer: Failed to open PDF from path: {e}")

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
        if self._last_img_cache[0] == page_no:
            return self._last_img_cache[1]

        img_bgr = None
        if self._pdf_doc:
            try:
                page = self._pdf_doc[page_no - 1]
                bitmap = page.render(scale=200 / 72.0)
                img = bitmap.to_numpy()
                if img.shape[2] == 4:
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                elif img.shape[2] == 3:
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"Failed to extract page image {page_no}: {e}")
        
        if img_bgr is None and self._scans_pdf_path and os.path.exists(self._scans_pdf_path):
            # Fallback if doc failed or we are using path-based loading
            try:
                img_bgr = ScanReader.load_pdf_page(self._scans_pdf_path, page_no - 1)
            except Exception as e:
                print(f"Failed to extract page image from file: {e}")

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
        
        self._last_img_cache = (page_no, img_bgr)
        return img_bgr

    def _clear_layout(self, layout):
        if not layout: return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout:
                    self._clear_layout(sub_layout)

    def _np_to_pixmap(self, img_bgr, scale=0.75):
        if img_bgr is None:
            return QPixmap()
        h, w, ch = img_bgr.shape
        new_w = int(w * scale)
        new_h = int(h * scale)
        img_bgr = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        h, w, ch = img_bgr.shape

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(img_rgb.data, w, h, w * ch, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg)

    def _load_current_page(self):
        if not self._results:
            return

        from PySide6.QtGui import QCursor
        self.setCursor(QCursor(Qt.WaitCursor))
        try:
            r = self._results[self._current_index]

            # Update progress header
            self.lbl_progress.setText(f"Correcting Scan Issue: {self._current_index + 1} of {len(self._results)} (Page {r.page_no})")

            # Clear old issues list
            self._clear_layout(self.issues_layout)

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

            issue_fields = {i.field_name for i in r.issues}

            has_id_issue = any(f == "student_id" or f.startswith("id_") or f.startswith("student_id_") for f in issue_fields)
            has_ver_issue = any(f == "version" or f.startswith("version_") for f in issue_fields)
            has_ans_issue = any(f.startswith("q_") for f in issue_fields)

            # Only show the section that has the issue
            self.id_group.setVisible(has_id_issue)
            self.ver_group.setVisible(has_ver_issue)
            self.ans_group.setVisible(has_ans_issue)

            # Extract current page image for cropping
            page_img = self._get_page_image(r.page_no)

            if page_img is not None:
                h, w = page_img.shape[:2]

                # Table crop: [433:688, 157:805]
                if has_id_issue:
                    r_table = r.crop_regions.get("table", {"y_start": 433, "y_end": 688, "x_start": 157, "x_end": 805})
                    table_crop = page_img[r_table["y_start"]:r_table["y_end"], r_table["x_start"]:r_table["x_end"]]
                    self.lbl_table_crop = QLabel()
                    self.lbl_table_crop.setPixmap(self._np_to_pixmap(table_crop, scale=0.5625))
                    self.lbl_table_crop.setStyleSheet("border: none; background: transparent;")
                    self.id_layout.insertWidget(0, self.lbl_table_crop)

                    # ID crop
                    if "id" in r.crop_regions:
                        r_id = r.crop_regions["id"]
                        id_crop = page_img[r_id["y_start"]:r_id["y_end"], r_id["x_start"]:r_id["x_end"]]
                    else:
                        id_digits = len(r.student_id) if r.student_id else 14
                        id_x_start = 1479 - (id_digits - 1) * 47.24
                        id_x_min = int(max(0, id_x_start - 35))
                        id_x_max = int(min(w, 1515))
                        id_crop = page_img[268:660, id_x_min:id_x_max]

                    self.lbl_id_crop = QLabel()
                    self.lbl_id_crop.setPixmap(self._np_to_pixmap(id_crop, scale=0.5625))
                    self.lbl_id_crop.setStyleSheet("border: none; background: transparent;")
                    self.id_layout.insertWidget(1, self.lbl_id_crop)

                # Version crop
                if has_ver_issue:
                    if "version" in r.crop_regions:
                        r_v = r.crop_regions["version"]
                        ver_crop = page_img[r_v["y_start"]:r_v["y_end"], r_v["x_start"]:r_v["x_end"]]
                    else:
                        ver_crop = page_img[755:820, 157:700]

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
            self._clear_layout(self.ans_layout)

            self._question_combos = {}

            for q_idx in range(self._active_questions):
                q_field = f"q_{q_idx + 1}"
                is_problematic = q_field in issue_fields

                # Show ONLY the specific question sections that have the issue
                if not is_problematic:
                    continue

                q_layout = QHBoxLayout()
                lbl = QLabel(f"Question {q_idx + 1}:")
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
                self._question_combos[q_idx] = cmb

                # Show crop for this question
                if page_img is not None:
                    q_key = str(q_idx)
                    if q_key in r.crop_regions:
                        r_q = r.crop_regions[q_key]
                        cx_start, cx_end = r_q["x_start"], r_q["x_end"]
                        cy_start, cy_end = r_q["y_start"], r_q["y_end"]
                    else:
                        import math
                        rows_per_col = math.ceil(self._num_questions / 3)
                        q_y_start = 868.5
                        q_x_starts = [204.5, 650.7, 1097.0]
                        bubble_step_px = 0.6 * (200 / 2.54)
                        
                        col_idx = q_idx // rows_per_col
                        row_idx = q_idx % rows_per_col
                        if col_idx < len(q_x_starts):
                            base_x = q_x_starts[col_idx]
                            y = int(q_y_start + row_idx * 39.37)
                            cx_start = int(max(0, base_x - 35))
                            cx_end = int(min(w, base_x + self._active_options * bubble_step_px + 15))
                            cy_start = int(max(0, y - 22))
                            cy_end = int(min(h, y + 22))
                        else:
                            cx_start, cx_end, cy_start, cy_end = 0, 0, 0, 0
                    
                    if cy_end > cy_start and cx_end > cx_start:
                        q_crop = page_img[cy_start:cy_end, cx_start:cx_end]
                        lbl_q_crop = QLabel()
                        lbl_q_crop.setPixmap(self._np_to_pixmap(q_crop))
                        lbl_q_crop.setStyleSheet("border: none; background: transparent;")
                        q_layout.addWidget(lbl_q_crop)

                row_widget = QWidget()
                row_widget.setLayout(q_layout)
                self.ans_layout.addWidget(row_widget)
        
        finally:
            self.unsetCursor()

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
        for q_idx, cmb in self._question_combos.items():
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
                if q_idx in self._question_combos:
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

    def closeEvent(self, event):
        if self._pdf_doc:
            self._pdf_doc.close()
            self._pdf_doc = None
        super().closeEvent(event)
