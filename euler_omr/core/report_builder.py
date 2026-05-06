"""
LaTeX analysis report composer; chart generation (matplotlib -> PDF embed).
"""
from __future__ import annotations
import os, tempfile, shutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import statistics
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
            # Generate Chart 1: Grade distribution histogram
            fig, ax = plt.subplots(figsize=(8, 4))
            max_s_int = int(report.max_score)
            bins = range(0, max_s_int + 2)
            ax.hist(report.overall_scores, bins=bins, color="#117A65",
                    edgecolor="#1B4F72", alpha=0.8, rwidth=0.85)
            ax.set_xlabel("Score", fontsize=11, fontweight="bold", color="#1B4F72")
            ax.set_ylabel("Number of Students", fontsize=11, fontweight="bold", color="#1B4F72")
            ax.set_title("Overall Grade Distribution", fontsize=13, fontweight="bold", color="#1B4F72")
            ax.set_xticks(range(0, max_s_int + 1))
            ax.grid(axis='y', linestyle='--', alpha=0.5)
            hist_path = os.path.join(tmp, "histogram.png")
            fig.savefig(hist_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

            # Generate Chart 2: Mean comparison bar
            if report.version_stats:
                fig, ax = plt.subplots(figsize=(8, 4))
                vers = [vs.version for vs in report.version_stats]
                means = [vs.mean for vs in report.version_stats]
                bars = ax.bar(vers, means, color="#117A65", edgecolor="#1B4F72", alpha=0.7, width=0.6)
                ax.set_xlabel("Version", fontsize=11, fontweight="bold", color="#1B4F72")
                ax.set_ylabel("Mean Score", fontsize=11, fontweight="bold", color="#1B4F72")
                ax.set_title("Version Mean Score Comparison", fontsize=13, fontweight="bold", color="#1B4F72")
                ax.axhline(y=report.overall_mean, color="red", linestyle="--", linewidth=2,
                           label=f"Overall Mean ({report.overall_mean})")
                ax.grid(axis='y', linestyle='--', alpha=0.5)
                ax.legend()
                bar_path = os.path.join(tmp, "version_bar.png")
                fig.savefig(bar_path, dpi=150, bbox_inches="tight")
                plt.close(fig)

            # Generate Chart 3: Box Plot — Score Distribution per Version
            if getattr(report, "version_stats", []):
                fig, ax = plt.subplots(figsize=(8, 4))
                vers = [vs.version for vs in report.version_stats if vs.scores]
                data = [vs.scores for vs in report.version_stats if vs.scores]
                if vers and data:
                    ax.boxplot(data, labels=vers, patch_artist=True, boxprops=dict(facecolor="#117A65", color="#1B4F72", alpha=0.7),
                               capprops=dict(color="#1B4F72"), whiskerprops=dict(color="#1B4F72"),
                               flierprops=dict(markerfacecolor="#C0392B", markeredgecolor="#C0392B", marker='o'),
                               medianprops=dict(color="red", linewidth=2))
                    ax.axhline(y=report.overall_mean, color="red", linestyle="--", linewidth=1.5, label=f"Overall Mean ({report.overall_mean})")
                    ax.set_xlabel("Exam Version", fontsize=10, fontweight="bold", color="#1B4F72")
                    ax.set_ylabel("Score", fontsize=10, fontweight="bold", color="#1B4F72")
                    ax.set_title("Score Distribution Box Plot by Version", fontsize=12, fontweight="bold", color="#1B4F72")
                    ax.grid(axis='y', linestyle='--', alpha=0.4)
                    ax.legend()
                    boxplot_path = os.path.join(tmp, "version_boxplot.png")
                    fig.savefig(boxplot_path, dpi=150, bbox_inches="tight")
                    plt.close(fig)

            # Generate Chart 4: Scatter Plot — Item Difficulty vs. Discrimination
            if getattr(report, "item_psychometrics", []):
                fig, ax = plt.subplots(figsize=(7, 5))
                diffs = [ip.p_value for ip in report.item_psychometrics]
                discs = [ip.discrimination_index for ip in report.item_psychometrics]
                labels = [f"Q{ip.question_idx+1}" for ip in report.item_psychometrics]
                ax.scatter(diffs, discs, color="#117A65", edgecolor="#1B4F72", s=80, zorder=5)
                for i, txt in enumerate(labels):
                    ax.annotate(txt, (diffs[i], discs[i]), xytext=(5, 5), textcoords="offset points", fontsize=9, fontweight="bold")
                ax.axvspan(0.3, 0.7, color="#1E8449", alpha=0.1, label="Optimal Difficulty")
                ax.axhspan(0.3, 1.0, color="#117A65", alpha=0.1, label="Good Discrimination")
                ax.set_xlabel("Difficulty (p-value)", fontsize=10, fontweight="bold", color="#1B4F72")
                ax.set_ylabel("Discrimination Index (D)", fontsize=10, fontweight="bold", color="#1B4F72")
                ax.set_title("Item Difficulty vs. Discrimination", fontsize=12, fontweight="bold", color="#1B4F72")
                ax.set_xlim(0, 1.05)
                ax.set_ylim(-0.2, 1.05)
                ax.grid(linestyle='--', alpha=0.4)
                ax.legend(loc="lower right")
                scatter_path = os.path.join(tmp, "item_scatter.png")
                fig.savefig(scatter_path, dpi=150, bbox_inches="tight")
                plt.close(fig)

            # Generate Chart 5: Stacked Bar Chart — At-Risk Students by Version
            if getattr(report, "at_risk_students", []):
                fig, ax = plt.subplots(figsize=(8, 4))
                vers = sorted(list(set([vs.version for vs in report.version_stats])))
                scores = [0, 1, 2]
                colors = ["#C0392B", "#D35400", "#F39C12"]
                counts = {s: {v: 0 for v in vers} for s in scores}
                for stu in report.at_risk_students:
                    v = stu.get("version", "--")
                    s = int(stu["score"])
                    if s in counts and v in vers:
                        counts[s][v] += 1
                bottom = np.zeros(len(vers))
                for s, color in zip(scores, colors):
                    s_counts = [counts[s][v] for v in vers]
                    ax.bar(vers, s_counts, bottom=bottom, color=color, edgecolor="#1B4F72", alpha=0.8, label=f"Score {s}")
                    bottom += np.array(s_counts)
                ax.set_xlabel("Exam Version", fontsize=10, fontweight="bold", color="#1B4F72")
                ax.set_ylabel("Number of At-Risk Students", fontsize=10, fontweight="bold", color="#1B4F72")
                ax.set_title("At-Risk Student Concentration by Version", fontsize=12, fontweight="bold", color="#1B4F72")
                ax.legend()
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                at_risk_chart_path = os.path.join(tmp, "at_risk_bar.png")
                fig.savefig(at_risk_chart_path, dpi=150, bbox_inches="tight")
                plt.close(fig)

            # Generate Chart 6: Heatmap — Inter-Item Correlation Matrix
            if getattr(report, "inter_item_correlation", []):
                fig, ax = plt.subplots(figsize=(6, 5))
                mat = np.array(report.inter_item_correlation)
                n = len(mat)
                cmap = matplotlib.colors.LinearSegmentedColormap.from_list("rg", ["#C0392B", "#F1C40F", "#1E8449"])
                cax = ax.matshow(mat, cmap=cmap, vmin=0, vmax=1)
                fig.colorbar(cax)
                ax.set_xticks(range(n))
                ax.set_yticks(range(n))
                ax.set_xticklabels([f"Q{i+1}" for i in range(n)])
                ax.set_yticklabels([f"Q{i+1}" for i in range(n)])
                for i in range(n):
                    for j in range(n):
                        val = mat[i, j]
                        text_color = "white" if val < 0.2 or val > 0.8 else "black"
                        ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=text_color, fontweight="bold")
                ax.set_title("Inter-Item Correlation Matrix", pad=20, fontsize=12, fontweight="bold", color="#1B4F72")
                heatmap_path = os.path.join(tmp, "correlation_heatmap.png")
                fig.savefig(heatmap_path, dpi=150, bbox_inches="tight")
                plt.close(fig)

            # Generate Chart 7: Bar Chart — Score Equating Adjustments by Version
            if getattr(report, "equated_scores", {}):
                fig, ax = plt.subplots(figsize=(8, 4))
                vers = list(report.equated_scores.keys())
                adjs = [eq["adjustment"] for eq in report.equated_scores.values()]
                colors = ["#1E8449" if a > 0 else "#C0392B" for a in adjs]
                bars = ax.bar(vers, adjs, color=colors, edgecolor="#1B4F72", alpha=0.8, width=0.6)
                ax.axhline(0, color="black", linewidth=1.2)
                ax.set_xlabel("Exam Version", fontsize=10, fontweight="bold", color="#1B4F72")
                ax.set_ylabel("Equating Adjustment (Points)", fontsize=10, fontweight="bold", color="#1B4F72")
                ax.set_title("Score Equating Adjustments by Version", fontsize=12, fontweight="bold", color="#1B4F72")
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                for bar in bars:
                    yval = bar.get_height()
                    offset = 0.05 if yval > 0 else -0.15
                    ax.text(bar.get_x() + bar.get_width()/2.0, yval + offset, f"{yval:+.3f}", ha='center', va='bottom' if yval>0 else 'top', fontweight="bold", fontsize=9)
                equating_path = os.path.join(tmp, "equating_bar.png")
                fig.savefig(equating_path, dpi=150, bbox_inches="tight")
                plt.close(fig)

            _log("Charts generated successfully.", "INFO")

            ms = report.max_score
            pct_mean = round(report.overall_mean / ms * 100, 1) if ms > 0 else 0
            modes_str = str(report.overall_mode)

            lines = [
                r"\documentclass[12pt, a4paper]{article}",
                r"\usepackage[margin=2.5cm]{geometry}",
                r"\usepackage{booktabs}",
                r"\usepackage{array}",
                r"\usepackage{xcolor}",
                r"\usepackage{colortbl}",
                r"\usepackage{graphicx}",
                r"\usepackage{amsmath}",
                r"\usepackage{hyperref}",
                r"\usepackage{fancyhdr}",
                r"\usepackage{titlesec}",
                r"\usepackage{multirow}",
                r"\usepackage{enumitem}",
                r"\usepackage{tcolorbox}",
                r"\usepackage{float}",
                r"\usepackage{caption}",
                "",
                r"\definecolor{primary}{HTML}{1B4F72}",
                r"\definecolor{accent}{HTML}{117A65}",
                r"\definecolor{lightgray}{HTML}{F2F3F4}",
                r"\definecolor{medgray}{HTML}{BDC3C7}",
                r"\definecolor{danger}{HTML}{C0392B}",
                r"\definecolor{warning}{HTML}{D4AC0D}",
                r"\definecolor{success}{HTML}{1E8449}",
                r"\definecolor{rowA}{HTML}{EBF5FB}",
                r"\definecolor{rowB}{HTML}{FFFFFF}",
                "",
                r"\pagestyle{fancy}",
                r"\fancyhf{}",
                r"\fancyhead[L]{\small\color{primary}\textbf{Euler OMR} --- Comprehensive Psychometric Report}",
                r"\fancyhead[R]{\small\color{medgray}Assessment Evaluation System}",
                r"\fancyfoot[C]{\small\color{medgray}\thepage}",
                r"\renewcommand{\headrulewidth}{0.4pt}",
                r"\renewcommand{\footrulewidth}{0pt}",
                "",
                r"\titleformat{\section}{\large\bfseries\color{primary}}{\thesection.}{0.5em}{}[\titrule]",
                r"\titleformat{\subsection}{\normalsize\bfseries\color{accent}}{\thesubsection}{0.5em}{}",
                "",
                r"\hypersetup{colorlinks=true, linkcolor=primary, urlcolor=accent}",
                "",
                r"\tcbuselibrary{skins, breakable}",
                r"\newtcolorbox{summarybox}{",
                r"	enhanced, colback=lightgray, colframe=primary, boxrule=1pt, arc=4pt,",
                r"	left=8pt, right=8pt, top=6pt, bottom=6pt,",
                r"	title={\bfseries\color{white} Summary Insight},",
                r"	fonttitle=\bfseries, coltitle=white,",
                r"	attach boxed title to top left={yshift=-2mm, xshift=4mm},",
                r"	boxed title style={colback=primary, arc=3pt}",
                r"}",
                "",
                r"\begin{document}",
            ]
            alpha = getattr(report, "cronbach_alpha", 0.0)
            if alpha >= 0.90:
                alpha_class = "Excellent"
                alpha_col = r"\textcolor{success}{\textbf{Excellent}}"
            elif alpha >= 0.80:
                alpha_class = "Good"
                alpha_col = r"\textcolor{success}{\textbf{Good}}"
            elif alpha >= 0.70:
                alpha_class = "Acceptable"
                alpha_col = r"\textcolor{warning}{\textbf{Acceptable}}"
            else:
                alpha_class = "Needs Review"
                alpha_col = r"\textcolor{danger}{\textbf{Needs Review}}"

            split_half = getattr(report, "split_half_reliability", 0.0)
            if split_half >= 0.90:
                split_half_col = r"\textcolor{success}{\textbf{Excellent}}"
            elif split_half >= 0.80:
                split_half_col = r"\textcolor{success}{\textbf{Good}}"
            elif split_half >= 0.70:
                split_half_col = r"\textcolor{warning}{\textbf{Acceptable}}"
            else:
                split_half_col = r"\textcolor{danger}{\textbf{Needs Review}}"

            if report.anova_p >= 0.05:
                ver_eq = "No statistically significant difference detected across versions."
                ver_col = r"\textcolor{success}{\textbf{No sig diff}}"
            else:
                ver_eq = "Statistically significant difference exists between versions."
                ver_col = r"\textcolor{danger}{\textbf{Significant diff}}"

            pattern_flag_count = 0
            for qcv in getattr(report, 'question_choices_by_version', []):
                for ver in qcv.version_option_pct.keys():
                    pct_map = qcv.version_option_pct[ver]
                    corr_keys = qcv.version_correct_keys.get(ver, [])
                    if not corr_keys:
                        corr_keys = ["A"]
                    correct_pct = sum(pct_map.get(k, 0.0) for k in corr_keys)
                    incorrect_pcts = {k: v for k, v in pct_map.items() if k not in corr_keys}
                    if incorrect_pcts:
                        max_inc_k = max(incorrect_pcts, key=incorrect_pcts.get)
                        max_inc_pct = incorrect_pcts[max_inc_k]
                        all_pcts = list(pct_map.values())
                        pct_range = max(all_pcts) - min(all_pcts) if all_pcts else 0
                        if max_inc_pct > correct_pct or (correct_pct <= 35.0 and pct_range <= 20.0):
                            pattern_flag_count += 1

            if report.item_psychometrics:
                easiest_item = max(report.item_psychometrics, key=lambda x: x.p_value)
                hardest_item = min(report.item_psychometrics, key=lambda x: x.p_value)
                best_disc = max(report.item_psychometrics, key=lambda x: x.discrimination_index)
                base_flagged_count = sum(1 for x in report.item_psychometrics if x.quality_class in ["Needs Review", "Poor"])
                flagged_count = base_flagged_count + pattern_flag_count
                
                flag_str = r"\textcolor{danger}{\textbf{" + str(flagged_count) + "}}" if flagged_count > 0 else r"\textcolor{success}{\textbf{0}}"
                hardest_str = f"Q{hardest_item.question_idx+1} ($p={hardest_item.p_value}$)"
                easiest_str = f"Q{easiest_item.question_idx+1} ($p={easiest_item.p_value}$)"
                best_d_str = f"Q{best_disc.question_idx+1} ($D={best_disc.discrimination_index}$)"
            else:
                flag_str = "--"
                hardest_str = "--"
                easiest_str = "--"
                best_d_str = "--"
                flagged_count = pattern_flag_count

            rec_actions = [f"       \\item Test reliability is classified as \\textbf{{{alpha_class}}}."]
            if alpha < 0.70:
                rec_actions.append(r"       \item \textcolor{danger}{\textbf{Critical Warning:}} Test length or item quality is insufficient for reliable institutional grading.")
            if flagged_count > 0:
                rec_actions.append(f"       \\item \\textcolor{{warning}}{{\\textbf{{Action Required:}}}} Review {flagged_count} flagged anomaly(s) (including poor psychometrics and critical pattern distractors) to improve assessment quality.")
            rec_actions.append(f"       \\item {ver_eq}")

            lines += [
                "",
                r"% Title Page & Executive Dashboard",
                r"\begin{titlepage}",
                r"	\centering",
                r"	\vspace*{0.5cm}",
                r"	{\Huge\bfseries\color{primary} Euler OMR\par}",
                r"	\vspace{0.4cm}",
                r"	{\LARGE\color{accent} Assessment Analytics \& Evaluation Dashboard\par}",
                r"	\vspace{0.6cm}",
                r"	\textcolor{medgray}{\rule{0.6\textwidth}{0.6pt}}",
                r"	\vspace{0.6cm}",
                r"	",
                r"	\begin{tcolorbox}[width=0.85\textwidth, colback=lightgray, colframe=primary, arc=4pt, boxrule=0.8pt]",
                r"		\centering",
                r"       \textbf{\large Executive Dashboard \& Test Quality Overview}\\[8pt]",
                r"		\renewcommand{\arraystretch}{1.3}",
                r"		\begin{tabular}{r@{\hspace{0.4cm}}l}",
                f"			\\textbf{{Total Students:}} & {report.total_students} \\\\",
                f"			\\textbf{{Overall Mean:}}   & {report.overall_mean} / {ms} ({pct_mean}\\%) \\\\",
                f"			\\textbf{{Reliability ($\\alpha$):}} & {alpha} ({alpha_col}) \\\\",
                f"			\\textbf{{Split-Half:}} & {split_half} ({split_half_col}) \\\\",
                f"			\\textbf{{Version Fairness:}} & {ver_col} \\\\[4pt]",
                f"			\\textbf{{Flagged Items:}} & {flag_str} \\\\",
                f"			\\textbf{{Hardest Item:}} & {hardest_str} \\\\",
                f"			\\textbf{{Easiest Item:}} & {easiest_str} \\\\",
                f"			\\textbf{{Best Discriminator:}} & {best_d_str} \\\\",
                r"		\end{tabular}",
                r"	\end{tcolorbox}",
                r"	",
                r"	\vspace{0.5cm}",
                r"	\begin{tcolorbox}[width=0.95\textwidth, colback=white, colframe=medgray, arc=4pt, boxrule=0.6pt, left=8pt, right=8pt]",
                r"		\textbf{Summary and Recommended Academic Actions:}",
                r"		\vspace{-0.2cm}",
                r"		\begin{itemize}[leftmargin=1.5em, label={--}]",
                "\n".join(rec_actions),
                r"		\end{itemize}",
                r"	\end{tcolorbox}",
                r"	",
                r"	\vfill",
                r"	{\small\color{medgray} Generated by Euler OMR Assessment Engine}",
                r"\end{titlepage}",
                "",
                r"\section{Reliability Analysis}",
                r"\begin{table}[H]",
                r"	\centering",
                r"	\caption{Reliability Coefficients Summary}",
                r"	\renewcommand{\arraystretch}{1.3}",
                r"	\begin{tabular}{lcl}",
                r"		\toprule",
                r"		\rowcolor{primary}",
                r"		\color{white}\textbf{Metric} & \color{white}\textbf{Calculated Value} & \color{white}\textbf{Status} \\ \midrule",
                f"		\\rowcolor{{rowA}} Cronbach's Alpha (KR-20) & {alpha} & {alpha_col} \\\\",
                f"		\\rowcolor{{rowB}} Split-Half Reliability & {split_half} & {split_half_col} \\\\",
                r"		\bottomrule",
                r"	\end{tabular}",
                r"\end{table}",
            ]

            # Explanation: Reliability
            lines += [
                "",
                r"\begin{tcolorbox}[width=0.95\textwidth, colback=rowA, colframe=accent, arc=4pt, boxrule=0.6pt, left=8pt, right=8pt]",
                r"	\textbf{\color{accent}What does this mean?}\\[4pt]",
                r"	\textbf{Cronbach's Alpha (KR-20)} measures how consistently the test questions work together. Think of it as: ``If a student is good, do all questions agree that the student is good?''\\",
                r"	\textbf{Split-Half Reliability} splits the test into two halves and checks if both halves give similar results.\\[4pt]",
                r"	\textbf{Benchmark Scale:}\\",
                r"	\begin{tabular}{ll}",
                r"		$\ge 0.90$ & \textcolor{success}{\textbf{Excellent}} --- Very consistent, suitable for high-stakes decisions \\",
                r"		$0.80 - 0.89$ & \textcolor{success}{\textbf{Good}} --- Reliable enough for classroom grading \\",
                r"		$0.70 - 0.79$ & \textcolor{warning}{\textbf{Acceptable}} --- Minimally acceptable; consider improving weak items \\",
                r"		$< 0.70$ & \textcolor{danger}{\textbf{Needs Review}} --- Too inconsistent for reliable grading \\",
                r"	\end{tabular}",
                r"\end{tcolorbox}",
            ]

            if getattr(report, "inter_item_correlation", []):
                n_cols = len(report.inter_item_correlation)
                lines += [
                    r"\vspace{0.5cm}",
                    r"\begin{table}[H]",
                    r"	\centering",
                    r"	\caption{Inter-Item Correlation Matrix (First 5 Items)}",
                    r"	\renewcommand{\arraystretch}{1.3}",
                    r"	\begin{tabular}{c|" + "c" * n_cols + "}",
                    r"		\toprule",
                    r"		\rowcolor{primary}",
                    r"		\color{white}\textbf{Item} & " + " & ".join(f"\\color{{white}}\\textbf{{Q{j+1}}}" for j in range(n_cols)) + r" \\ \midrule",
                ]
                for i, row in enumerate(report.inter_item_correlation):
                    bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                    formatted_row = []
                    for j, r_val in enumerate(row):
                        if i == j:
                            formatted_row.append(str(r_val))
                        elif r_val < 0.15:
                            formatted_row.append(f"\\textcolor{{danger}}{{\\textbf{{{r_val}}}}}")
                        else:
                            formatted_row.append(str(r_val))
                    lines.append(f"		{bg}\\textbf{{Q{i+1}}} & " + " & ".join(formatted_row) + r" \\\\")
                lines += [
                    r"		\bottomrule",
                    r"	\end{tabular}",
                    r"\end{table}",
                    r"	\begin{center}\textcolor{medgray}{\textit{*Note: Values below 0.15 are highlighted in red as they may indicate items measuring different constructs.}}\end{center}",
                    "",
                    r"\begin{figure}[H]",
                    r"	\centering",
                    r"	\includegraphics[width=0.65\textwidth]{correlation_heatmap.png}",
                    r"	\caption{Heatmap of the Inter-Item Correlation Matrix}",
                    r"\end{figure}",
                ]
            lines += [
                "",
                r"\section{Descriptive Statistics}",
                r"\begin{center}",
                r"	\begin{tcolorbox}[width=0.7\textwidth, colback=rowA, colframe=primary, arc=4pt, boxrule=0.8pt]",
                r"		\centering",
                r"		\renewcommand{\arraystretch}{1.4}",
                r"		\begin{tabular}{>{\bfseries}l r}",
                r"			\toprule",
                r"			\multicolumn{1}{c}{\color{primary}\textbf{Statistic}} & \multicolumn{1}{c}{\color{primary}\textbf{Value}} \\ \midrule",
                f"			Total Students & {report.total_students} \\\\",
                f"			Mean Score & {report.overall_mean} / {ms} \\quad ({pct_mean}\\%) \\\\",
                f"			Median & {report.overall_median} \\\\",
                f"			Mode & {modes_str} \\\\",
                f"			Std Deviation & {report.overall_stddev} \\\\",
                f"			Range & {report.overall_min} -- {report.overall_max} \\\\",
                r"			\bottomrule",
                r"		\end{tabular}",
                r"	\end{tcolorbox}",
                r"\end{center}",
                "",
                r"\begin{tcolorbox}[width=0.95\textwidth, colback=rowA, colframe=accent, arc=4pt, boxrule=0.6pt, left=8pt, right=8pt]",
                r"	\textbf{\color{accent}What does this mean?}\\[4pt]",
                r"	\textbf{Mean (Average):} The total of all scores divided by the number of students. A class mean around 60--75\% of max score is typical for a well-balanced exam.\\",
                r"	\textbf{Median:} The middle score when all scores are sorted. If the median is much lower than the mean, a few high scorers are pulling the average up.\\",
                r"	\textbf{Mode:} The most frequently occurring score --- the ``most common grade.''\\",
                r"	\textbf{Standard Deviation (Std Dev):} How spread out the scores are. A small value means most students scored similarly; a large value means wide variation.\\",
                r"	\textbf{Range:} The gap between the lowest and highest score.\\[4pt]",
                r"	\textbf{Quick Reference:} If Mean $\ge 70\%$ of max score, the exam may be easy. If Mean $\le 40\%$, the exam may be too hard or poorly taught.",
                r"\end{tcolorbox}",
                "",
                r"\section{Score Distributions}",
                r"\begin{table}[H]",
                r"	\centering",
                r"	\caption{Score Frequency Summary}",
                r"	\renewcommand{\arraystretch}{1.3}",
                r"	\begin{tabular}{ccc}",
                r"		\toprule",
                r"		\rowcolor{primary}",
                r"		\color{white}\textbf{Score} & \color{white}\textbf{Students} & \color{white}\textbf{Percentage} \\ \midrule",
            ]

            for i, sd in enumerate(report.score_distribution):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                lines.append(f"		{bg}{sd.score} / {ms} & {sd.count} & {sd.percentage}\\% \\\\")

            lines += [
                r"		\bottomrule",
                r"	\end{tabular}",
                r"\end{table}",
                "",
                r"\begin{figure}[H]",
                r"	\centering",
                r"	\includegraphics[width=0.82\textwidth]{histogram.png}",
                r"	\caption{Overall score curve distribution chart}",
                r"\end{figure}",
                "",
                r"\newpage",
                r"\section{Per-Version Performance Stats}",
                r"\begin{table}[H]",
                r"	\centering",
                r"	\caption{Overall Version Stats Breakdown}",
                r"	\renewcommand{\arraystretch}{1.35}",
                r"	\begin{tabular}{cccccccc}",
                r"		\toprule",
                r"		\rowcolor{primary}",
                r"		\color{white}\textbf{Version} &",
                r"		\color{white}\textbf{N} &",
                r"		\color{white}\textbf{Mean} &",
                r"		\color{white}\textbf{\%} &",
                r"		\color{white}\textbf{Median} &",
                r"		\color{white}\textbf{Std Dev} &",
                r"		\color{white}\textbf{Min} &",
                r"		\color{white}\textbf{Max} \\ \midrule",
            ]

            for i, vs in enumerate(report.version_stats):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                v_pct = round(vs.mean / ms * 100, 1) if ms > 0 else 0
                lines.append(f"		{bg}{vs.version} & {vs.count} & {vs.mean} & {v_pct}\\% & {vs.median} & {vs.stddev} & {vs.min_score} & {vs.max_score_val} \\\\")

            lines += [
                r"		\bottomrule",
                r"	\end{tabular}",
                r"\end{table}",
                "",
                r"\begin{figure}[H]",
                r"	\centering",
                r"	\includegraphics[width=0.82\textwidth]{version_bar.png}",
                r"	\caption{Mean score comparison across exam versions}",
                r"\end{figure}",
                "",
                r"\begin{tcolorbox}[width=0.95\textwidth, colback=rowA, colframe=accent, arc=4pt, boxrule=0.6pt, left=8pt, right=8pt]",
                r"	\textbf{\color{accent}What does this mean?}\\[4pt]",
                r"	\textbf{Per-Version Stats} compares how students performed on each version of the exam (A, B, C, etc.).\\[4pt]",
                r"	\textbf{Why it matters:} If one version's mean is much lower than the others, that version may be unfairly harder. Ideally, all versions should have similar means (within 5--10\% of each other).",
                r"\end{tcolorbox}",
                "",
                r"\newpage",
                r"\section{Score Distribution by Version (Box Plot)}",
                r"\begin{figure}[H]",
                r"	\centering",
                r"	\includegraphics[width=0.95\textwidth]{version_boxplot.png}",
                r"	\caption{Box plot comparing score distribution across exam versions}",
                r"	\vspace{0.5cm}",
                r"	\textcolor{medgray}{\textit{*Note: Red horizontal line denotes the overall class mean. Boxes indicate interquartile range (IQR).}}",
                r"\end{figure}",
                "",
                r"\begin{tcolorbox}[width=0.95\textwidth, colback=rowA, colframe=accent, arc=4pt, boxrule=0.6pt, left=8pt, right=8pt]",
                r"	\textbf{\color{accent}What does this mean?}\\[4pt]",
                r"	\textbf{Box Plot:} Each ``box'' shows the middle 50\% of scores for a version. The line inside the box is the median (middle score). The ``whiskers'' (lines extending from the box) show the full range, and dots outside are outliers (unusually high or low scores).\\[4pt]",
                r"	\textbf{How to read it:} A taller box means more variability. If one box is much lower than the others, that version was harder.",
                r"\end{tcolorbox}",
                "",
                r"\newpage",
                r"\section{Answer Choice Distribution By Question}",
                r"\begin{table}[H]",
                r"	\centering",
                r"	\caption{Answer Choice Frequency Across All Students}",
                r"	\renewcommand{\arraystretch}{1.3}",
                r"	\begin{tabular}{ccccccc}",
                r"		\toprule",
                r"		\rowcolor{primary}",
                r"		\color{white}\textbf{Q} & \color{white}\textbf{Key} & \color{white}\textbf{A} & \color{white}\textbf{B} & \color{white}\textbf{C} & \color{white}\textbf{D} & \color{white}\textbf{Blank} \\ \midrule",
            ]

            for i, qco in enumerate(report.question_choices_overall):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                freq = qco.option_frequencies
                opts = []
                for o in ["A", "B", "C", "D"]:
                    c = freq.get(o, 0)
                    p = round(c / qco.total_responses * 100, 1) if qco.total_responses > 0 else 0
                    opts.append(f"{c} ({p}\\%)")
                blank_cnt = freq.get("BLANK", 0)
                blank_p = round(blank_cnt / qco.total_responses * 100, 1) if qco.total_responses > 0 else 0
                blank_str = f"{blank_cnt} ({blank_p}\\%)" if blank_cnt > 0 else "--"
                key_str = ", ".join(qco.correct_keys) if qco.correct_keys else "--"
                lines.append(f"		{bg}Q{i+1} & {key_str} & " + " & ".join(opts) + f" & {blank_str} \\\\")

            lines += [
                r"		\bottomrule",
                r"	\end{tabular}",
                r"\end{table}",
                "",
                r"\newpage",
                r"\section{Advanced Item Analysis: Difficulty \& Discrimination}",
                r"\begin{table}[H]",
                r"	\centering",
                r"	\caption{Complete Advanced Question Metrics}",
                r"	\renewcommand{\arraystretch}{1.3}",
                r"	\resizebox{0.95\textwidth}{!}{%",
                r"	\begin{tabular}{ccccccc}",
                r"		\toprule",
                r"		\rowcolor{primary}",
                r"		\color{white}\textbf{Q} & \color{white}\textbf{Key} & \color{white}\textbf{p-value} & \color{white}\textbf{Discrimination} & \color{white}\textbf{Point-Biserial} & \color{white}\textbf{Distractor Eff.} & \color{white}\textbf{Status} \\ \midrule",
            ]

            for i, psy in enumerate(report.item_psychometrics):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                key_str = ", ".join(psy.correct_keys) if psy.correct_keys else "--"
                if psy.quality_class == "Excellent":
                    status_str = r"\textcolor{success}{\textbf{Excellent}}"
                elif psy.quality_class == "Acceptable":
                    status_str = r"\textcolor{success}{\textbf{Acceptable}}"
                elif psy.quality_class == "Needs Review":
                    status_str = r"\textcolor{warning}{\textbf{Needs Review}}"
                else:
                    status_str = r"\textcolor{danger}{\textbf{Poor}}"

                lines.append(f"		{bg}Q{psy.question_idx+1} & {key_str} & {psy.p_value} & {psy.discrimination_index} & {psy.point_biserial} & {psy.distractor_efficiency}\\% & {status_str} \\\\")

            lines += [
                r"		\bottomrule",
                r"	\end{tabular}%",
                r"	}",
                r"\end{table}",
                "",
                r"\begin{figure}[H]",
                r"	\centering",
                r"	\includegraphics[width=0.75\textwidth]{item_scatter.png}",
                r"	\caption{Scatter plot of item difficulty (p-value) vs. discrimination (D)}",
                r"\end{figure}",
                "",
                r"\begin{tcolorbox}[width=0.95\textwidth, colback=lightgray, colframe=primary, arc=4pt, boxrule=0.6pt, left=8pt, right=8pt]",
                r"	\textbf{Psychometrics Standard Threshold Interpretation Reference:}\\",
                r"	\textbf{Difficulty (p-value):} Very Easy $>0.90$, Easy $0.70-0.90$, Moderate $0.30-0.70$, Difficult $<0.30$.\\",
                r"	\textbf{Discrimination (D):} Excellent $\ge 0.40$, Good $0.30-0.39$, Acceptable $0.20-0.29$, Weak/Poor $<0.20$.\\",
                r"	\textcolor{medgray}{\textit{*Note: $0\%$ Distractor Efficiency on items with Excellent/Good Discrimination simply indicates strong mastery; no distractor was necessary to trick top-performing students.}}",
                r"\end{tcolorbox}",
                "",
                r"\begin{tcolorbox}[width=0.95\textwidth, colback=white, colframe=danger, arc=4pt, boxrule=0.8pt, left=8pt, right=8pt]",
                r"	\textbf{\color{danger}Actionable Recommendations:}\\",
                r"	\textbf{Item-Level Recommendations:}\\",
            ]

            recs_added = False
            for psy in report.item_psychometrics:
                if psy.quality_class in ["Needs Review", "Poor"]:
                    recs_added = True
                    desc = "Extremely easy" if psy.p_value > 0.90 else "Highly difficult" if psy.p_value < 0.30 else "Moderate difficulty"
                    lines.append(f"    --- \\textbf{{Q{psy.question_idx+1}}}: \\textbf{{Problem:}} {desc} ($p = {psy.p_value}$) and low discrimination ($D = {psy.discrimination_index}$). \\textbf{{Affected:}} All students. \\textbf{{Action:}} Consider removing from grading or revising distractors. \\\\")

            if not recs_added:
                lines.append(r"    --- All items performed optimally across test difficulty and discrimination bounds. \\")

            lines.append(r"	\vspace{4pt}\textbf{Version-Level Recommendations:}\\")
            ver_recs_added = False
            
            for qcv in getattr(report, 'question_choices_by_version', []):
                for ver, pct_map in qcv.version_option_pct.items():
                    corr_keys = qcv.version_correct_keys.get(ver, [])
                    if not corr_keys:
                        corr_keys = ["A"]
                    correct_pct = sum(pct_map.get(k, 0.0) for k in corr_keys)
                    incorrect_pcts = {k: v for k, v in pct_map.items() if k not in corr_keys}
                    if incorrect_pcts:
                        max_inc_k = max(incorrect_pcts, key=incorrect_pcts.get)
                        max_inc_pct = incorrect_pcts[max_inc_k]
                        if max_inc_pct > correct_pct:
                            ver_recs_added = True
                            lines.append(f"    --- \\textbf{{Q{qcv.question_idx+1} (Version {ver})}}: \\textbf{{Problem:}} Option {max_inc_k} pulled more students than the correct key. \\textbf{{Affected:}} Version {ver} students. \\textbf{{Action:}} Verify answer key and check for printing errors. \\\\")
            if getattr(report, "anova_p", 1.0) < 0.05:
                ver_recs_added = True
                lines.append(r"    --- \textbf{Global Fairness}: \textbf{Problem:} Statistically significant difference between versions. \textbf{Affected:} Disadvantaged versions. \textbf{Action:} Apply score equating before releasing final grades. \\")
                
            if not ver_recs_added:
                lines.append(r"    --- No critical version-specific anomalies detected. \\")

            lines += [
                r"\end{tcolorbox}",
                "",
                r"\newpage",
                r"\section{Detailed Answer Patterns by Version}",
            ]

            for qcv in report.question_choices_by_version:
                q_idx = qcv.question_idx
                lines += [
                    f"\\subsection{{Question {q_idx + 1}}}",
                    r"\begin{table}[H]",
                    r"	\centering",
                    r"	\renewcommand{\arraystretch}{1.3}",
                    r"	\begin{tabular}{l ccccc m{5.5cm}}",
                    r"		\toprule",
                    r"		\rowcolor{primary}",
                    r"		\color{white}\textbf{Version} & \color{white}\textbf{A} & \color{white}\textbf{B} & \color{white}\textbf{C} & \color{white}\textbf{D} & \color{white}\textbf{Pattern} & \color{white}\textbf{Insight} \\ \midrule",
                ]
                for i, ver in enumerate(sorted(qcv.version_option_pct.keys())):
                    bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                    pct_map = qcv.version_option_pct[ver]
                    vals = " & ".join(f"{int(pct_map.get(o, 0))}\\%" for o in ["A", "B", "C", "D"])
                    corr_keys = qcv.version_correct_keys.get(ver, [])
                    if not corr_keys:
                        corr_keys = ["A"]
                    correct_pct = sum(pct_map.get(k, 0.0) for k in corr_keys)
                    incorrect_pcts = {k: v for k, v in pct_map.items() if k not in corr_keys}
                    if incorrect_pcts:
                        max_inc_k = max(incorrect_pcts, key=incorrect_pcts.get)
                        max_inc_pct = incorrect_pcts[max_inc_k]
                        all_pcts = list(pct_map.values())
                        pct_range = max(all_pcts) - min(all_pcts) if all_pcts else 0
                        
                        if max_inc_pct > correct_pct:
                            status = r"\textcolor{danger}{\textbf{Critical}}"
                            insight = f"Option {max_inc_k} pulled more students than correct key."
                        elif correct_pct <= 35.0 and pct_range <= 20.0:
                            status = r"\textcolor{danger}{\textbf{Warning}}"
                            insight = "Scattered options."
                        elif correct_pct - max_inc_pct <= 15.0:
                            status = r"\textcolor{warning}{\textbf{Moderate}}"
                            insight = f"Option {max_inc_k} closely competing."
                        else:
                            status = r"\textcolor{success}{\textbf{Optimal}}"
                            insight = "--"
                    else:
                        status = r"\textcolor{success}{\textbf{Optimal}}"
                        insight = "--"
                    lines.append(f"		{bg}{ver} & {vals} & {status} & {insight} \\\\")
                lines += [
                    r"		\bottomrule",
                    r"	\end{tabular}",
                    r"\end{table}",
                    "",
                ]

            lines += [
                r"\newpage",
                r"\section{Topic-Based Outcomes}",
                r"\begin{table}[H]",
                r"	\centering",
                r"	\caption{Learning Mastery Breakdown}",
                r"	\renewcommand{\arraystretch}{1.3}",
                r"	\begin{tabular}{lclcc}",
                r"		\toprule",
                r"		\rowcolor{primary}",
                r"		\color{white}\textbf{Topic ID} & \color{white}\textbf{Questions} & \color{white}\textbf{Difficulty} & \color{white}\textbf{Discrimination} & \color{white}\textbf{Status} \\ \midrule",
            ]

            for i, t in enumerate(getattr(report, 'topic_analyses', [])):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                lines.append(f"		{bg}{t['topic_id']} & {t['items']} & {t['mean_difficulty']} & {t['mean_discrimination']} & {t['status']} \\\\")

            lines += [
                r"		\bottomrule",
                r"	\end{tabular}",
                r"\end{table}",
                "",
            ]

            # Explanation: Topic-Based Outcomes
            lines += [
                "",
                r"\begin{tcolorbox}[width=0.95\textwidth, colback=rowA, colframe=accent, arc=4pt, boxrule=0.6pt, left=8pt, right=8pt]",
                r"	\textbf{\color{accent}What does this mean?}\\[4pt]",
                r"	\textbf{Topic Domains} group questions into clusters of 5 to identify which content areas students struggle with.\\",
                r"	\textbf{Difficulty:} The proportion of students who answered correctly (higher = easier).\\",
                r"	\textbf{Discrimination:} How well the topic separates strong from weak students.\\[4pt]",
                r"	\textbf{Status:} ``Strong'' ($D \ge 0.30$) means the topic reliably distinguishes student ability. ``Needs Review'' means the questions in that domain may need revision.",
                r"\end{tcolorbox}",
            ]

            if getattr(report, "at_risk_students", []):
                at_risk_chunk_size = 25
                at_risk_list = report.at_risk_students
                for chunk_idx in range(0, len(at_risk_list), at_risk_chunk_size):
                    chunk = at_risk_list[chunk_idx : chunk_idx + at_risk_chunk_size]
                    lines += [
                        r"\newpage",
                        r"\section{At-Risk Student Identification}",
                        r"\begin{table}[H]",
                        r"	\centering",
                        f"	\\caption{{Students Scoring Below 60\\% Threshold (Page {chunk_idx // at_risk_chunk_size + 1})}}",
                        r"	\renewcommand{\arraystretch}{1.25}",
                        r"	\begin{tabular}{lccccc}",
                        r"		\toprule",
                        r"		\rowcolor{danger}",
                        r"		\color{white}\textbf{Student ID} & \color{white}\textbf{Version} & \color{white}\textbf{Score} & \color{white}\textbf{Relative Standing \%} & \color{white}\textbf{Z-Score} & \color{white}\textbf{Performance Band} \\ \midrule",
                    ]
                    for i, s in enumerate(chunk):
                        bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                        lines.append(f"		{bg}{s['student_id']} & {s.get('version', '--')} & {s['score']} & {s['percentile']}\\% & {s['z_score']} & \\textcolor{{danger}}{{\\textbf{{{s['band']}}}}} \\\\")

                    lines += [
                        r"		\bottomrule",
                        r"	\end{tabular}",
                        r"\end{table}",
                    ]

                lines += [
                    r"\begin{figure}[H]",
                    r"	\centering",
                    r"	\includegraphics[width=0.9\textwidth]{at_risk_bar.png}",
                    r"	\caption{Stacked bar chart showing the concentration of at-risk students across exam versions}",
                    r"\end{figure}",
                    "",
                ]

            stu_list = getattr(report, 'student_analytics', [])
            chunk_size = 25
            for chunk_idx in range(0, len(stu_list), chunk_size):
                chunk = stu_list[chunk_idx : chunk_idx + chunk_size]
                lines += [
                    r"\newpage",
                    r"\section{Appendix: Complete Student Performance Analytics}",
                    r"\begin{table}[H]",
                    r"	\centering",
                    f"	\\caption{{Performance Overview per Student (Page {chunk_idx // chunk_size + 1})}}",
                    r"	\renewcommand{\arraystretch}{1.25}",
                    r"	\begin{tabular}{lccccc}",
                    r"		\toprule",
                    r"		\rowcolor{primary}",
                    r"		\color{white}\textbf{Student ID} & \color{white}\textbf{Version} & \color{white}\textbf{Score} & \color{white}\textbf{Relative Standing \% (PR)} & \color{white}\textbf{Z-Score} & \color{white}\textbf{Band} \\ \midrule",
                ]
                for i, s in enumerate(chunk):
                    bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                    lines.append(f"		{bg}{s['student_id']} & {s.get('version', '--')} & {s['score']} & {s['percentile']}\\% & {s['z_score']} & {s['band']} \\\\")

                lines += [
                    r"		\bottomrule",
                    r"	\end{tabular}",
                    r"\end{table}",
                ]

            lines += [
                "",
                r"\newpage",
                r"\section{Version Analytics & Equality Evaluation}",
                r"\begin{table}[H]",
                r"	\centering",
                r"	\caption{Equivalence Testing Summary}",
                r"	\renewcommand{\arraystretch}{1.35}",
                r"	\begin{tabular}{lccc}",
                r"		\toprule",
                r"		\rowcolor{primary}",
                r"		\color{white}\textbf{Test} & \color{white}\textbf{Statistic} & \color{white}\textbf{p-value} & \color{white}\textbf{Equivalence Verdict} \\ \midrule",
                f"		\\rowcolor{{rowA}} ANOVA & $F = {round(report.anova_f, 3)}$ & ${round(report.anova_p, 3)}$ & " + (r"\textcolor{danger}{\textbf{Significant diff}}" if report.anova_p < 0.05 else r"\textcolor{success}{\textbf{No sig diff detected}}") + r" \\",
                f"		\\rowcolor{{rowB}} Kruskal-Wallis & $H = {round(report.kruskal_h, 3)}$ & ${round(report.kruskal_p, 3)}$ & " + (r"\textcolor{danger}{\textbf{Significant diff}}" if report.kruskal_p < 0.05 else r"\textcolor{success}{\textbf{No sig diff detected}}") + r" \\",
                r"		\bottomrule",
                r"	\end{tabular}",
                r"\end{table}",
            ]

            # Explanation: ANOVA & Kruskal-Wallis
            lines += [
                "",
                r"\begin{tcolorbox}[width=0.95\textwidth, colback=rowA, colframe=accent, arc=4pt, boxrule=0.6pt, left=8pt, right=8pt]",
                r"	\textbf{\color{accent}What does this mean?}\\[4pt]",
                r"	\textbf{ANOVA} checks whether the average scores across exam versions are statistically different. It answers: ``Did one version produce significantly different results?''\\",
                r"	\textbf{Kruskal-Wallis} is a non-parametric alternative that does not assume scores follow a bell curve.\\[4pt]",
                r"	\textbf{p-value:} The probability that the observed difference happened by pure chance.\\",
                r"	\begin{tabular}{ll}",
                r"		$p \ge 0.05$ & \textcolor{success}{\textbf{No significant difference}} --- versions are fair \\",
                r"		$p < 0.05$ & \textcolor{danger}{\textbf{Significant difference}} --- at least one version is unfairly harder/easier \\",
                r"	\end{tabular}\\[4pt]",
                r"	\textbf{Tukey's HSD} (shown below if applicable) identifies exactly \textit{which} version pairs differ.",
                r"\end{tcolorbox}",
            ]

            if getattr(report, "anova_p", 1.0) < 0.05 and getattr(report, "tukey_hsd_results", []):
                lines += [
                    r"\vspace{0.5cm}",
                    r"\begin{table}[H]",
                    r"	\centering",
                    r"	\caption{Tukey's HSD Post-Hoc Analysis (Significant Pairwise Differences)}",
                    r"	\renewcommand{\arraystretch}{1.3}",
                    r"	\begin{tabular}{lllc}",
                    r"		\toprule",
                    r"		\rowcolor{primary}",
                    r"		\color{white}\textbf{Pairwise Comparison} & \color{white}\textbf{Mean Difference} & \color{white}\textbf{p-value} & \color{white}\textbf{Significance} \\ \midrule",
                ]
                for i, res in enumerate(report.tukey_hsd_results):
                    bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                    lines.append(f"		{bg}{res['pair']} & {res['diff']} & {res['p_value']} & \\textcolor{{danger}}{{\\textbf{{Significant}}}} \\\\")
                lines += [
                    r"		\bottomrule",
                    r"	\end{tabular}",
                    r"\end{table}",
                ]

            if getattr(report, "equated_scores", {}):
                lines += [
                    r"\vspace{0.5cm}",
                    r"\begin{table}[H]",
                    r"	\centering",
                    r"	\caption{Recommended Score Equating Adjustments (Mean Equating)}",
                    r"	\renewcommand{\arraystretch}{1.3}",
                    r"	\begin{tabular}{lccc}",
                    r"		\toprule",
                    r"		\rowcolor{primary}",
                    r"		\color{white}\textbf{Version} & \color{white}\textbf{Raw Mean} & \color{white}\textbf{Target Grand Mean} & \color{white}\textbf{Equating Adjustment} \\ \midrule",
                ]
                for i, (ver, eq) in enumerate(report.equated_scores.items()):
                    bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                    adj_str = f"+{eq['adjustment']}" if eq['adjustment'] > 0 else f"{eq['adjustment']}"
                    lines.append(f"		{bg}Version {ver} & {eq['original_mean']} & {eq['target_mean']} & \\textbf{{{adj_str}}} \\\\")
                lines += [
                    r"		\bottomrule",
                    r"	\end{tabular}",
                    r"\end{table}",
                    "",
                    r"\begin{figure}[H]",
                    r"	\centering",
                    r"	\includegraphics[width=0.9\textwidth]{equating_bar.png}",
                    r"	\caption{Bar chart visualizing the required mean equating adjustments per version}",
                    r"\end{figure}",
                ]

            # Explanation: Score Equating
            lines += [
                "",
                r"\begin{tcolorbox}[width=0.95\textwidth, colback=rowA, colframe=accent, arc=4pt, boxrule=0.6pt, left=8pt, right=8pt]",
                r"	\textbf{\color{accent}What does this mean?}\\[4pt]",
                r"	\textbf{Score Equating} compensates for unfair difficulty differences between exam versions. If Version B was harder than Version A, students who took B get a small bonus added to their raw score so the comparison is fair.\\[4pt]",
                r"	\textbf{How to use it:} Add the ``Equating Adjustment'' value to each student's raw score. Positive = version was harder (bonus). Negative = version was easier (penalty).",
                r"\end{tcolorbox}",
            ]

            # Explanation: Student Analytics
            lines += [
                "",
                r"\begin{tcolorbox}[width=0.95\textwidth, colback=rowA, colframe=accent, arc=4pt, boxrule=0.6pt, left=8pt, right=8pt]",
                r"	\textbf{\color{accent}Student Analytics Glossary}\\[4pt]",
                r"	\textbf{Percentile Rank (PR):} The percentage of students who scored at or below this student. PR=80\% means the student scored better than 80\% of the class.\\",
                r"	\textbf{Z-Score:} How many standard deviations a student's score is from the class mean. $Z=0$ means average, $Z>1$ is above average, $Z<-1$ is below average.\\",
                r"	\textbf{Performance Bands:}\\",
                r"	\begin{tabular}{ll}",
                r"		\textbf{Advanced} & $\ge 85\%$ --- Mastery level \\",
                r"		\textbf{Proficient} & $70\% - 84\%$ --- Strong understanding \\",
                r"		\textbf{Basic} & $50\% - 69\%$ --- Developing understanding \\",
                r"		\textbf{Below Basic} & $< 50\%$ --- At-risk; needs intervention \\",
                r"	\end{tabular}",
                r"\end{tcolorbox}",
            ]

            lines += [
                "",
                r"\begin{summarybox}",
                r"	\begin{itemize}[leftmargin=*, itemsep=4pt]",
                f"		\\item \\textbf{{Total Students:}} {report.total_students}",
                f"		\\item \\textbf{{Overall Mean:}} {report.overall_mean} / {ms} \\quad ({pct_mean}\\%)",
                f"		\\item \\textbf{{Overall Median:}} {report.overall_median}",
                f"		\\item \\textbf{{Cronbach's Alpha:}} {getattr(report, 'cronbach_alpha', 0.0)}",
                f"		\\item \\textbf{{ANOVA p-value:}} {report.anova_p}",
                r"	\end{itemize}",
                r"\end{summarybox}",
                "",
                r"\vfill",
                r"\begin{center}",
                r"	\textcolor{medgray}{\small\rule{0.4\textwidth}{0.4pt} \\[4pt] End of Detailed Evaluation Report}",
                r"\end{center}",
                "",
                r"\end{document}",
            ]

            tex_path = os.path.join(tmp, "report.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            pdflatex = TemplateCompiler.find_pdflatex()
            if pdflatex:
                import subprocess
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
            shutil.rmtree(tmp, ignore_errors=True)
