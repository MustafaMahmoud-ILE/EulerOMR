"""MainWindow: central QTabWidget (TDI); menu bar; status bar; recent-files; drag-and-drop."""
import os
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu, QStatusBar,
    QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QIcon, QDragEnterEvent, QDropEvent

from euler_omr.constants import (
    APP_NAME, APP_VERSION, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    EOMRT_EXTENSION, EOMRP_EXTENSION, EOMRT_FILTER, EOMRP_FILTER,
)
from euler_omr.config import AppConfig
from euler_omr.ui.tabs.welcome_tab import WelcomeTab
from euler_omr.ui.tabs.template_tab import TemplateTab
from euler_omr.ui.tabs.project_tab import ProjectTab
from euler_omr.ui.dialogs.unsaved_changes_dialog import UnsavedChangesDialog
from euler_omr.file_io.eomrt_handler import EomrtHandler
from euler_omr.file_io.eomrp_handler import EomrpHandler


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        self._config = AppConfig()
        self.setAcceptDrops(True)

        # --- Central Tab Widget ---
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.setCentralWidget(self.tabs)

        # --- Menu Bar ---
        self._create_menus()

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # --- Welcome Tab ---
        self._add_welcome_tab()

        # --- Restore Geometry ---
        geom = self._config.load_geometry()
        if geom:
            self.restoreGeometry(geom)

    def _create_menus(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        new_project = QAction("New Project", self)
        new_project.setShortcut("Ctrl+N")
        new_project.triggered.connect(self._new_project)
        file_menu.addAction(new_project)

        new_template = QAction("New Template", self)
        new_template.setShortcut("Ctrl+Shift+N")
        new_template.triggered.connect(self._new_template)
        file_menu.addAction(new_template)

        file_menu.addSeparator()

        open_project = QAction("Open Project...", self)
        open_project.setShortcut("Ctrl+O")
        open_project.triggered.connect(self._open_project_dialog)
        file_menu.addAction(open_project)

        open_template = QAction("Open Template...", self)
        open_template.setShortcut("Ctrl+Shift+O")
        open_template.triggered.connect(self._open_template_dialog)
        file_menu.addAction(open_template)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")
        about = QAction("About", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _add_welcome_tab(self):
        recents = self._config.get_recents()
        welcome = WelcomeTab(recents)
        welcome.create_project_requested.connect(self._new_project)
        welcome.create_template_requested.connect(self._new_template)
        welcome.open_project_requested.connect(self._open_project_dialog)
        welcome.open_template_requested.connect(self._open_template_dialog)
        welcome.open_file_requested.connect(self._open_file)
        welcome.remove_recent_requested.connect(self._remove_recent)
        idx = self.tabs.addTab(welcome, "Welcome")
        # Welcome tab not closable
        self.tabs.tabBar().setTabButton(idx, self.tabs.tabBar().ButtonPosition.RightSide, None)

    def _new_project(self):
        tab = ProjectTab()
        tab.title_changed.connect(lambda title: self._update_tab_title(tab, title))
        idx = self.tabs.addTab(tab, tab.tab_title())
        self.tabs.setCurrentIndex(idx)

    def _new_template(self):
        tab = TemplateTab()
        tab.title_changed.connect(lambda title: self._update_tab_title(tab, title))
        idx = self.tabs.addTab(tab, tab.tab_title())
        self.tabs.setCurrentIndex(idx)

    def _open_project_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", EOMRP_FILTER)
        if path:
            self._open_file(path)

    def _open_template_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Template", "", EOMRT_FILTER)
        if path:
            self._open_file(path)

    def _open_file(self, path: str):
        if not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found", f"File not found: {path}")
            self._config.remove_recent(path)
            self._refresh_welcome()
            return

        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == EOMRT_EXTENSION:
                data = EomrtHandler.load(path)
                tab = TemplateTab(config=data["config"], file_path=path)
                if data["compiled_pdf_bytes"]:
                    tab._compiled_pdf_bytes = data["compiled_pdf_bytes"]
                    tab.preview.set_pdf_preview(data["compiled_pdf_bytes"])
                    tab.btn_save.setEnabled(True)
                if data["logo_bytes"]:
                    tab._logo_bytes = data["logo_bytes"]
                    tab._logo_filename = data["logo_filename"]
                tab.title_changed.connect(lambda title: self._update_tab_title(tab, title))
                idx = self.tabs.addTab(tab, tab.tab_title())
                self.tabs.setCurrentIndex(idx)

            elif ext == EOMRP_EXTENSION:
                data = EomrpHandler.load(path)
                tab = ProjectTab(file_path=path)
                tab._project_name = data["project_name"]
                tab._template_config = data["template_config"]
                tab._template_pdf_bytes = data["template_pdf_bytes"]
                tab._template_logo_bytes = data["template_logo_bytes"]
                tab._template_logo_filename = data["template_logo_filename"]
                tab._scans_pdf_bytes = data["scans_pdf_bytes"]
                tab._scan_results = data["scan_results"]
                tab._answer_keys = data["answer_keys"]
                tab.chk_analysis.setChecked(data["chk_run_analysis"])

                # Update UI
                if tab._template_config:
                    tc = tab._template_config
                    cfg = data["config"]
                    tab.sp_active_q.setMaximum(tc.num_questions)
                    tab.sp_active_q.setValue(cfg.active_questions)
                    tab.sp_active_q.setEnabled(True)
                    tab.sp_active_opt.setMaximum(tc.num_options)
                    tab.sp_active_opt.setValue(cfg.active_options)
                    tab.sp_active_opt.setEnabled(True)
                    tab.sp_active_ver.setMaximum(tc.num_versions)
                    tab.sp_active_ver.setValue(cfg.active_versions)
                    tab.sp_active_ver.setEnabled(True)

                if tab._scan_results:
                    tab.table_model.set_results(tab._scan_results)
                    tab._scan_reading_done = True
                    tab.btn_manage_keys.setEnabled(True)
                    tab._update_summary()

                if data["answer_keys"].keys:
                    tab._answer_keys_saved = True
                    tab._update_grading_button()

                tab._scans_pdf_path = None  # Scans are embedded
                tab.btn_start_reading.setEnabled(tab._template_config is not None)
                tab.title_changed.connect(lambda title: self._update_tab_title(tab, title))
                idx = self.tabs.addTab(tab, tab.tab_title())
                self.tabs.setCurrentIndex(idx)
            else:
                QMessageBox.warning(self, "Unknown File", f"Unknown file type: {ext}")
                return

            self._config.add_recent(path)
            self._refresh_welcome()
            self.status_bar.showMessage(f"Opened: {path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file:\n{e}")

    def _remove_recent(self, path):
        self._config.remove_recent(path)
        self._refresh_welcome()

    def _refresh_welcome(self):
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, WelcomeTab):
                widget.update_recents(self._config.get_recents())
                break

    def _update_tab_title(self, tab, title):
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            self.tabs.setTabText(idx, title)

    def _on_tab_close_requested(self, index):
        widget = self.tabs.widget(index)
        if isinstance(widget, WelcomeTab):
            return

        if isinstance(widget, (TemplateTab, ProjectTab)) and widget.is_dirty:
            dlg = UnsavedChangesDialog(self.tabs.tabText(index).rstrip("*"), self)
            if dlg.exec():
                result = dlg.get_result()
                if result == UnsavedChangesDialog.SAVE:
                    if isinstance(widget, TemplateTab):
                        widget._save_template()
                    else:
                        widget._save_project()
                elif result == UnsavedChangesDialog.CANCEL:
                    return
            else:
                return

        self.tabs.removeTab(index)

    def _show_about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "A production-grade desktop application for designing OMR templates,\n"
            "scanning and marking student answer sheets, and running\n"
            "statistical analysis on grading results.\n\n"
            "github.com/MustafaMahmoud-ILE/EulerOMR"
        )

    # --- Drag and Drop ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                ext = os.path.splitext(path)[1].lower()
                if ext in (EOMRT_EXTENSION, EOMRP_EXTENSION):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in (EOMRT_EXTENSION, EOMRP_EXTENSION):
                self._open_file(path)

    def closeEvent(self, event):
        # Check all tabs for unsaved changes
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, (TemplateTab, ProjectTab)) and widget.is_dirty:
                self.tabs.setCurrentIndex(i)
                dlg = UnsavedChangesDialog(self.tabs.tabText(i).rstrip("*"), self)
                if dlg.exec():
                    result = dlg.get_result()
                    if result == UnsavedChangesDialog.SAVE:
                        if isinstance(widget, TemplateTab):
                            widget._save_template()
                        else:
                            widget._save_project()
                    elif result == UnsavedChangesDialog.CANCEL:
                        event.ignore()
                        return
                else:
                    event.ignore()
                    return

        self._config.save_geometry(self.saveGeometry())
        event.accept()
