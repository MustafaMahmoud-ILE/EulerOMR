"""ReviewPageDialog: left nav with color-coded issues; right panel with crops and corrections."""
import os
import cv2
import math
import numpy as np
import pypdfium2 as pdfium
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap

from euler_omr.constants import VERSION_LETTERS, OPTION_LETTERS
from euler_omr.models.scan_result import ScanResult, Issue, IssueType, PageState
from euler_omr.core.scan_reader import ScanReader


class ReviewPageDialog(QDialog):
    def __init__(self, result: ScanResult, active_questions: int,
                 active_options: int, active_versions: int,
                 scans_pdf_path: str = None, scans_pdf_bytes: bytes = None, 
                 num_questions: int = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Review Page {result.page_no}")
        self.setMinimumSize(950, 700)
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
        self.num_questions = num_questions if num_questions is not None else active_questions

        # Load original image for page crops
        self._page_img = None
        img_bgr = None

        if scans_pdf_path and os.path.exists(scans_pdf_path):
            try:
                img_bgr = ScanReader.load_pdf_page(scans_pdf_path, result.page_no - 1)
            except Exception as e:
                print(f"Failed to extract page image from file for cropping: {e}")
        elif scans_pdf_bytes:
            try:
                doc = pdfium.PdfDocument(scans_pdf_bytes)
                page = doc[result.page_no - 1]
                bitmap = page.render(scale=200 / 72.0)
                img = bitmap.to_numpy()
                if img.shape[2] == 4:
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                elif img.shape[2] == 3:
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                doc.close()
            except Exception as e:
                print(f"Failed to extract page image from bytes for cropping: {e}")

        # Correct orientation and apply perspective transformation to the page
        if img_bgr is not None:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            sr = ScanReader(14, 4, active_questions, active_options, active_versions)
            marks = sr._find_corner_marks(gray)
            if marks is not None:
                rotation = sr._detect_orientation(marks)
                if rotation != 0:
                    gray = sr._rotate_image(gray, rotation)
                    img_bgr = sr._rotate_image(img_bgr, rotation)
                    marks = sr._find_corner_marks(gray)
                if marks is not None:
                    img_bgr = sr._perspective_correct(img_bgr, marks)
            self._page_img = img_bgr

        self._build_ui()

    def _np_to_pixmap(self, img_bgr):
        if img_bgr is None:
            return QPixmap()
        h, w, ch = img_bgr.shape
        # resize down to 75% of original (2.5x previous 30% scale)
        new_w = int(w * 0.75)
        new_h = int(h * 0.75)
        img_bgr = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        h, w, ch = img_bgr.shape

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(img_rgb.data, w, h, w * ch, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg)

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

        # Show table and ID crops
        if self._page_img is not None:
            h, w = self._page_img.shape[:2]
            # Tight Table crop: [433:688, 157:805]
            table_crop = self._page_img[433:688, 157:805]
            lbl_table_crop = QLabel()
            lbl_table_crop.setPixmap(self._np_to_pixmap(table_crop))
            lbl_table_crop.setStyleSheet("border: none; background: transparent;")
            id_layout.addWidget(QLabel("Written Data (Name, Course, Date):"))
            id_layout.addWidget(lbl_table_crop)

            # Dynamic Tight ID crop based on digits
            id_digits = len(self._result.student_id) if self._result.student_id else 14
            id_x_start = 1479 - (id_digits - 1) * 47.24
            id_x_min = int(max(0, id_x_start - 35))
            id_x_max = int(min(w, 1515))

            id_crop = self._page_img[268:660, id_x_min:id_x_max]
            lbl_id_crop = QLabel()
            lbl_id_crop.setPixmap(self._np_to_pixmap(id_crop))
            lbl_id_crop.setStyleSheet("border: none; background: transparent;")
            id_layout.addWidget(QLabel("Student ID Bubbles:"))
            id_layout.addWidget(lbl_id_crop)

        id_layout.addWidget(QLabel("Student ID Input:"))
        self.txt_id = QLineEdit(self._result.student_id)
        self.txt_id.setMaxLength(len(self._result.student_id) if self._result.student_id else 14)
        id_layout.addWidget(self.txt_id)
        id_layout.addStretch()
        self.stack.addWidget(id_page)

        # Version page
        ver_page = QWidget()
        ver_layout = QVBoxLayout(ver_page)

        if self._page_img is not None:
            h, w = self._page_img.shape[:2]
            # Tight Version crop: [755:820, 157:565]
            ver_crop = self._page_img[755:820, 157:565]
            lbl_ver_crop = QLabel()
            lbl_ver_crop.setPixmap(self._np_to_pixmap(ver_crop))
            lbl_ver_crop.setStyleSheet("border: none; background: transparent;")
            ver_layout.addWidget(QLabel("Exam Version Bubbles:"))
            ver_layout.addWidget(lbl_ver_crop)

        ver_layout.addWidget(QLabel("Exam Version Selection:"))
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
        rows_per_col = math.ceil(self.num_questions / 3)
        q_y_start = 868.5
        q_x_starts = [204.5, 650.7, 1097.0]
        bubble_step_px = 47.24

        for q_idx in range(self.active_questions):
            q_page = QWidget()
            q_layout = QVBoxLayout(q_page)

            if self._page_img is not None:
                h, w = self._page_img.shape[:2]
                col_idx = q_idx // rows_per_col
                row_idx = q_idx % rows_per_col
                if col_idx < len(q_x_starts):
                    base_x = q_x_starts[col_idx]
                    y = int(q_y_start + row_idx * 39.37)
                    cx_start = int(max(0, base_x - 35))
                    cx_end = int(min(w, base_x + self.active_options * bubble_step_px + 15))
                    cy_start = int(max(0, y - 22))
                    cy_end = int(min(h, y + 22))

                    q_crop = self._page_img[cy_start:cy_end, cx_start:cx_end]
                    lbl_q_crop = QLabel()
                    lbl_q_crop.setPixmap(self._np_to_pixmap(q_crop))
                    lbl_q_crop.setStyleSheet("border: none; background: transparent;")
                    q_layout.addWidget(QLabel(f"Question {q_idx + 1} Bubbles:"))
                    q_layout.addWidget(lbl_q_crop)

            q_layout.addWidget(QLabel(f"Question {q_idx + 1} Correct Choice:"))
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
