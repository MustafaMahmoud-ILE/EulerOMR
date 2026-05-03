"""WelcomeTab: left panel (linked labels, recents); right panel (What is New); bottom (GitHub)."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QSplitter, QSizePolicy, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices, QCursor
from PySide6.QtCore import QUrl

from euler_omr.constants import APP_VERSION, EOMRT_EXTENSION, EOMRP_EXTENSION


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("linked_label")

    def mousePressEvent(self, ev):
        from euler_omr.core.sound_manager import SoundManager
        SoundManager.play_click()
        self.clicked.emit()
        super().mousePressEvent(ev)


class WelcomeTab(QWidget):
    create_project_requested = Signal()
    create_template_requested = Signal()
    open_project_requested = Signal()
    open_template_requested = Signal()
    open_file_requested = Signal(str)
    remove_recent_requested = Signal(str)

    def __init__(self, recents: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._build_ui(recents or [])

    def _build_ui(self, recents):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === Left Panel ===
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(24, 24, 16, 8)

        title = QLabel("Euler OMR")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2eb891;")
        left_layout.addWidget(title)
        left_layout.addSpacing(8)

        subtitle = QLabel("OMR Template Designer, Scanner & Grader")
        subtitle.setStyleSheet("font-size: 13px; color: #6c7f7d;")
        left_layout.addWidget(subtitle)
        left_layout.addSpacing(20)

        # Action links
        actions = [
            ("Create a Project", self.create_project_requested),
            ("Create a Template", self.create_template_requested),
            ("Open a Project", self.open_project_requested),
            ("Open a Template", self.open_template_requested),
        ]
        for text, signal in actions:
            lbl = ClickableLabel(f"  > {text}")
            lbl.clicked.connect(signal.emit)
            left_layout.addWidget(lbl)
            left_layout.addSpacing(4)

        left_layout.addSpacing(12)
        recent_header = QLabel("Recent Files")
        recent_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #abcbc4;")
        left_layout.addWidget(recent_header)

        self.recents_list = QListWidget()
        self.recents_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.recents_list.customContextMenuRequested.connect(self._show_context_menu)
        self.recents_list.doubleClicked.connect(self._on_recent_double_click)
        left_layout.addWidget(self.recents_list)
        self._populate_recents(recents)

        # === Right Panel ===
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 24, 24, 8)

        what_new = QLabel(f"What is New in Euler OMR v{APP_VERSION}")
        what_new.setObjectName("heading_large")
        right_layout.addWidget(what_new)
        right_layout.addSpacing(12)

        notes = QLabel(
            "Initial release.\n\n"
            "- Template designer with LaTeX compilation\n"
            "- OMR scan reader with auto-contrast\n"
            "- Statistical analysis report generator\n"
            "- Full project save/load\n"
            "- XLSX grade export\n"
            "- Per-question difficulty analysis\n"
            "- Version fairness comparison"
        )
        notes.setWordWrap(True)
        notes.setStyleSheet("color: #abcbc4; font-size: 12px; line-height: 1.5;")
        right_layout.addWidget(notes)
        right_layout.addStretch()

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

        # === Bottom Panel ===
        bottom = QHBoxLayout()
        bottom.setContentsMargins(24, 4, 24, 8)
        gh = ClickableLabel("  Open Project on GitHub")
        gh.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://github.com/MustafaMahmoud-ILE/EulerOMR")))
        bottom.addWidget(gh)
        bottom.addStretch()
        main_layout.addLayout(bottom)

    def _populate_recents(self, recents):
        self.recents_list.clear()
        for path in recents:
            import os
            name = os.path.basename(path)
            ext = os.path.splitext(path)[1].lower()
            prefix = "[P] " if ext == EOMRP_EXTENSION else "[T] "
            item = QListWidgetItem(prefix + name)
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.recents_list.addItem(item)

    def update_recents(self, recents):
        self._populate_recents(recents)

    def _on_recent_double_click(self, index):
        item = self.recents_list.currentItem()
        if item:
            path = item.data(Qt.ItemDataRole.UserRole)
            self.open_file_requested.emit(path)

    def _show_context_menu(self, pos):
        item = self.recents_list.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #052221; color: #f0f6f6; border: 1px solid #385550; }")
        open_action = menu.addAction("Open")
        remove_action = menu.addAction("Remove from Recents")
        action = menu.exec(QCursor.pos())
        if action == open_action:
            self.open_file_requested.emit(path)
        elif action == remove_action:
            self.remove_recent_requested.emit(path)
