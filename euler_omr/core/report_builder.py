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
            # ── Chart 1: Overall histogram ──
            fig, ax = plt.subplots(figsize=(8, 4))
            bins = range(0, report.max_score + 2)
            ax.hist(report.overall_scores, bins=bins, color="#2eb891",
                    edgecolor="#041010", alpha=0.85, rwidth=0.85)
            ax.set_xlabel("Score", fontsize=11)
            ax.set_ylabel("Frequency", fontsize=11)
            ax.set_title("Overall Grade Distribution", fontsize=13, fontweight="bold")
            ax.set_xticks(range(0, report.max_score + 1))
            hist_path = os.path.join(tmp, "histogram.png")
            fig.savefig(hist_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

            # ── Chart 2: Per-version boxplot ──
            if report.version_stats:
                fig, ax = plt.subplots(figsize=(8, 4))
                data = [vs.scores for vs in report.version_stats]
                labels = [vs.version for vs in report.version_stats]
                bp = ax.boxplot(data, labels=labels, patch_artist=True, widths=0.6)
                colors = plt.cm.Set3(np.linspace(0, 1, len(data)))
                for patch, c in zip(bp["boxes"], colors):
                    patch.set_facecolor(c)
                ax.set_xlabel("Version", fontsize=11)
                ax.set_ylabel("Score", fontsize=11)
                ax.set_title("Per-Version Score Distribution", fontsize=13, fontweight="bold")
                box_path = os.path.join(tmp, "boxplot.png")
                fig.savefig(box_path, dpi=150, bbox_inches="tight")
                plt.close(fig)

            # ── Chart 3: Version mean comparison bar ──
            if report.version_stats:
                fig, ax = plt.subplots(figsize=(8, 4))
                vers = [vs.version for vs in report.version_stats]
                means = [vs.mean for vs in report.version_stats]
                bars = ax.bar(vers, means, color="#05604b", edgecolor="#041010")
                ax.set_xlabel("Version", fontsize=11)
                ax.set_ylabel("Mean Score", fontsize=11)
                ax.set_title("Version Mean Comparison", fontsize=13, fontweight="bold")
                ax.axhline(y=report.overall_mean, color="#e63946", linestyle="--",
                           label=f"Overall Mean ({report.overall_mean})")
                ax.legend()
                bar_path = os.path.join(tmp, "version_bar.png")
                fig.savefig(bar_path, dpi=150, bbox_inches="tight")
                plt.close(fig)

            # ── Chart 4: Per-question choice distribution (all students) ──
            if report.question_choices_overall:
                n_q = len(report.question_choices_overall)
                cols_per_page = 1
                rows_per_page = min(n_q, 6)
                q_chart_paths = []
                for page_start in range(0, n_q, rows_per_page):
                    page_end = min(page_start + rows_per_page, n_q)
                    n_plots = page_end - page_start
                    fig, axes = plt.subplots(n_plots, 1, figsize=(8, 2.2 * n_plots))
                    if n_plots == 1:
                        axes = [axes]
                    for ax_idx, q_idx in enumerate(range(page_start, page_end)):
                        qco = report.question_choices_overall[q_idx]
                        options = sorted([k for k in qco.option_frequencies.keys() if k != "BLANK"])
                        if "BLANK" in qco.option_frequencies:
                            options.append("BLANK")
                        counts = [qco.option_frequencies.get(o, 0) for o in options]
                        pcts = [c / qco.total_responses * 100 if qco.total_responses else 0 for c in counts]
                        bars = axes[ax_idx].barh(options, pcts, color="#2eb891", edgecolor="#041010", height=0.6)
                        axes[ax_idx].set_xlim(0, 100)
                        axes[ax_idx].set_title(f"Q{q_idx + 1}", fontsize=10, fontweight="bold", loc="left")
                        for bar, p, c in zip(bars, pcts, counts):
                            axes[ax_idx].text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                                              f"{c} ({p:.1f}%)", va='center', fontsize=8)
                    plt.tight_layout()
                    chart_name = f"q_choices_{page_start}.png"
                    chart_path = os.path.join(tmp, chart_name)
                    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
                    plt.close(fig)
                    q_chart_paths.append(chart_name)

            _log("Charts generated", "INFO")

            # ═══════════════════════════════════════════════════════════
            #  Build LaTeX report
            # ═══════════════════════════════════════════════════════════
            ms = report.max_score
            pct_mean = round(report.overall_mean / ms * 100, 1) if ms > 0 else 0

            lines = [
                r"\documentclass[a4paper,10pt]{article}",
                r"\usepackage[margin=1.8cm]{geometry}",
                r"\usepackage{graphicx}",
                r"\usepackage{booktabs}",
                r"\usepackage{xcolor}",
                r"\usepackage{longtable}",
                r"\usepackage{multicol}",
                r"\usepackage{fancyhdr}",
                r"\usepackage{amssymb}",
                r"\definecolor{euler}{HTML}{2eb891}",
                r"\definecolor{darkeuler}{HTML}{05604b}",
                r"\pagestyle{fancy}",
                r"\fancyhf{}",
                r"\fancyhead[C]{\color{darkeuler}\textbf{Euler OMR -- Statistical Analysis Report}}",
                r"\fancyfoot[C]{\thepage}",
                r"\begin{document}",
                "",
                r"\begin{center}",
                r"{\LARGE\bfseries\color{euler} Euler OMR -- Statistical Analysis Report}\\[3mm]",
                r"{\small Generated by Euler OMR Grading System}",
                r"\end{center}",
                r"\vspace{3mm}",
                r"\noindent\rule{\textwidth}{1pt}",
                "",
            ]

            # ── Section 1: Overall Statistics ──
            modes = report.overall_mode
            lines += [
                r"\section*{1. Overall Statistics (All Students, All Versions)}",
                r"\begin{tabular}{ll}",
                f"Total Students & {report.total_students} \\\\",
                f"Mean & {report.overall_mean} / {ms} ({pct_mean}\\%) \\\\",
                f"Median & {report.overall_median} \\\\",
                f"Mode & {modes} \\\\",
                f"Std Dev & {report.overall_stddev} \\\\",
                f"Range & {report.overall_min} -- {report.overall_max} \\\\",
                r"\end{tabular}",
                r"\vspace{3mm}",
                "",
                r"\noindent\textbf{Score Distribution:}\\[2mm]",
                r"\begin{tabular}{crr}",
                r"\toprule",
                r"Score & Students & Percentage \\ \midrule",
            ]
            for sd in report.score_distribution:
                lines.append(f"{sd.score}/{ms} & {sd.count} & {sd.percentage}\\% \\\\")
            lines += [
                r"\bottomrule",
                r"\end{tabular}",
                "",
                r"\begin{center}\includegraphics[width=0.85\textwidth]{histogram.png}\end{center}",
                "",
            ]

            # ── Section 2: Per-Version Statistics ──
            if report.version_stats:
                lines += [
                    r"\section*{2. Per-Version Statistics}",
                    r"\begin{center}",
                    r"\begin{tabular}{lrrrrrrr}",
                    r"\toprule",
                    r"Version & N & Mean & \% & Median & Std Dev & Min & Max \\ \midrule",
                ]
                for vs in report.version_stats:
                    pct = round(vs.mean / ms * 100, 1) if ms > 0 else 0
                    lines.append(
                        f"{vs.version} & {vs.count} & {vs.mean} & {pct}\\% & "
                        f"{vs.median} & {vs.stddev} & {vs.min_score} & {vs.max_score_val} \\\\"
                    )
                lines += [
                    r"\bottomrule",
                    r"\end{tabular}",
                    r"\end{center}",
                    "",
                    r"\begin{center}\includegraphics[width=0.85\textwidth]{boxplot.png}\end{center}",
                    "",
                ]

            # ── Section 3: Answer Choice Analysis by Question (All Students) ──
            if report.question_choices_overall:
                lines += [
                    r"\section*{3. Answer Choice Analysis by Question (All Students)}",
                    "",
                ]
                for qco in report.question_choices_overall:
                    q_idx = qco.question_idx
                    lines.append(f"\\noindent\\textbf{{Q{q_idx + 1}}}\\\\[1mm]")
                    options = sorted([k for k in qco.option_frequencies.keys() if k != "BLANK"])
                    if "BLANK" in qco.option_frequencies:
                        options.append("BLANK")
                    for opt in options:
                        cnt = qco.option_frequencies.get(opt, 0)
                        pct = round(cnt / qco.total_responses * 100, 1) if qco.total_responses > 0 else 0.0
                        bar_len = int(pct / 5)  # scale bars
                        bar = "█" * bar_len if bar_len > 0 else ""
                        lines.append(f"\\quad {opt} \\quad {bar} \\quad {cnt} ({pct}\\%)\\\\")
                    lines.append("")

                # Include charts
                for chart_name in q_chart_paths:
                    lines.append(f"\\begin{{center}}\\includegraphics[width=0.9\\textwidth]{{{chart_name}}}\\end{{center}}")
                    lines.append("")

            # ── Section 4: Answer Choice Analysis × Version ──
            if report.question_choices_by_version:
                lines += [
                    r"\section*{4. Answer Choice Analysis by Version}",
                    "",
                ]
                opts = report.active_options if report.active_options else ["A", "B", "C", "D"]
                for qcv in report.question_choices_by_version:
                    q_idx = qcv.question_idx
                    lines.append(f"\\noindent\\textbf{{Q{q_idx + 1}}}\\\\[1mm]")
                    header_opts = " & ".join(opts)
                    col_spec = "l" + "r" * len(opts)
                    lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
                    lines.append(r"\toprule")
                    lines.append(f"Version & {header_opts} \\\\ \\midrule")
                    for ver in sorted(qcv.version_option_pct.keys()):
                        pct_map = qcv.version_option_pct[ver]
                        vals = " & ".join(f"{int(pct_map.get(o, 0))}\\%" for o in opts)
                        lines.append(f"{ver} & {vals} \\\\")
                    lines.append(r"\bottomrule")
                    lines.append(r"\end{tabular}")
                    lines.append(r"\vspace{3mm}")
                    lines.append("")

            # ── Section 5: Version Comparison - Difficulty Ranking ──
            if report.version_ranking:
                lines += [
                    r"\section*{5. Version Comparison -- Difficulty Ranking}",
                    r"\noindent Ranked by Mean Score (Easiest $\rightarrow$ Hardest)\\[2mm]",
                    r"\begin{tabular}{clrl}",
                    r"\toprule",
                    r"Rank & Version & Mean & Difficulty \\ \midrule",
                ]
                for rank_idx, vr in enumerate(report.version_ranking):
                    lines.append(f"{rank_idx + 1} & {vr.version} & {vr.mean} & {vr.difficulty_label} \\\\")
                lines += [
                    r"\bottomrule",
                    r"\end{tabular}",
                    r"\vspace{4mm}",
                    "",
                ]

                # ANOVA results
                anova_sig = "Yes" if report.anova_p < 0.05 else "No"
                anova_mark = r"$\times$" if report.anova_p < 0.05 else r"$\checkmark$"
                lines += [
                    r"\noindent\textbf{ANOVA Test (Are versions statistically equivalent?)}\\[1mm]",
                    f"\\quad F-statistic: {report.anova_f}\\\\",
                    f"\\quad p-value: {report.anova_p}\\\\",
                ]
                if report.anova_p < 0.05:
                    lines.append(r"\quad $\times$ Significant difference found (p $<$ 0.05). Versions are NOT equivalent.\\")
                else:
                    lines.append(r"\quad $\checkmark$ No significant difference (p $\geq$ 0.05). Versions are equivalent.\\")

                lines += [
                    r"\vspace{2mm}",
                    r"\noindent\textbf{Kruskal-Wallis Test (non-parametric)}\\[1mm]",
                    f"\\quad H-statistic: {report.kruskal_h}\\\\",
                    f"\\quad p-value: {report.kruskal_p}\\\\",
                ]
                if report.kruskal_p < 0.05:
                    lines.append(r"\quad $\times$ Non-parametric test also shows significant differences.\\")
                else:
                    lines.append(r"\quad $\checkmark$ Non-parametric test confirms no significant differences.\\")

                # Outlier versions
                if report.version_outliers:
                    lines += [
                        r"\vspace{3mm}",
                        r"\noindent\textbf{Outlier Versions}\\[1mm]",
                        f"\\quad Grand Mean across versions: {report.grand_mean_versions}\\\\",
                        f"\\quad Std of version means: {report.std_version_means}\\\\[2mm]",
                        r"\begin{tabular}{lrrl}",
                        r"\toprule",
                        r"Version & Mean & z-score & Note \\ \midrule",
                    ]
                    for vo in report.version_outliers:
                        sign = "+" if vo.z_score >= 0 else ""
                        note_escaped = vo.label.replace("←", r"$\leftarrow$")
                        lines.append(f"{vo.version} & {vo.mean} & {sign}{vo.z_score} & {note_escaped} \\\\")
                    lines += [
                        r"\bottomrule",
                        r"\end{tabular}",
                        "",
                    ]

                lines.append(r"\begin{center}\includegraphics[width=0.85\textwidth]{version_bar.png}\end{center}")
                lines.append("")

            # ── Section 6: Quick Summary ──
            if report.version_ranking:
                easiest = report.version_ranking[0]
                hardest = report.version_ranking[-1]
                spread = round(easiest.mean - hardest.mean, 3)
            else:
                easiest = hardest = None
                spread = 0

            lines += [
                r"\section*{6. Quick Summary}",
                r"\begin{itemize}",
                f"\\item Total Students: {report.total_students}",
                f"\\item Overall Mean: {report.overall_mean} / {ms} ({pct_mean}\\%)",
                f"\\item Overall Median: {report.overall_median}",
                f"\\item Overall Mode: {modes}",
                f"\\item Overall Std Dev: {report.overall_stddev}",
            ]
            if easiest:
                lines.append(f"\\item Easiest Version: {easiest.version} (mean = {easiest.mean})")
            if hardest:
                lines.append(f"\\item Hardest Version: {hardest.version} (mean = {hardest.mean})")
            lines.append(f"\\item Spread in Means: {spread} points")
            lines.append(f"\\item ANOVA p-value: {report.anova_p} $\\rightarrow$ "
                         + (r"\textbf{NOT equivalent}" if report.anova_p < 0.05 else r"\textbf{Equivalent}"))
            lines += [
                r"\end{itemize}",
                "",
                r"\vspace{5mm}",
                r"\noindent\rule{\textwidth}{1pt}",
                r"\begin{center}{\small End of Report}\end{center}",
                r"\end{document}",
            ]

            tex_path = os.path.join(tmp, "report.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            pdflatex = TemplateCompiler.find_pdflatex()
            if pdflatex:
                import subprocess
                # Run twice for cross-references
                subprocess.run([pdflatex, "-interaction=nonstopmode", "report.tex"], cwd=tmp, capture_output=True)
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
