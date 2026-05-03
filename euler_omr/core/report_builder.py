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
            ax.hist(report.overall_scores, bins=bins, color="#117A65",
                    edgecolor="#1B4F72", alpha=0.8, rwidth=0.85)
            ax.set_xlabel("Score", fontsize=11, fontweight="bold", color="#1B4F72")
            ax.set_ylabel("Number of Students", fontsize=11, fontweight="bold", color="#1B4F72")
            ax.set_title("Overall Grade Distribution", fontsize=13, fontweight="bold", color="#1B4F72")
            ax.set_xticks(range(0, report.max_score + 1))
            ax.grid(axis='y', linestyle='--', alpha=0.5)
            hist_path = os.path.join(tmp, "histogram.png")
            fig.savefig(hist_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

            # ── Chart 2: Version mean comparison bar ──
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

            # ── Chart 3: Individual version histograms ──
            version_chart_paths = []
            if report.version_stats:
                for vs in report.version_stats:
                    if not vs.scores:
                        continue
                    fig, ax = plt.subplots(figsize=(6, 3))
                    bins = range(0, report.max_score + 2)
                    ax.hist(vs.scores, bins=bins, color="#1B4F72", edgecolor="#117A65", alpha=0.75, rwidth=0.85)
                    ax.set_xlabel("Score", fontsize=10, fontweight="bold", color="#1B4F72")
                    ax.set_ylabel("Frequency", fontsize=10, fontweight="bold", color="#1B4F72")
                    ax.set_title(f"Score Distribution - Version {vs.version}", fontsize=11, fontweight="bold", color="#1B4F72")
                    ax.set_xticks(range(0, report.max_score + 1))
                    ax.grid(axis='y', linestyle='--', alpha=0.4)
                    chart_name = f"dist_version_{vs.version}.png"
                    chart_path = os.path.join(tmp, chart_name)
                    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
                    plt.close(fig)
                    version_chart_paths.append((vs.version, chart_name))

            _log("Charts generated", "INFO")

            # ═══════════════════════════════════════════════════════════
            #  Build LaTeX report using exact reporttemplate.tex style
            # ═══════════════════════════════════════════════════════════
            ms = report.max_score
            pct_mean = round(report.overall_mean / ms * 100, 1) if ms > 0 else 0
            modes = report.overall_mode

            lines = [
                r"\documentclass[12pt, a4paper]{article}",
                "",
                r"% ─── Packages ────────────────────────────────────────────────────────────────",
                r"\usepackage[margin=2.5cm]{geometry}",
                r"\usepackage{booktabs}",
                r"\usepackage{array}",
                r"\usepackage{xcolor}",
                r"\usepackage{colortbl}",
                r"\usepackage{graphicx}",
                r"\usepackage{pgfplots}",
                r"\usepackage{pgfplotstable}",
                r"\usepackage{tikz}",
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
                r"\pgfplotsset{compat=1.18}",
                "",
                r"% ─── Colors ──────────────────────────────────────────────────────────────────",
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
                r"% ─── Page Style ──────────────────────────────────────────────────────────────",
                r"\pagestyle{fancy}",
                r"\fancyhf{}",
                r"\fancyhead[L]{\small\color{primary}\textbf{Euler OMR} — Statistical Analysis Report}",
                r"\fancyhead[R]{\small\color{medgray}Generated by Euler OMR Grading System}",
                r"\fancyfoot[C]{\small\color{medgray}\thepage}",
                r"\renewcommand{\headrulewidth}{0.4pt}",
                r"\renewcommand{\footrulewidth}{0pt}",
                "",
                r"% ─── Section Styling ─────────────────────────────────────────────────────────",
                r"\titleformat{\section}",
                r"{\large\bfseries\color{primary}}",
                r"{\thesection.}{0.5em}{}[\titrule]",
                "",
                r"\titleformat{\subsection}",
                r"{\normalsize\bfseries\color{accent}}",
                r"{\thesubsection}{0.5em}{}",
                "",
                r"% ─── Hyperlinks ──────────────────────────────────────────────────────────────",
                r"\hypersetup{",
                r"	colorlinks=true,",
                r"	linkcolor=primary,",
                r"	urlcolor=accent",
                r"}",
                "",
                r"% ─── Summary Box ─────────────────────────────────────────────────────────────",
                r"\tcbuselibrary{skins, breakable}",
                r"\newtcolorbox{summarybox}{",
                r"	enhanced,",
                r"	colback=lightgray,",
                r"	colframe=primary,",
                r"	boxrule=1pt,",
                r"	arc=4pt,",
                r"	left=8pt, right=8pt, top=6pt, bottom=6pt,",
                r"	title={\bfseries\color{white} Quick Summary},",
                r"	fonttitle=\bfseries,",
                r"	coltitle=white,",
                r"	attach boxed title to top left={yshift=-2mm, xshift=4mm},",
                r"	boxed title style={colback=primary, arc=3pt}",
                r"}",
                "",
                r"\newtcolorbox{statbox}[1]{",
                r"	enhanced,",
                r"	colback=#1!10,",
                r"	colframe=#1,",
                r"	boxrule=0.8pt,",
                r"	arc=3pt,",
                r"	left=6pt, right=6pt, top=4pt, bottom=4pt",
                r"}",
                "",
                r"% ─── Document ─────────────────────────────────────────────────────────────────",
                r"\begin{document}",
                r"	",
                r"	% ── Title Page ────────────────────────────────────────────────────────────────",
                r"	\begin{titlepage}",
                r"		\centering",
                r"		\vspace*{3cm}",
                r"		{\Huge\bfseries\color{primary} Euler OMR\par}",
                r"		\vspace{0.4cm}",
                r"		{\LARGE\color{accent} Statistical Analysis Report\par}",
                r"		\vspace{1cm}",
                r"		\textcolor{medgray}{\rule{0.6\textwidth}{0.6pt}}",
                r"		\vspace{0.8cm}",
                r"		",
                r"		\begin{tcolorbox}[",
                r"			width=0.65\textwidth,",
                r"			colback=lightgray,",
                r"			colframe=medgray,",
                r"			arc=4pt,",
                r"			boxrule=0.6pt",
                r"			]",
                r"			\centering",
                r"			\begin{tabular}{rl}",
                f"				\\textbf{{Total Students:}} & {report.total_students} \\\\[4pt]",
                f"				\\textbf{{Overall Mean:}}   & {report.overall_mean} / {ms} \\quad ({pct_mean}\\%) \\\\[4pt]",
                f"				\\textbf{{Median:}}         & {report.overall_median} \\\\[4pt]",
                f"				\\textbf{{Mode:}}           & {modes} \\\\[4pt]",
                f"				\\textbf{{Std Dev:}}        & {report.overall_stddev} \\\\[4pt]",
                f"				\\textbf{{Score Range:}}    & {report.overall_min} -- {report.overall_max} \\\\",
                r"			\end{tabular}",
                r"		\end{tcolorbox}",
                r"		",
                r"		\vfill",
                r"		{\small\color{medgray} Generated by Euler OMR Grading System}",
                r"	\end{titlepage}",
                "",
                r"	% ── Section 1 ────────────────────────────────────────────────────────────────",
                r"	\section{Overall Statistics (All Students, All Versions)}",
                r"	\subsection{Descriptive Statistics}",
                r"	",
                r"	\begin{center}",
                r"		\begin{tcolorbox}[",
                r"			width=0.7\textwidth,",
                r"			colback=rowA,",
                r"			colframe=primary,",
                r"			arc=4pt,",
                r"			boxrule=0.8pt",
                r"			]",
                r"			\centering",
                r"			\renewcommand{\arraystretch}{1.4}",
                r"			\begin{tabular}{>{\bfseries}l r}",
                r"				\toprule",
                r"				\multicolumn{1}{c}{\color{primary}\textbf{Statistic}} &",
                r"				\multicolumn{1}{c}{\color{primary}\textbf{Value}} \\",
                r"				\midrule",
                f"				Total Students  & {report.total_students} \\\\",
                f"				Mean            & {report.overall_mean} / {ms} \\quad ({pct_mean}\\%) \\\\",
                f"				Median          & {report.overall_median} \\\\",
                f"				Mode            & {modes} \\\\",
                f"				Std Deviation   & {report.overall_stddev} \\\\",
                f"				Range           & {report.overall_min} -- {report.overall_max} \\\\",
                r"				\bottomrule",
                r"			\end{tabular}",
                r"		\end{tcolorbox}",
                r"	\end{center}",
                r"	",
                r"	\subsection{Score Distribution}",
                r"	\begin{table}[H]",
                r"		\centering",
                r"		\caption{Score frequency across all students and versions}",
                r"		\renewcommand{\arraystretch}{1.35}",
                r"		\begin{tabular}{>{\centering\arraybackslash}m{2cm}>{\centering\arraybackslash}m{3cm}>{\centering\arraybackslash}m{3cm}}",
                r"			\toprule",
                r"			\rowcolor{primary}",
                r"			\color{white}\textbf{Score} & \color{white}\textbf{Students} & \color{white}\textbf{Percentage} \\ \midrule",
            ]
            for i, sd in enumerate(report.score_distribution):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                lines.append(f"			{bg}{sd.score} / {ms} & {sd.count} & {sd.percentage}\\% \\\\")
            lines += [
                r"			\bottomrule",
                r"		\end{tabular}",
                r"	\end{table}",
                "",
                r"	\begin{figure}[H]",
                r"		\centering",
                r"		\includegraphics[width=0.85\textwidth]{histogram.png}",
                r"		\caption{Overall score distribution chart}",
                r"	\end{figure}",
                "",
                r"	% ── Section 2 ────────────────────────────────────────────────────────────────",
                r"	\section{Per-Version Statistics}",
                r"	\begin{table}[H]",
                r"		\centering",
                r"		\caption{Descriptive statistics broken down by exam version}",
                r"		\renewcommand{\arraystretch}{1.35}",
                r"		\begin{tabular}{cccccccc}",
                r"			\toprule",
                r"			\rowcolor{primary}",
                r"			\color{white}\textbf{Version} &",
                r"			\color{white}\textbf{N} &",
                r"			\color{white}\textbf{Mean} &",
                r"			\color{white}\textbf{\%} &",
                r"			\color{white}\textbf{Median} &",
                r"			\color{white}\textbf{Std Dev} &",
                r"			\color{white}\textbf{Min} &",
                r"			\color{white}\textbf{Max} \\ \midrule",
            ]
            for i, vs in enumerate(report.version_stats):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                pct = round(vs.mean / ms * 100, 1) if ms > 0 else 0
                lines.append(f"			{bg}{vs.version} & {vs.count} & {vs.mean} & {pct}\\% & {vs.median} & {vs.stddev} & {vs.min_score} & {vs.max_score_val} \\\\")
            lines += [
                r"			\bottomrule",
                r"		\end{tabular}",
                r"	\end{table}",
                "",
                r"	\begin{figure}[H]",
                r"		\centering",
                r"		\includegraphics[width=0.85\textwidth]{version_bar.png}",
                r"		\caption{Mean score comparison across exam versions}",
                r"	\end{figure}",
                "",
                r"	% ── Section 2.1 ──────────────────────────────────────────────────────────────",
                r"	\newpage",
                r"	\section{Per-Version Detailed Score Distributions}",
                "",
            ]
            for ver, chart_name in version_chart_paths:
                lines += [
                    r"	\begin{figure}[H]",
                    r"		\centering",
                    f"		\\includegraphics[width=0.72\\textwidth]{{{chart_name}}}",
                    f"		\\caption{{Detailed Score Distribution for Version {ver}}}",
                    r"	\end{figure}",
                    "",
                ]
            lines += [
                r"	% ── Section 3 ────────────────────────────────────────────────────────────────",
                r"	\section{Answer Choice Analysis by Question}",
                r"	\begin{table}[H]",
                r"		\centering",
                r"		\caption{Answer choice distribution with Answer Keys}",
                r"		\renewcommand{\arraystretch}{1.35}",
                r"		\begin{tabular}{ccccccc}",
                r"			\toprule",
                r"			\rowcolor{primary}",
                r"			\color{white}\textbf{Q} & \color{white}\textbf{Answer Key} & \color{white}\textbf{A} & \color{white}\textbf{B} & \color{white}\textbf{C} & \color{white}\textbf{D} & \color{white}\textbf{Blank} \\ \midrule",
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
                lines.append(f"			{bg}Q{i+1} & {key_str} & " + " & ".join(opts) + f" & {blank_str} \\\\")
            lines += [
                r"			\bottomrule",
                r"		\end{tabular}",
                r"	\end{table}",
                "",
                r"	% ── Psychometrics Section ───────────────────────────────────────────────────",
                r"	\newpage",
                r"	\section{Item Psychometrics: Difficulty \& Discrimination Index}",
                r"	\begin{table}[H]",
                r"		\centering",
                r"		\caption{Item performance metrics across all students and versions}",
                r"		\renewcommand{\arraystretch}{1.35}",
                r"		\begin{tabular}{ccccc}",
                r"			\toprule",
                r"			\rowcolor{primary}",
                r"			\color{white}\textbf{Q} & \color{white}\textbf{Key} & \color{white}\textbf{p-value (Difficulty)} & \color{white}\textbf{Discrimination Index (D)} & \color{white}\textbf{Failure Rate} \\ \midrule",
            ]
            for i, psy in enumerate(report.item_psychometrics):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                key_str = ", ".join(psy.correct_keys) if psy.correct_keys else "--"
                lines.append(f"			{bg}Q{psy.question_idx+1} & {key_str} & {psy.p_value} & {psy.discrimination_index} & {psy.failure_rate}\\% \\\\")
            lines += [
                r"			\bottomrule",
                r"		\end{tabular}",
                r"	\end{table}",
                "",
                r"	\begin{tcolorbox}[colback=lightgray, colframe=primary, arc=3pt, boxrule=0.8pt]",
                r"		\textbf{Psychometrics Interpretation:}\\",
                r"		\textbf{p-value (Difficulty):} Proportion of students answering correctly. Values $>0.75$ are Easy, $0.30 - 0.75$ are Moderate, $<0.30$ are Hard.\\",
                r"		\textbf{Discrimination Index (D):} Difference in correct rate between the top 27\% and bottom 27\% of students. Values $>0.30$ indicate Excellent discrimination, $0.10 - 0.30$ Fair, and $<0.10$ Poor.",
                r"	\end{tcolorbox}",
            ]
            has_low_d = any(psy.discrimination_index < 0.10 for psy in report.item_psychometrics)
            if has_low_d:
                lines += [
                    r"	\begin{tcolorbox}[colback=danger!5, colframe=danger, arc=3pt, boxrule=0.8pt]",
                    r"		\textbf{Note --- Low Discrimination Index Detected}\\",
                    r"		One or more items in this assessment show a Discrimination Index (D) below the acceptable threshold (D $<$ 0.10), which is rated as Poor. This indicates that these questions do not effectively differentiate between high-performing and low-performing students, and may not be contributing meaningfully to the overall assessment quality.\\",
                    r"		\textbf{Recommendation:} The flagged items should be reviewed by the exam committee to assess their content validity and determine whether revision or removal is appropriate in future versions of the test.",
                    r"	\end{tcolorbox}",
                    "",
                ]
            lines += [
                r"	\subsection{Cross-Question Performance Comparison}",
                r"	\begin{table}[H]",
                r"		\centering",
                r"		\caption{Items ranked from highest to lowest failure rate}",
                r"		\renewcommand{\arraystretch}{1.35}",
                r"		\begin{tabular}{cccc}",
                r"			\toprule",
                r"			\rowcolor{primary}",
                r"			\color{white}\textbf{Rank} & \color{white}\textbf{Item} & \color{white}\textbf{Failure Rate} & \color{white}\textbf{p-value (Difficulty)} \\ \midrule",
            ]
            sorted_psy = sorted(report.item_psychometrics, key=lambda p: p.failure_rate, reverse=True)
            for i, psy in enumerate(sorted_psy):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                lines.append(f"			{bg}{i+1} & Q{psy.question_idx+1} & {psy.failure_rate}\\% & {psy.p_value} \\\\")
            lines += [
                r"			\bottomrule",
                r"		\end{tabular}",
                r"	\end{table}",
                "",
                r"	% ── Section 4 ────────────────────────────────────────────────────────────────",
                r"	\newpage",
                r"	\section{Answer Choice Analysis by Version}",
                "",
            ]
            for qcv in report.question_choices_by_version:
                q_idx = qcv.question_idx
                lines.append(f"	\\subsection{{Question {q_idx + 1}}}")
                lines.append(r"	\begin{table}[H]")
                lines.append(r"		\centering")
                lines.append(r"		\renewcommand{\arraystretch}{1.3}")
                lines.append(r"		\begin{tabular}{l ccccc m{5.5cm}}")
                lines.append(r"			\toprule")
                lines.append(r"			\rowcolor{primary}")
                lines.append(r"			\color{white}\textbf{Version} & \color{white}\textbf{A} & \color{white}\textbf{B} & \color{white}\textbf{C} & \color{white}\textbf{D} & \color{white}\textbf{Pattern} & \color{white}\textbf{Insight} \\ \midrule")
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
                            status = "Not OK (Wrong Conc)"
                            insight = f"Option {max_inc_k} attracted more students than correct answer."
                        elif correct_pct <= 35.0 and pct_range <= 20.0:
                            status = "Not OK (Scattered)"
                            insight = "Choices are spread evenly; students were guessing."
                        elif correct_pct - max_inc_pct <= 15.0:
                            status = "Not OK (Rival Dist)"
                            insight = f"Option {max_inc_k} is competing closely with correct answer."
                        else:
                            status = "OK"
                            insight = "--"
                    else:
                        status = "OK"
                        insight = "--"
                    lines.append(f"			{bg}{ver} & {vals} & {status} & {insight} \\\\")
                lines.append(r"			\bottomrule")
                lines.append(r"		\end{tabular}")
                lines.append(r"	\end{table}")
                lines.append("")
            lines += [
                r"	% ── Section 5 ────────────────────────────────────────────────────────────────",
                r"	\section{Version Comparison — Difficulty Ranking}",
                r"	\begin{table}[H]",
                r"		\centering",
                r"		\caption{Versions ranked from easiest to hardest by mean score}",
                r"		\renewcommand{\arraystretch}{1.4}",
                r"		\begin{tabular}{cccc}",
                r"			\toprule",
                r"			\rowcolor{primary}",
                r"			\color{white}\textbf{Rank} & \color{white}\textbf{Version} & \color{white}\textbf{Mean} & \color{white}\textbf{Difficulty} \\ \midrule",
            ]
            for i, vr in enumerate(report.version_ranking):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                lines.append(f"			{bg}{i+1} & {vr.version} & {vr.mean} & {vr.difficulty_label} \\\\")
            lines += [
                r"			\bottomrule",
                r"		\end{tabular}",
                r"	\end{table}",
                "",
                r"	\subsection{Statistical Equivalence Tests}",
                r"	\begin{table}[H]",
                r"		\centering",
                r"		\caption{ANOVA and Kruskal-Wallis tests for version equivalence}",
                r"		\renewcommand{\arraystretch}{1.4}",
                r"		\begin{tabular}{lccc}",
                r"			\toprule",
                r"			\rowcolor{primary}",
                r"			\color{white}\textbf{Test} & \color{white}\textbf{Statistic} & \color{white}\textbf{p-value} & \color{white}\textbf{Result} \\ \midrule",
                f"			\\rowcolor{{rowA}} ANOVA (parametric)        & $F = {report.anova_f}$ & ${report.anova_p}$ & " + (r"\textcolor{danger}{\textbf{Significant diff}}" if report.anova_p < 0.05 else r"\textcolor{success}{\textbf{No sig diff}}") + r" \\",
                f"			\\rowcolor{{rowB}} Kruskal-Wallis (non-param) & $H = {report.kruskal_h}$ & ${report.kruskal_p}$ & " + (r"\textcolor{danger}{\textbf{Significant diff}}" if report.kruskal_p < 0.05 else r"\textcolor{success}{\textbf{No sig diff}}") + r" \\",
                r"			\bottomrule",
                r"		\end{tabular}",
                r"	\end{table}",
                "",
                r"	\begin{tcolorbox}[colback=danger!5, colframe=danger, arc=3pt, boxrule=0.8pt]",
                r"		\textbf{Interpretation:} Both tests confirm whether versions are \textbf{statistically",
                f"		equivalent}} ($p \\ge 0.05$ or $p < 0.05$). Currently, p-value = {report.anova_p}.",
                r"	\end{tcolorbox}",
                "",
                r"	\subsection{Outlier Versions (Z-Score Analysis)}",
                r"	\begin{table}[H]",
                r"		\centering",
                r"		\caption{Z-scores relative to grand mean and std dev}",
                r"		\renewcommand{\arraystretch}{1.4}",
                r"		\begin{tabular}{cccc}",
                r"			\toprule",
                r"			\rowcolor{primary}",
                r"			\color{white}\textbf{Version} & \color{white}\textbf{Mean} & \color{white}\textbf{Z-Score} & \color{white}\textbf{Note} \\ \midrule",
            ]
            for i, vo in enumerate(report.version_outliers):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                sign = "+" if vo.z_score >= 0 else ""
                note = vo.label.replace("←", r"$\leftarrow$")
                lines.append(f"			{bg}{vo.version} & {vo.mean} & {sign}{vo.z_score} & {note} \\\\")
            lines += [
                r"			\bottomrule",
                r"		\end{tabular}",
                r"	\end{table}",
                "",
                r"	% ── Section 6 ────────────────────────────────────────────────────────────────",
                r"	\section{Quick Summary}",
                r"	\begin{summarybox}",
                r"		\begin{itemize}[leftmargin=*, itemsep=4pt]",
                f"			\\item \\textbf{{Total Students:}} {report.total_students}",
                f"			\\item \\textbf{{Overall Mean:}} {report.overall_mean} / {ms} \\quad ({pct_mean}\\%)",
                f"			\\item \\textbf{{Overall Median:}} {report.overall_median}",
                f"			\\item \\textbf{{Overall Mode:}} {modes}",
                f"			\\item \\textbf{{Overall Std Dev:}} {report.overall_stddev}",
            ]
            if report.version_ranking:
                easiest = report.version_ranking[0]
                hardest = report.version_ranking[-1]
                spread = round(easiest.mean - hardest.mean, 3)
                lines.append(f"			\\item \\textbf{{Easiest Version:}} {easiest.version} \\quad (mean = {easiest.mean})")
                lines.append(f"			\\item \\textbf{{Hardest Version:}} {hardest.version} \\quad (mean = {hardest.mean})")
                lines.append(f"			\\item \\textbf{{Spread in Means:}} {spread} points across versions")
            lines += [
                f"			\\item \\textbf{{ANOVA p-value:}} {report.anova_p} \\quad " + (r"\textcolor{danger}{$\rightarrow$ Not equivalent}" if report.anova_p < 0.05 else r"\textcolor{success}{$\rightarrow$ Equivalent}"),
                r"		\end{itemize}",
                r"	\end{summarybox}",
                "",
                r"	\vfill",
                r"	\begin{center}",
                r"		\textcolor{medgray}{\small\rule{0.4\textwidth}{0.4pt} \\[4pt]",
                r"			End of Report — Generated by Euler OMR Grading System}",
                r"	\end{center}",
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
            pass
