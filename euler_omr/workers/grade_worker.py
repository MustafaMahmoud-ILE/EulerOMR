"""Applies answer keys and runs analysis; emits progress and final report path."""
from euler_omr.workers.base_worker import BaseWorker
from euler_omr.core.grader import Grader
from euler_omr.core.analysis import AnalysisEngine
from euler_omr.core.report_builder import ReportBuilder
from euler_omr.core.xlsx_exporter import XlsxExporter
from euler_omr.models.scan_result import ScanResult
from euler_omr.models.answer_key import AnswerKey
import os


class GradeWorker(BaseWorker):
    def __init__(self, scan_results: list[ScanResult], answer_key: AnswerKey,
                 active_questions: int, xlsx_path: str,
                 run_analysis: bool = False, report_path: str = ""):
        super().__init__()
        self.scan_results = scan_results
        self.answer_key = answer_key
        self.active_questions = active_questions
        self.xlsx_path = xlsx_path
        self.run_analysis = run_analysis
        self.report_path = report_path

    def run(self):
        try:
            self._log("Grading...", "INFO")
            self.signals.progress.emit(1, 4)
            grades = Grader.grade(self.scan_results, self.answer_key,
                                  self.active_questions, self._log)
            self.signals.progress.emit(2, 4)
            report = None
            if self.run_analysis:
                self._log("Running analysis...", "INFO")
                report = AnalysisEngine.analyze(grades, self.answer_key, self.active_questions)
                self.signals.progress.emit(3, 4)
                if self.report_path:
                    ReportBuilder.build(report, self.report_path, self._log)
            self._log("Exporting XLSX...", "INFO")
            XlsxExporter.export(grades, self.xlsx_path, report)
            self.signals.progress.emit(4, 4)
            self.signals.result.emit((self.xlsx_path, self.report_path))
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(f"Grading error: {e}")
