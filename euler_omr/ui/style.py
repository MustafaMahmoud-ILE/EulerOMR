"""Full QSS stylesheet string built from the brand color palette."""


def get_stylesheet() -> str:
    return """
/* === Global === */
QWidget {
    background-color: #041010;
    color: #f0f6f6;
    font-family: "Fixedsys Excelsior 3.01", "Fixedsys Excelsior", "Courier New", monospace;
    font-size: 13px;
}

/* === Main Window === */
QMainWindow {
    background-color: #041010;
}

/* === Menu Bar === */
QMenuBar {
    background-color: #052221;
    color: #f0f6f6;
    border-bottom: 1px solid #385550;
    padding: 2px;
}
QMenuBar::item {
    padding: 4px 12px;
    background: transparent;
}
QMenuBar::item:selected {
    background-color: #2eb891;
    color: #041010;
}
QMenu {
    background-color: #052221;
    color: #f0f6f6;
    border: 1px solid #385550;
}
QMenu::item:selected {
    background-color: #2eb891;
    color: #041010;
}
QMenu::separator {
    height: 1px;
    background: #385550;
    margin: 4px 8px;
}

/* === Tab Widget === */
QTabWidget::pane {
    border: 1px solid #385550;
    background-color: #041010;
}
QTabBar::tab {
    background-color: #052221;
    color: #f0f6f6;
    padding: 6px 16px;
    border: 1px solid #385550;
    border-bottom: none;
    margin-right: 2px;
    min-width: 100px;
}
QTabBar::tab:selected {
    background-color: #041010;
    border-bottom: 2px solid #2eb891;
    color: #2eb891;
}
QTabBar::tab:hover:!selected {
    background-color: #0f4339;
}
QTabBar::close-button {
    subcontrol-position: right;
    padding: 2px;
}
QTabBar::close-button:hover {
    background-color: #e63946;
}

/* === Buttons === */
QPushButton {
    background-color: #05604b;
    color: #f0f6f6;
    border: 1px solid #385550;
    padding: 6px 16px;
    border-radius: 3px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #2eb891;
    color: #041010;
    border-color: #2eb891;
}
QPushButton:pressed {
    background-color: #09a964;
}
QPushButton:disabled {
    background-color: #abcbc4;
    color: #8caaa4;
    border-color: #385550;
}

/* === Line Edit / SpinBox / ComboBox === */
QLineEdit, QSpinBox, QComboBox {
    background-color: #052221;
    color: #f0f6f6;
    border: 1px solid #385550;
    padding: 4px 8px;
    border-radius: 3px;
    min-height: 24px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #2eb891;
}
QComboBox::drop-down {
    border: none;
    background-color: #0f4339;
    width: 24px;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}
QComboBox QAbstractItemView {
    background-color: #052221;
    color: #f0f6f6;
    border: 1px solid #385550;
    selection-background-color: #2eb891;
    selection-color: #041010;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #0f4339;
    border: none;
    width: 16px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #2eb891;
}

/* === Check Box === */
QCheckBox {
    spacing: 8px;
    color: #f0f6f6;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #385550;
    border-radius: 3px;
    background-color: #052221;
}
QCheckBox::indicator:checked {
    background-color: #2eb891;
    border-color: #2eb891;
}
QCheckBox::indicator:hover {
    border-color: #2eb891;
}

/* === Scroll Bars === */
QScrollBar:vertical {
    background: #041010;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2eb891;
    min-height: 30px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #041010;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #2eb891;
    min-width: 30px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* === Progress Bar === */
QProgressBar {
    background-color: #052221;
    border: 1px solid #385550;
    border-radius: 3px;
    text-align: center;
    color: #f0f6f6;
    min-height: 20px;
}
QProgressBar::chunk {
    background-color: #2eb891;
    border-radius: 2px;
}

/* === Table View === */
QTableView {
    background-color: #041010;
    color: #f0f6f6;
    gridline-color: #385550;
    border: 1px solid #385550;
    selection-background-color: #0f4339;
    selection-color: #f0f6f6;
}
QHeaderView::section {
    background-color: #052221;
    color: #2eb891;
    padding: 4px 8px;
    border: 1px solid #385550;
    font-weight: bold;
}

/* === List Widget === */
QListWidget {
    background-color: #052221;
    color: #f0f6f6;
    border: 1px solid #385550;
    border-radius: 3px;
}
QListWidget::item {
    padding: 4px 8px;
}
QListWidget::item:selected {
    background-color: #2eb891;
    color: #041010;
}
QListWidget::item:hover:!selected {
    background-color: #0f4339;
}

/* === Splitter === */
QSplitter::handle {
    background-color: #385550;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}

/* === Labels === */
QLabel {
    color: #f0f6f6;
    background: transparent;
}

/* === Group Box === */
QGroupBox {
    border: 1px solid #385550;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
    color: #f0f6f6;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #2eb891;
}

/* === Status Bar === */
QStatusBar {
    background-color: #052221;
    color: #f0f6f6;
    border-top: 1px solid #385550;
}

/* === Dialogs === */
QDialog {
    background-color: #041010;
}

/* === Tool Tips === */
QToolTip {
    background-color: #052221;
    color: #f0f6f6;
    border: 1px solid #2eb891;
    padding: 4px;
}

/* === Named widgets === */
QLabel#linked_label {
    color: #2eb891;
    font-size: 14px;
}
QLabel#linked_label:hover {
    color: #00de81;
}
QLabel#heading_large {
    font-size: 18px;
    font-weight: bold;
    color: #f0f6f6;
}
QLabel#error_label {
    color: #e63946;
}
QLabel#success_label {
    color: #09a964;
}
QLabel#warning_label {
    color: #ffb703;
}
QLabel#info_label {
    color: #219ebc;
}
"""


def apply_stylesheet(app):
    """Apply the global QSS stylesheet to a QApplication."""
    app.setStyleSheet(get_stylesheet())
