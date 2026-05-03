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

            # Generate Chart 3: Score distribution per version
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
                "",
                r"% Title Page",
                r"\begin{titlepage}",
                r"	\centering",
                r"	\vspace*{2cm}",
                r"	{\Huge\bfseries\color{primary} Euler OMR\par}",
                r"	\vspace{0.4cm}",
                r"	{\LARGE\color{accent} Statistical & Psychometric Report\par}",
                r"	\vspace{1cm}",
                r"	\textcolor{medgray}{\rule{0.6\textwidth}{0.6pt}}",
                r"	\vspace{0.8cm}",
                r"	",
                r"	\begin{tcolorbox}[width=0.7\textwidth, colback=lightgray, colframe=medgray, arc=4pt, boxrule=0.6pt]",
                r"		\centering",
                r"		\begin{tabular}{rl}",
                f"			\\textbf{{Total Students:}} & {report.total_students} \\\\",
                f"			\\textbf{{Overall Mean:}}   & {report.overall_mean} / {ms} \\quad ({pct_mean}\\%) \\\\",
                f"			\\textbf{{Median Score:}}   & {report.overall_median} \\\\",
                f"			\\textbf{{Std Deviation:}}  & {report.overall_stddev} \\\\",
                f"			\\textbf{{Score Range:}}    & {report.overall_min} -- {report.overall_max} \\\\",
                r"		\end{tabular}",
                r"	\end{tcolorbox}",
                r"	\vfill",
                r"	{\small\color{medgray} Generated by Euler OMR Evaluation System}",
                r"\end{titlepage}",
                "",
                r"\section{Reliability Analysis}",
                r"\begin{table}[H]",
                r"	\centering",
                r"	\caption{Reliability Coefficients Summary}",
                r"	\renewcommand{\arraystretch}{1.3}",
                r"	\begin{tabular}{lc}",
                r"		\toprule",
                r"		\rowcolor{primary}",
                r"		\color{white}\textbf{Metric} & \color{white}\textbf{Calculated Value} \\ \midrule",
                f"		\\rowcolor{{rowA}} Cronbach's Alpha (KR-20) & {getattr(report, 'cronbach_alpha', 0.0)} \\\\",
                f"		\\rowcolor{{rowB}} Split-Half Reliability & {getattr(report, 'split_half_reliability', 0.0)} \\\\",
                r"		\bottomrule",
                r"	\end{tabular}",
                r"\end{table}",
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
                r"\newpage",
                r"\section{Individual Version Score Histograms}",
            ]

            for ver, chart_name in version_chart_paths:
                lines += [
                    r"\begin{figure}[H]",
                    r"	\centering",
                    f"	\\includegraphics[width=0.72\\textwidth]{{{chart_name}}}",
                    f"	\\caption{{Score Distribution for Version {ver}}}",
                    r"\end{figure}",
                    "",
                ]

            lines += [
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
                r"	\begin{tabular}{ccccccc}",
                r"		\toprule",
                r"		\rowcolor{primary}",
                r"		\color{white}\textbf{Q} & \color{white}\textbf{Key} & \color{white}\textbf{p-value} & \color{white}\textbf{Discrimination} & \color{white}\textbf{Point-Biserial} & \color{white}\textbf{Distractor Eff.} & \color{white}\textbf{Status} \\ \midrule",
            ]

            for i, psy in enumerate(report.item_psychometrics):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                key_str = ", ".join(psy.correct_keys) if psy.correct_keys else "--"
                lines.append(f"		{bg}Q{psy.question_idx+1} & {key_str} & {psy.p_value} & {psy.discrimination_index} & {psy.point_biserial} & {psy.distractor_efficiency}\\% & {psy.quality_class} \\\\")

            lines += [
                r"		\bottomrule",
                r"	\end{tabular}",
                r"\end{table}",
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
                            status = "Not OK"
                            insight = f"Option {max_inc_k} pulled more students than correct key."
                        elif correct_pct <= 35.0 and pct_range <= 20.0:
                            status = "Not OK"
                            insight = "Scattered options."
                        elif correct_pct - max_inc_pct <= 15.0:
                            status = "Not OK"
                            insight = f"Option {max_inc_k} closely competing."
                        else:
                            status = "OK"
                            insight = "--"
                    else:
                        status = "OK"
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
                r"\newpage",
                r"\section{Student-Level Master Performance Breakdown}",
                r"\begin{table}[H]",
                r"	\centering",
                r"	\caption{Performance Overview per Student}",
                r"	\renewcommand{\arraystretch}{1.3}",
                r"	\begin{tabular}{lcccc}",
                r"		\toprule",
                r"		\rowcolor{primary}",
                r"		\color{white}\textbf{Student ID} & \color{white}\textbf{Score} & \color{white}\textbf{Percentile} & \color{white}\textbf{Z-Score} & \color{white}\textbf{Band} \\ \midrule",
            ]

            stu_list = getattr(report, 'student_analytics', [])
            for i, s in enumerate(stu_list):
                bg = r"\rowcolor{rowA} " if i % 2 == 0 else r"\rowcolor{rowB} "
                lines.append(f"		{bg}{s['student_id']} & {s['score']} & {s['percentile']}\\% & {s['z_score']} & {s['band']} \\\\")

            lines += [
                r"		\bottomrule",
                r"	\end{tabular}",
                r"\end{table}",
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
