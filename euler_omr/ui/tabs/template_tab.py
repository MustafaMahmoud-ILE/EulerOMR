"""TemplateTab: left form panel; right PDF preview; bottom log panel; dirty-state tracking."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QPushButton, QSplitter, QFileDialog, QFormLayout, QGroupBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QThreadPool
from PySide6.QtGui import QPixmap, QImage

from euler_omr.constants import (
    ID_DIGITS_MIN, ID_DIGITS_MAX, ID_DIGITS_DEFAULT,
    NUM_VERSIONS_MIN, NUM_VERSIONS_MAX, NUM_VERSIONS_DEFAULT,
    NUM_QUESTIONS_MIN, NUM_QUESTIONS_MAX, NUM_QUESTIONS_DEFAULT,
    NUM_OPTIONS_MIN, NUM_OPTIONS_MAX, NUM_OPTIONS_DEFAULT,
    EOMRT_FILTER, PDF_FILTER, IMAGE_FILTER,
)
from euler_omr.models.template_model import TemplateConfig
from euler_omr.workers.compile_worker import CompileWorker
from euler_omr.file_io.eomrt_handler import EomrtHandler
from euler_omr.ui.widgets.log_panel import LogPanel
from euler_omr.ui.widgets.image_preview import ImagePreview
from euler_omr.ui.widgets.progress_overlay import ProgressOverlay


class TemplateTab(QWidget):
    dirty_changed = Signal(bool)
    title_changed = Signal(str)

    def __init__(self, config: TemplateConfig | None = None, file_path: str | None = None, parent=None):
        super().__init__(parent)
        self.config = config or TemplateConfig()
        self.file_path = file_path
        self._dirty = False
        self._compiled_pdf_bytes: bytes | None = None
        self._logo_bytes: bytes | None = None
        self._logo_ext: str = "png"
        self._logo_filename: str | None = None
        self._worker: CompileWorker | None = None
        self._build_ui()
        self._load_config()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)

        vsplit = QSplitter(Qt.Orientation.Vertical)
        hsplit = QSplitter(Qt.Orientation.Horizontal)

        # === Left Form Panel ===
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 8, 8)

        form_group = QGroupBox("Template Settings")
        form = QFormLayout(form_group)

        self.txt_institution = QLineEdit()
        self.txt_institution.setMaxLength(80)
        self.txt_institution.setPlaceholderText("Institution Name")
        self.txt_institution.textChanged.connect(self._mark_dirty)
        form.addRow("Institute Name:", self.txt_institution)

        logo_row = QHBoxLayout()
        self.btn_logo = QPushButton("Browse...")
        self.btn_logo.clicked.connect(self._browse_logo)
        self.lbl_logo_preview = QLabel()
        self.lbl_logo_preview.setFixedSize(20, 20)
        self.lbl_logo_preview.setScaledContents(True)
        logo_row.addWidget(self.btn_logo)
        logo_row.addWidget(self.lbl_logo_preview)
        logo_row.addStretch()
        form.addRow("Institute Logo:", logo_row)

        self.sp_id_digits = QSpinBox()
        self.sp_id_digits.setRange(ID_DIGITS_MIN, ID_DIGITS_MAX)
        self.sp_id_digits.setValue(ID_DIGITS_DEFAULT)
        self.sp_id_digits.valueChanged.connect(self._mark_dirty)
        form.addRow("ID Digit Length:", self.sp_id_digits)

        self.sp_versions = QSpinBox()
        self.sp_versions.setRange(NUM_VERSIONS_MIN, NUM_VERSIONS_MAX)
        self.sp_versions.setValue(NUM_VERSIONS_DEFAULT)
        self.sp_versions.valueChanged.connect(self._mark_dirty)
        form.addRow("Number of Versions:", self.sp_versions)

        self.sp_questions = QSpinBox()
        self.sp_questions.setRange(NUM_QUESTIONS_MIN, NUM_QUESTIONS_MAX)
        self.sp_questions.setValue(NUM_QUESTIONS_DEFAULT)
        self.sp_questions.setSingleStep(3)
        self.sp_questions.valueChanged.connect(self._on_questions_changed)
        form.addRow("Number of Questions:", self.sp_questions)

        self.lbl_q_error = QLabel()
        self.lbl_q_error.setObjectName("error_label")
        self.lbl_q_error.hide()
        form.addRow("", self.lbl_q_error)

        self.sp_options = QSpinBox()
        self.sp_options.setRange(NUM_OPTIONS_MIN, NUM_OPTIONS_MAX)
        self.sp_options.setValue(NUM_OPTIONS_DEFAULT)
        self.sp_options.valueChanged.connect(self._mark_dirty)
        form.addRow("Number of Options:", self.sp_options)

        left_layout.addWidget(form_group)
        left_layout.addSpacing(12)

        # Buttons
        self.btn_compile = QPushButton("Compile and Save PDF")
        self.btn_compile.setMinimumHeight(36)
        self.btn_compile.setStyleSheet("QPushButton { font-weight: bold; }")
        self.btn_compile.clicked.connect(self._compile)
        left_layout.addWidget(self.btn_compile)

        self.btn_save = QPushButton("Save Template")
        self.btn_save.setMinimumHeight(32)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_template)
        left_layout.addWidget(self.btn_save)

        left_layout.addStretch()
        left.setMaximumWidth(380)

        # === Right Preview Panel ===
        self.preview = ImagePreview()

        hsplit.addWidget(left)
        hsplit.addWidget(self.preview)
        hsplit.setStretchFactor(0, 0)
        hsplit.setStretchFactor(1, 1)

        # === Bottom Log Panel ===
        self.log_panel = LogPanel()

        vsplit.addWidget(hsplit)
        vsplit.addWidget(self.log_panel)
        vsplit.setStretchFactor(0, 3)
        vsplit.setStretchFactor(1, 1)

        main.addWidget(vsplit)

        # Overlay
        self.overlay = ProgressOverlay(self)
        self.overlay.cancelled.connect(self._cancel_compile)

    def _load_config(self):
        self.txt_institution.setText(self.config.institution_name)
        self.sp_id_digits.setValue(self.config.id_digits)
        self.sp_versions.setValue(self.config.num_versions)
        self.sp_questions.setValue(self.config.num_questions)
        self.sp_options.setValue(self.config.num_options)
        self._dirty = False

    def _get_config(self) -> TemplateConfig:
        return TemplateConfig(
            institution_name=self.txt_institution.text(),
            id_digits=self.sp_id_digits.value(),
            num_versions=self.sp_versions.value(),
            num_questions=self.sp_questions.value(),
            num_options=self.sp_options.value(),
        )

    def _mark_dirty(self):
        self._dirty = True
        self.dirty_changed.emit(True)
        self.title_changed.emit(self.tab_title())

    def _on_questions_changed(self, val):
        if val % 3 != 0:
            self.lbl_q_error.setText("Must be divisible by 3")
            self.lbl_q_error.show()
        else:
            self.lbl_q_error.hide()
        self._mark_dirty()

    def _browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Logo", os.path.expanduser("~/Pictures"), IMAGE_FILTER)
        if path:
            with open(path, "rb") as f:
                self._logo_bytes = f.read()
            self._logo_ext = os.path.splitext(path)[1].lstrip(".")
            self._logo_filename = os.path.basename(path)
            pixmap = QPixmap(path).scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio)
            self.lbl_logo_preview.setPixmap(pixmap)
            self._mark_dirty()

    def _compile(self):
        q = self.sp_questions.value()
        if q % 3 != 0:
            self.log_panel.append_log("Error: Number of questions must be divisible by 3", "ERROR")
            return

        config = self._get_config()
        self._set_form_enabled(False)
        self.overlay.show_indeterminate("Compiling template...")

        worker = CompileWorker(config, self._logo_bytes, self._logo_ext)
        worker.signals.log.connect(self.log_panel.append_log)
        worker.signals.result.connect(self._on_compile_result)
        worker.signals.finished.connect(self._on_compile_finished)
        worker.signals.error.connect(self._on_compile_error)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    def _on_compile_result(self, result):
        pdf_path, pdf_bytes = result
        self._compiled_pdf_bytes = pdf_bytes
        self.preview.set_pdf_preview(pdf_bytes)
        self.btn_save.setEnabled(True)

        # Ask where to save the PDF
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Compiled PDF", os.path.expanduser("~/Documents"), PDF_FILTER)
        if save_path:
            with open(save_path, "wb") as f:
                f.write(pdf_bytes)
            self.log_panel.append_log(f"PDF saved to {save_path}", "INFO")

    def _on_compile_finished(self):
        self.overlay.hide_overlay()
        self._set_form_enabled(True)
        self.log_panel.append_log("Compilation finished.", "INFO")

    def _on_compile_error(self, msg):
        self.overlay.hide_overlay()
        self._set_form_enabled(True)
        self.log_panel.append_log(f"Compilation failed: {msg}", "ERROR")

        # Check if pdflatex not found
        if "not found" in msg.lower():
            from euler_omr.ui.dialogs.tinytex_dialog import TinyTexInstallDialog
            dlg = TinyTexInstallDialog(self)
            dlg.exec()

    def _cancel_compile(self):
        if self._worker:
            self._worker.cancel()

    def _save_template(self):
        config = self._get_config()
        if self.file_path:
            path = self.file_path
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Save Template", os.path.expanduser("~/Documents"), EOMRT_FILTER)
            if not path:
                return

        try:
            EomrtHandler.save(path, config, self._compiled_pdf_bytes,
                              self._logo_bytes, self._logo_filename)
            self.file_path = path
            self._dirty = False
            self.dirty_changed.emit(False)
            self.title_changed.emit(self.tab_title())
            self.log_panel.append_log(f"Template saved to {path}", "INFO")
        except Exception as e:
            self.log_panel.append_log(f"Save failed: {e}", "ERROR")

    def _set_form_enabled(self, enabled):
        for w in [self.txt_institution, self.sp_id_digits, self.sp_versions,
                   self.sp_questions, self.sp_options, self.btn_compile,
                   self.btn_save, self.btn_logo]:
            w.setEnabled(enabled)

    def tab_title(self) -> str:
        name = os.path.basename(self.file_path) if self.file_path else "New Template.eomrt"
        return f"{name}*" if self._dirty else name

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())
