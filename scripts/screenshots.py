"""
Screenshot generator for Euler OMR using PySide6.
Grabs screenshots of core application states for documentation.
"""
import sys
import os
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from euler_omr.ui.style import apply_stylesheet
from euler_omr.ui.fonts import load_fonts
from euler_omr.ui.main_window import MainWindow
from euler_omr.ui.tabs.welcome_tab import WelcomeTab
from euler_omr.ui.tabs.template_tab import TemplateTab
from euler_omr.ui.tabs.project_tab import ProjectTab
from euler_omr.ui.dialogs.answer_key_dialog import AnswerKeyDialog
from euler_omr.ui.dialogs.review_page_dialog import ReviewPageDialog
from euler_omr.models.template_model import TemplateConfig
from euler_omr.models.scan_result import ScanResult, PageState, Issue, IssueType

def main():
    app = QApplication(sys.argv)
    apply_stylesheet(app)
    font = load_fonts()
    app.setFont(font)

    # Prepare save directory
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "screenshots")
    os.makedirs(out_dir, exist_ok=True)

    print(f"Generating screenshots in: {out_dir}")

    # 1. Welcome Screen
    window = MainWindow()
    window.resize(1100, 750)
    window.show()
    QApplication.processEvents()
    time.sleep(0.5)
    
    welcome_path = os.path.join(out_dir, "welcome.png")
    window.grab().save(welcome_path)
    print(f"Saved {welcome_path}")

    # 2. Template Tab Screen
    # Close window and create specific screens to grab perfectly
    window.close()
    
    t_tab = TemplateTab(config=TemplateConfig(
        institution_name="Egypt University of Informatics",
        id_digits=8,
        num_versions=4,
        num_questions=30,
        num_options=4
    ))
    t_tab.resize(1100, 750)
    t_tab.show()
    QApplication.processEvents()
    time.sleep(0.5)
    
    template_path = os.path.join(out_dir, "template.png")
    t_tab.grab().save(template_path)
    print(f"Saved {template_path}")
    t_tab.close()

    # 3. Project Tab Screen
    p_tab = ProjectTab()
    # Add dummy results to show inside the table
    r1 = ScanResult(page_no=1, student_id="20240101", version="A", state=PageState.SUCCESS)
    r2 = ScanResult(page_no=2, student_id="2024010*", version="B", state=PageState.NEEDS_REVIEW, issues=[
        Issue(IssueType.MISSING_DIGIT, "id_digit_7", "Ambiguous bubble")
    ])
    p_tab._scan_results = [r1, r2]
    p_tab.table_model.set_results(p_tab._scan_results)
    p_tab._update_summary()
    p_tab.resize(1100, 750)
    p_tab.show()
    QApplication.processEvents()
    time.sleep(0.5)

    project_path = os.path.join(out_dir, "project.png")
    p_tab.grab().save(project_path)
    print(f"Saved {project_path}")
    p_tab.close()

    # 4. Review Issues Screen
    review_dlg = ReviewPageDialog(
        result=r2,
        active_questions=30,
        active_options=4,
        active_versions=4
    )
    review_dlg.show()
    QApplication.processEvents()
    time.sleep(0.5)

    review_path = os.path.join(out_dir, "review_issues.png")
    review_dlg.grab().save(review_path)
    print(f"Saved {review_path}")
    review_dlg.close()

    # 5. Manage Answer Keys Screen
    ak_dlg = AnswerKeyDialog(
        active_versions=4,
        active_questions=30,
        active_options=4
    )
    ak_dlg.show()
    QApplication.processEvents()
    time.sleep(0.5)

    answer_keys_path = os.path.join(out_dir, "manage_answer_keys.png")
    ak_dlg.grab().save(answer_keys_path)
    print(f"Saved {answer_keys_path}")
    ak_dlg.close()

    print("All screenshots generated successfully!")

if __name__ == "__main__":
    main()
