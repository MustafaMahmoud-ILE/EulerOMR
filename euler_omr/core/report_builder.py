"""LaTeX analysis report composer; chart generation (matplotlib -> PDF embed)."""
from __future__ import annotations
import os, tempfile, shutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from euler_omr.core.analysis import AnalysisReport
from euler_omr.core.template_compiler import TemplateCompiler
import structlog

logger = structlog.get_logger(__name__)


class ReportBuilder:
    @staticmethod
    def build(report: AnalysisReport, output_path: str, log_callback=None) -> str:
        _log = log_callback or (lambda m, l: None)
        tmp = tempfile.mkdtemp(prefix="euler_report_")
        try:
            # Overall histogram
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.hist(report.overall_scores, bins=range(0, report.max_score + 2), color="#2eb891", edgecolor="#041010", alpha=0.85)
            ax.set_xlabel("Score"); ax.set_ylabel("Frequency"); ax.set_title("Overall Grade Distribution")
            hist_path = os.path.join(tmp, "histogram.png")
            fig.savefig(hist_path, dpi=150, bbox_inches="tight"); plt.close(fig)

            # Per-version boxplot
            if report.version_stats:
                fig, ax = plt.subplots(figsize=(8, 4))
                data = [vs.scores for vs in report.version_stats]
                labels = [vs.version for vs in report.version_stats]
                bp = ax.boxplot(data, labels=labels, patch_artist=True)
                for patch in bp["boxes"]:
                    patch.set_facecolor("#2eb891")
                ax.set_xlabel("Version"); ax.set_ylabel("Score"); ax.set_title("Per-Version Score Distribution")
                box_path = os.path.join(tmp, "boxplot.png")
                fig.savefig(box_path, dpi=150, bbox_inches="tight"); plt.close(fig)

            # Version comparison bar
            if report.version_stats:
                fig, ax = plt.subplots(figsize=(8, 4))
                vers = [vs.version for vs in report.version_stats]
                means = [vs.mean for vs in report.version_stats]
                ax.bar(vers, means, color="#05604b", edgecolor="#041010")
                ax.set_xlabel("Version"); ax.set_ylabel("Mean Score"); ax.set_title("Version Mean Comparison")
                ax.axhline(y=report.overall_mean, color="#e63946", linestyle="--", label=f"Overall Mean ({report.overall_mean})")
                ax.legend()
                bar_path = os.path.join(tmp, "version_bar.png")
                fig.savefig(bar_path, dpi=150, bbox_inches="tight"); plt.close(fig)

            _log("Charts generated", "INFO")

            # Build LaTeX report
            lines = [
                r"\documentclass[a4paper]{article}",
                r"\usepackage[margin=2cm]{geometry}",
                r"\usepackage{graphicx}",
                r"\usepackage{booktabs}",
                r"\usepackage{xcolor}",
                r"\definecolor{euler}{HTML}{2eb891}",
                r"\begin{document}",
                r"\begin{center}{\LARGE\bfseries\color{euler} Euler OMR Analysis Report}\end{center}",
                r"\vspace{5mm}",
                r"\section*{Overall Grade Statistics}",
                f"Mean: {report.overall_mean} \\quad Median: {report.overall_median} \\quad "
                f"Mode: {report.overall_mode} \\quad Std Dev: {report.overall_stddev}",
                r"\begin{center}\includegraphics[width=0.8\textwidth]{histogram.png}\end{center}",
            ]
            if report.version_stats:
                lines += [
                    r"\section*{Per-Version Grade Statistics}",
                    r"\begin{center}\includegraphics[width=0.8\textwidth]{boxplot.png}\end{center}",
                    r"\begin{tabular}{lrrrrr}\toprule",
                    r"Version & Count & Mean & Median & Mode & Std Dev \\ \midrule",
                ]
                for vs in report.version_stats:
                    lines.append(f"{vs.version} & {vs.count} & {vs.mean} & {vs.median} & {vs.mode} & {vs.stddev} \\\\")
                lines += [r"\bottomrule\end{tabular}"]
                lines += [
                    r"\section*{Version Fairness}",
                    f"Verdict: \\textbf{{{report.fairness_verdict}}}",
                    f"\\\\ {report.fairness_explanation}",
                    r"\begin{center}\includegraphics[width=0.8\textwidth]{version_bar.png}\end{center}",
                ]
            lines.append(r"\end{document}")

            tex_path = os.path.join(tmp, "report.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            pdflatex = TemplateCompiler.find_pdflatex()
            if pdflatex:
                import subprocess
                subprocess.run([pdflatex, "-interaction=nonstopmode", "report.tex"], cwd=tmp, capture_output=True)
                pdf_src = os.path.join(tmp, "report.pdf")
                if os.path.exists(pdf_src):
                    shutil.copy2(pdf_src, output_path)
                    _log(f"Analysis report saved to {output_path}", "INFO")
                    return output_path
            _log("pdflatex not available for report compilation", "WARNING")
            return ""
        finally:
            pass  # keep tmp for debugging
