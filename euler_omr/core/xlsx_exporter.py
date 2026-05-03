"""openpyxl-based grading result exporter."""
from __future__ import annotations
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from euler_omr.models.scan_result import GradeRecord
from euler_omr.core.analysis import AnalysisReport
import structlog

logger = structlog.get_logger(__name__)


class XlsxExporter:
    HEADER_FILL = PatternFill(start_color="2EB891", end_color="2EB891", fill_type="solid")
    HEADER_FONT = Font(bold=True, color="F0F6F6", size=11)
    ALT_FILL = PatternFill(start_color="E8F4F0", end_color="E8F4F0", fill_type="solid")

    @staticmethod
    def export(grades: list[GradeRecord], output_path: str, report: AnalysisReport | None = None):
        wb = Workbook()
        ws = wb.active
        ws.title = "Grades"
        headers = ["Student ID", "Version", "Score", "Max Score", "Percentage"]
        for col, h in enumerate(headers, 1):
            c = ws.cell(row=1, column=col, value=h)
            c.fill = XlsxExporter.HEADER_FILL
            c.font = XlsxExporter.HEADER_FONT
            c.alignment = Alignment(horizontal="center")
        for i, g in enumerate(grades, 2):
            ws.cell(row=i, column=1, value=g.student_id)
            ws.cell(row=i, column=2, value=g.version)
            ws.cell(row=i, column=3, value=g.score)
            ws.cell(row=i, column=4, value=g.max_score)
            ws.cell(row=i, column=5, value=g.percentage)
            if i % 2 == 0:
                for col in range(1, 6):
                    ws.cell(row=i, column=col).fill = XlsxExporter.ALT_FILL
        for col in range(1, 6):
            ws.column_dimensions[chr(64 + col)].width = 18

        if report:
            ws2 = wb.create_sheet("Analysis Summary")
            summary_headers = ["Metric", "Value"]
            for col, h in enumerate(summary_headers, 1):
                c = ws2.cell(row=1, column=col, value=h)
                c.fill = XlsxExporter.HEADER_FILL
                c.font = XlsxExporter.HEADER_FONT
            rows = [
                ("Overall Mean", report.overall_mean),
                ("Overall Median", report.overall_median),
                ("Overall Mode", report.overall_mode),
                ("Overall Std Dev", report.overall_stddev),
                ("Fairness Verdict", report.fairness_verdict),
            ]
            for vs in report.version_stats:
                rows.append((f"Version {vs.version} Mean", vs.mean))
                rows.append((f"Version {vs.version} Count", vs.count))
            for i, (k, v) in enumerate(rows, 2):
                ws2.cell(row=i, column=1, value=k)
                ws2.cell(row=i, column=2, value=v)
            ws2.column_dimensions["A"].width = 25
            ws2.column_dimensions["B"].width = 18

        wb.save(output_path)
        logger.info("XLSX exported", path=output_path, count=len(grades))
