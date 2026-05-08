"""ProjectTab: left controls; right scan results table; bottom log; dirty-state tracking."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton,
    QSplitter, QFileDialog, QGroupBox, QCheckBox, QTableView, QHeaderView,
    QAbstractItemView, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex, QThreadPool
from PySide6.QtGui import QColor, QBrush

from euler_omr.constants import (
    EOMRT_FILTER, EOMRP_FILTER, PDF_FILTER,
    ACTIVE_QUESTIONS_MIN, ACTIVE_OPTIONS_MIN, ACTIVE_VERSIONS_MIN,
    VERSION_LETTERS,
)
from euler_omr.models.template_model import TemplateConfig
from euler_omr.models.project_model import ProjectConfig
from euler_omr.models.scan_result import ScanResult, PageState
from euler_omr.models.answer_key import AnswerKey
from euler_omr.file_io.eomrt_handler import EomrtHandler
from euler_omr.file_io.eomrp_handler import EomrpHandler
from euler_omr.core.scan_reader import ScanReader
from euler_omr.workers.grade_worker import GradeWorker
from euler_omr.ui.widgets.log_panel import LogPanel
from euler_omr.ui.widgets.progress_overlay import ProgressOverlay


class ScanResultTableModel(QAbstractTableModel):
    HEADERS = ["Page", "ID", "Version", "State"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: list[ScanResult] = []

    def set_results(self, results):
        self.beginResetModel()
        self._results = results
        self.endResetModel()

    def add_result(self, result):
        row = len(self._results)
        self.beginInsertRows(QModelIndex(), row, row)
        self._results.append(result)
        self.endInsertRows()

    def rowCount(self, parent=QModelIndex()):
        return len(self._results)

    def columnCount(self, parent=QModelIndex()):
        return 4

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        r = self._results[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return r.page_no
            if col == 1: return r.student_id
            if col == 2: return r.version
            if col == 3: return r.state.value.replace("_", " ").title()
        elif role == Qt.ItemDataRole.BackgroundRole:
            if r.state == PageState.NEEDS_REVIEW:
                return QBrush(QColor(255, 183, 3, 38))
            elif r.state == PageState.RESOLVED:
                return QBrush(QColor(9, 169, 100, 38))
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def get_result(self, row) -> ScanResult | None:
        return self._results[row] if 0 <= row < len(self._results) else None

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        self.beginResetModel()
        reverse = (order == Qt.SortOrder.DescendingOrder)
        if column == 0:
            self._results.sort(key=lambda r: r.page_no, reverse=reverse)
        elif column == 1:
            self._results.sort(key=lambda r: r.student_id or "", reverse=reverse)
        elif column == 2:
            self._results.sort(key=lambda r: r.version or "", reverse=reverse)
        elif column == 3:
            self._results.sort(key=lambda r: r.state.value if r.state else "", reverse=reverse)
        self.endResetModel()


class ProjectTab(QWidget):
    dirty_changed = Signal(bool)
    title_changed = Signal(str)

    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self._dirty = False
        self._template_config: TemplateConfig | None = None
        self._template_pdf_bytes: bytes | None = None
        self._template_logo_bytes: bytes | None = None
        self._template_logo_filename: str | None = None
        self._scans_pdf_path: str | None = None
        self._scans_pdf_bytes: bytes | None = None
        self._scan_results: list[ScanResult] = []
        self._answer_keys = AnswerKey()
        self._project_name = "Untitled"
        self._scan_reading_done = False
        self._answer_keys_saved = False
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        vsplit = QSplitter(Qt.Orientation.Vertical)
        hsplit = QSplitter(Qt.Orientation.Horizontal)

        # === Left Controls (Scrollable Sidebar) ===
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setMaximumWidth(320)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_container = QWidget()
        ll = QVBoxLayout(left_container)
        ll.setContentsMargins(12, 12, 8, 8)

        grp = QGroupBox("Project Controls")
        gl = QVBoxLayout(grp)

        self.btn_import_template = QPushButton("Import Template (*.eomrt)")
        self.btn_import_template.clicked.connect(self._import_template)
        gl.addWidget(self.btn_import_template)

        self.btn_import_scans = QPushButton("Import Scans (*.pdf)")
        self.btn_import_scans.clicked.connect(self._import_scans)
        gl.addWidget(self.btn_import_scans)

        gl.addSpacing(8)

        self.sp_active_q = QSpinBox()
        self.sp_active_q.setRange(ACTIVE_QUESTIONS_MIN, 99)
        self.sp_active_q.setValue(60)
        self.sp_active_q.setEnabled(False)
        self.sp_active_q.valueChanged.connect(self._mark_dirty)
        aq_row = QHBoxLayout()
        aq_row.addWidget(QLabel("Active Questions:"))
        aq_row.addWidget(self.sp_active_q)
        gl.addLayout(aq_row)

        self.sp_active_opt = QSpinBox()
        self.sp_active_opt.setRange(ACTIVE_OPTIONS_MIN, 8)
        self.sp_active_opt.setValue(4)
        self.sp_active_opt.setEnabled(False)
        self.sp_active_opt.valueChanged.connect(self._mark_dirty)
        ao_row = QHBoxLayout()
        ao_row.addWidget(QLabel("Active Options:"))
        ao_row.addWidget(self.sp_active_opt)
        gl.addLayout(ao_row)

        self.sp_active_ver = QSpinBox()
        self.sp_active_ver.setRange(ACTIVE_VERSIONS_MIN, 26)
        self.sp_active_ver.setValue(4)
        self.sp_active_ver.setEnabled(False)
        self.sp_active_ver.valueChanged.connect(self._mark_dirty)
        av_row = QHBoxLayout()
        av_row.addWidget(QLabel("Active Versions:"))
        av_row.addWidget(self.sp_active_ver)
        gl.addLayout(av_row)

        gl.addSpacing(8)

        self.btn_start_reading = QPushButton("Start Reading Scans")
        self.btn_start_reading.setEnabled(False)
        self.btn_start_reading.clicked.connect(self._start_reading)
        gl.addWidget(self.btn_start_reading)

        self.btn_manage_keys = QPushButton("Manage Answer Keys")
        self.btn_manage_keys.setEnabled(False)
        self.btn_manage_keys.clicked.connect(self._manage_keys)
        gl.addWidget(self.btn_manage_keys)

        self.btn_wizard_fixer = QPushButton("Wizard Fixer")
        self.btn_wizard_fixer.setEnabled(False)
        self.btn_wizard_fixer.clicked.connect(self._open_wizard_fixer)
        gl.addWidget(self.btn_wizard_fixer)

        self.chk_analysis = QCheckBox("Run Analysis")
        gl.addWidget(self.chk_analysis)

        self.btn_save_project = QPushButton("Save Project (*.eomrp)")
        self.btn_save_project.clicked.connect(self._save_project)
        gl.addWidget(self.btn_save_project)

        self.btn_run_grading = QPushButton("Run Grading")
        self.btn_run_grading.setEnabled(False)
        self.btn_run_grading.clicked.connect(self._run_grading)
        gl.addWidget(self.btn_run_grading)

        ll.addWidget(grp)
        ll.addStretch()
        scroll_area.setWidget(left_container)

        # === Right Panel: Table + Summary ===
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 12, 12, 8)

        self.table_model = ScanResultTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.doubleClicked.connect(self._on_table_double_click)
        rl.addWidget(self.table_view)

        summary = QHBoxLayout()
        self.lbl_pages = QLabel("Total Pages: 0")
        self.lbl_issues = QLabel("Issues: 0")
        self.lbl_issues.setObjectName("success_label")
        summary.addWidget(self.lbl_pages)
        summary.addStretch()
        summary.addWidget(self.lbl_issues)
        rl.addLayout(summary)

        hsplit.addWidget(scroll_area)
        hsplit.addWidget(right)
        hsplit.setStretchFactor(0, 0)
        hsplit.setStretchFactor(1, 1)

        self.log_panel = LogPanel()
        vsplit.addWidget(hsplit)
        vsplit.addWidget(self.log_panel)
        vsplit.setStretchFactor(0, 3)
        vsplit.setStretchFactor(1, 1)

        main.addWidget(vsplit)

        self.overlay = ProgressOverlay(self)

    def _mark_dirty(self):
        self._dirty = True
        self.dirty_changed.emit(True)
        self.title_changed.emit(self.tab_title())

    def _import_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Template", os.path.expanduser("~/Documents"), EOMRT_FILTER)
        if not path:
            return
        try:
            data = EomrtHandler.load(path)
            self._template_config = data["config"]
            self._template_pdf_bytes = data["compiled_pdf_bytes"]
            self._template_logo_bytes = data["logo_bytes"]
            self._template_logo_filename = data["logo_filename"]
            tc = self._template_config
            self.sp_active_q.setMaximum(tc.num_questions)
            self.sp_active_q.setValue(tc.num_questions)
            self.sp_active_q.setEnabled(True)
            self.sp_active_opt.setMaximum(tc.num_options)
            self.sp_active_opt.setValue(tc.num_options)
            self.sp_active_opt.setEnabled(True)
            self.sp_active_ver.setMaximum(tc.num_versions)
            self.sp_active_ver.setValue(tc.num_versions)
            self.sp_active_ver.setEnabled(True)
            self._update_start_button()
            self.log_panel.append_log(f"Template imported: {path}", "INFO")
            self._mark_dirty()
        except Exception as e:
            self.log_panel.append_log(f"Failed to import template: {e}", "ERROR")

    def _import_scans(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Scans PDF", os.path.expanduser("~/Documents"), PDF_FILTER)
        if not path:
            return
        self._scans_pdf_path = path
        with open(path, "rb") as f:
            self._scans_pdf_bytes = f.read()
        self._update_start_button()
        self.log_panel.append_log(f"Scans imported: {path}", "INFO")
        self._mark_dirty()

    def _update_start_button(self):
        self.btn_start_reading.setEnabled(
            self._template_config is not None and self._scans_pdf_path is not None
        )

    def _start_reading(self):
        if self._scan_results:
            reply = QMessageBox.warning(
                self, "Re-run Scan",
                "This will clear all resolved issues. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        tc = self._template_config
        reader = ScanReader(
            id_digits=tc.id_digits,
            num_versions=tc.num_versions,
            active_questions=self.sp_active_q.value(),
            active_options=self.sp_active_opt.value(),
            active_versions=self.sp_active_ver.value(),
            num_questions=tc.num_questions,
        )

        self._scan_results = []
        self.table_model.set_results([])
        self.overlay.show_progress(0, 1, "Reading scans...")

        # Run in thread
        from euler_omr.workers.base_worker import BaseWorker

        class _ReadWorker(BaseWorker):
            def __init__(self, pdf_path, rdr):
                super().__init__()
                self.pdf_path = pdf_path
                self.reader = rdr

            def run(self_w):
                try:
                    results = self_w.reader.read_pdf(
                        self_w.pdf_path,
                        progress_callback=lambda c, t: self_w.signals.progress.emit(c, t),
                        log_callback=self_w._log,
                        cancel_check=self_w.is_cancelled,
                    )
                    self_w.signals.result.emit(results)
                    self_w.signals.finished.emit()
                except Exception as e:
                    self_w.signals.error.emit(str(e))

        w = _ReadWorker(self._scans_pdf_path, reader)
        w.signals.log.connect(self.log_panel.append_log)
        w.signals.progress.connect(lambda c, t: self.overlay.show_progress(c, t, f"Reading page {c}/{t}..."))
        w.signals.result.connect(self._on_read_result)
        w.signals.finished.connect(self._on_read_finished)
        w.signals.error.connect(self._on_read_error)
        self.overlay.cancelled.connect(w.cancel)
        QThreadPool.globalInstance().start(w)

    def _on_read_result(self, results):
        if isinstance(results, list):
            self._scan_results = results
            self.table_model.set_results(results)
            self._update_summary()

    def _on_read_finished(self):
        self.overlay.hide_overlay()
        self._scan_reading_done = True
        self.btn_manage_keys.setEnabled(True)
        self._mark_dirty()
        from euler_omr.core.sound_manager import SoundManager
        SoundManager.play_complete()
        self.log_panel.append_log("Scan reading complete.", "INFO")

    def _on_read_error(self, msg):
        self.overlay.hide_overlay()
        self.log_panel.append_log(f"Scan error: {msg}", "ERROR")

    def _update_summary(self):
        n = len(self._scan_results)
        issues = sum(1 for r in self._scan_results if r.state == PageState.NEEDS_REVIEW)
        self.lbl_pages.setText(f"Total Pages: {n}")
        self.lbl_issues.setText(f"Issues: {issues}")
        if issues > 0:
            self.lbl_issues.setObjectName("error_label")
            self.btn_wizard_fixer.setEnabled(True)
        else:
            self.lbl_issues.setObjectName("success_label")
            self.btn_wizard_fixer.setEnabled(False)
        
        self.lbl_issues.style().unpolish(self.lbl_issues)
        self.lbl_issues.style().polish(self.lbl_issues)
        self._update_grading_button()

    def _open_wizard_fixer(self):
        problematic = [r for r in self._scan_results if r.state == PageState.NEEDS_REVIEW]
        if not problematic:
            return
        from euler_omr.ui.dialogs.wizard_fixer_dialog import WizardFixerDialog
        dlg = WizardFixerDialog(
            problematic_results=problematic,
            active_questions=self.sp_active_q.value(),
            active_options=self.sp_active_opt.value(),
            active_versions=self.sp_active_ver.value(),
            num_questions=self._template_config.num_questions if self._template_config else self.sp_active_q.value(),
            scans_pdf_path=self._scans_pdf_path,
            scans_pdf_bytes=self._scans_pdf_bytes,
            parent=self,
        )
        if dlg.exec():
            results = dlg.get_results()
            for updated in results:
                for idx, orig in enumerate(self._scan_results):
                    if orig.page_no == updated.page_no:
                        self._scan_results[idx] = updated
                        break
            self.table_model.set_results(self._scan_results)
            self._update_summary()
            self._mark_dirty()


    def _manage_keys(self):
        from euler_omr.ui.dialogs.answer_key_dialog import AnswerKeyDialog
        dlg = AnswerKeyDialog(
            active_versions=self.sp_active_ver.value(),
            active_questions=self.sp_active_q.value(),
            active_options=self.sp_active_opt.value(),
            answer_key=self._answer_keys,
            parent=self,
        )
        if dlg.exec():
            self._answer_keys = dlg.get_answer_key()
            self._answer_keys_saved = True
            self._mark_dirty()
            self._update_grading_button()
            self.log_panel.append_log("Answer keys saved.", "INFO")

    def _on_table_double_click(self, index):
        row = index.row()
        result = self.table_model.get_result(row)
        if not result:
            return
        from euler_omr.ui.dialogs.review_page_dialog import ReviewPageDialog
        dlg = ReviewPageDialog(
            result=result,
            active_questions=self.sp_active_q.value(),
            active_options=self.sp_active_opt.value(),
            active_versions=self.sp_active_ver.value(),
            scans_pdf_path=self._scans_pdf_path,
            scans_pdf_bytes=self._scans_pdf_bytes,
            num_questions=self._template_config.num_questions if self._template_config else self.sp_active_q.value(),
            parent=self,
        )
        if dlg.exec():
            updated = dlg.get_result()
            self._scan_results[row] = updated
            self.table_model.set_results(self._scan_results)
            self._update_summary()
            self._mark_dirty()

    def _update_grading_button(self):
        issues = sum(1 for r in self._scan_results if r.state == PageState.NEEDS_REVIEW)
        self.btn_run_grading.setEnabled(
            self._answer_keys_saved and self.file_path is not None and issues == 0
        )

    def _save_project(self):
        if self.file_path:
            path = self.file_path
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Save Project", os.path.expanduser("~/Documents"), EOMRP_FILTER)
            if not path:
                return
        try:
            config = ProjectConfig(
                active_questions=self.sp_active_q.value(),
                active_options=self.sp_active_opt.value(),
                active_versions=self.sp_active_ver.value(),
            )
            EomrpHandler.save(
                path, self._project_name, config,
                self._template_config or TemplateConfig(),
                self._template_pdf_bytes, self._template_logo_bytes,
                self._template_logo_filename,
                self._scans_pdf_bytes, self._scan_results,
                self._answer_keys, self.chk_analysis.isChecked(),
            )
            self.file_path = path
            self._dirty = False
            self.dirty_changed.emit(False)
            self.title_changed.emit(self.tab_title())
            self._update_grading_button()
            self.log_panel.append_log(f"Project saved to {path}", "INFO")
        except Exception as e:
            self.log_panel.append_log(f"Save failed: {e}", "ERROR")

    def _run_grading(self):
        xlsx_path, _ = QFileDialog.getSaveFileName(self, "Save Grades", os.path.expanduser("~/Documents"), "Excel Files (*.xlsx)")
        if not xlsx_path:
            return
        report_path = ""
        if self.chk_analysis.isChecked():
            report_path, _ = QFileDialog.getSaveFileName(self, "Save Analysis Report", os.path.expanduser("~/Documents"), "PDF Files (*.pdf)")

        # Pre-flight: if a report is requested, ensure LaTeX is available
        if report_path:
            from euler_omr.core.latex_check import ensure_latex_available
            if not ensure_latex_available(parent=self):
                self.log_panel.append_log(
                    "Grading cancelled: LaTeX engine not available for report generation. "
                    "Please install TinyTeX via Help > Install TinyTeX.", "ERROR")
                return

        self.overlay.show_progress(0, 4, "Grading...")
        worker = GradeWorker(
            self._scan_results, self._answer_keys,
            self.sp_active_q.value(), xlsx_path,
            self.chk_analysis.isChecked(), report_path,
        )
        worker.signals.log.connect(self.log_panel.append_log)
        worker.signals.progress.connect(lambda c, t: self.overlay.show_progress(c, t, "Processing..."))
        worker.signals.finished.connect(self._on_grade_finished)
        worker.signals.error.connect(self._on_grade_error)
        worker.signals.result.connect(self._on_grade_result)
        QThreadPool.globalInstance().start(worker)


    def _on_grade_result(self, result):
        xlsx_path, report_path = result
        self.log_panel.append_log(f"Results exported to {xlsx_path}", "INFO")
        if report_path:
            self.log_panel.append_log(f"Analysis report saved to {report_path}", "INFO")
        # Open folder
        import subprocess
        subprocess.Popen(["explorer", "/select,", xlsx_path.replace("/", "\\")])

    def _on_grade_finished(self):
        self.overlay.hide_overlay()

    def _on_grade_error(self, msg):
        self.overlay.hide_overlay()
        self.log_panel.append_log(f"Grading error: {msg}", "ERROR")

    def tab_title(self) -> str:
        name = os.path.basename(self.file_path) if self.file_path else "New Project.eomrp"
        return f"{name}*" if self._dirty else name

    @property
    def is_dirty(self):
        return self._dirty

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())
