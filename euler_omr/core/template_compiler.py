"""LaTeX template builder; pdflatex/TinyTeX detection and invocation; progress callbacks."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

import structlog

from euler_omr.models.template_model import TemplateConfig

logger = structlog.get_logger(__name__)

# The bundled LaTeX maximum template — embedded as a string constant.
# This is the MAXIMUM configuration (14 ID digits, 26 versions, 99 questions, 8 options).
# The compiler substitutes only the \\newcommand values at the top.
LATEX_TEMPLATE = r"""\documentclass[a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=2cm, top=1.5cm]{geometry}
\usepackage{tikz}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{array}

% --- User Settings ----------------------------------------------------------
\newcommand{\InstitutionName}{__INSTITUTION_NAME__}
\newcommand{\IDDigits}{__ID_DIGITS__}        % Number of ID digits
\newcommand{\NumQuestions}{__NUM_QUESTIONS__}   % Total number of questions
\newcommand{\NumOptions}{__NUM_OPTIONS__}      % Options per question  (max 8:  A-H)
\newcommand{\NumVersions}{__NUM_VERSIONS__}    % Exam versions         (max 26: A-Z)

% --- Lengths (change once, applies everywhere) -------------------------------
\newcommand{\BubbleRcm}{0.22}     % bubble radius              (cm)
\newcommand{\BubbleStepCm}{0.6}  % horizontal bubble-to-bubble (cm)
\newcommand{\RowStepCm}{0.5}     % vertical row-to-row spacing (cm)
\newlength{\BubbleR}    \setlength{\BubbleR}{\BubbleRcm cm}
\newlength{\BubbleStep} \setlength{\BubbleStep}{\BubbleStepCm cm}
\newlength{\RowStep}    \setlength{\RowStep}{\RowStepCm cm}

% --- Colors -----------------------------------------------------------------
\colorlet{OMRColor}{magenta!40}   % drop-out color for scanner
\colorlet{MarkColor}{black}       % corner / timing mark color

% ----------------------------------------------------------------------------
\begin{document}
	\pagestyle{empty}
	
	% --- Corner & Timing Marks --------------------------------------------------
	\begin{tikzpicture}[remember picture, overlay]
		% Four corner marks: top-left is wider (2.0cm) to detect 180-degree rotation
		% Bottom markers adjusted to y=2.0 to maintain a safe margin from the page edge
		\foreach \anchor/\dx/\dy/\w in {
			north west/ 1.2/-1.2/2.0, % Top-Left (Wider for orientation)
			north east/-2.0/-1.2/0.8, % Top-Right
			south west/ 1.2/ 2.0/0.8, % Bottom-Left 
			south east/-2.0/ 2.0/0.8  % Bottom-Right 
		}{
			\fill[MarkColor]
			(current page.\anchor) ++(\dx cm, \dy cm)
			rectangle ++(\w cm, -0.8cm);
		}
		
		% Timing marks (left and right margins)
		\foreach \y in {0, \RowStepCm, ..., 22}{
			% Skip the first mark (y=0) so it doesn't merge with the bottom corner marks
			\ifdim \y pt > 0.1pt 
			% Left side
			\fill[MarkColor]
			(current page.south west) ++(1.2cm, 2cm + \y cm)
			rectangle ++(0.4cm, 0.2cm);
			% Right side (mirror)
			\fill[MarkColor]
			(current page.south east) ++(-1.6cm, 2cm + \y cm)
			rectangle ++(0.4cm, 0.2cm);
			\fi
		}
	\end{tikzpicture}
	
	% --- Top Row: Left = Info  |  Right = ID Bubbles ----------------------------
	\noindent
	%
	% -- Left block: logo + institution name + written fields (48% of width) ------
	\begin{minipage}[t]{0.48\textwidth}
		\vspace{0pt}
		\begin{center}
			\includegraphics[width=4cm, height=1.2cm, keepaspectratio]{assets/logo}\\[3mm]
			{\large\bfseries \InstitutionName}\\[1mm]
			\rule{0.9\linewidth}{0.4pt}
		\end{center}
		\vspace{4mm}
		
		\renewcommand{\arraystretch}{1.8}
		\begin{tabular}{|p{0.22\linewidth}p{0.68\linewidth}|}
			\hline
			\textbf{Name:}       & \\[3mm] \hline
			\textbf{Course:}     & \\[3mm] \hline
			\textbf{Date:}       & \\[3mm] \hline
		\end{tabular}
	\end{minipage}%
	\hfill%
	% -- Right block: Student ID bubbles (48% of width) ---------------------------
	\begin{minipage}[t]{0.48\textwidth}
		\vspace{0pt}
		\raggedleft
		\textbf{Student ID:}\par\vspace{3mm}
		% Changed y to -\RowStep to match the vertical spacing of the rest of the sheet
		\begin{tikzpicture}[x=\BubbleStep, y=-\RowStep]
			\foreach \col in {1,...,\IDDigits}{
				\draw[OMRColor,thick] (\col - 0.35, 0.4) rectangle (\col + 0.35, -0.4);
			}
		\end{tikzpicture}
		\par\vspace{1mm}
		\begin{tikzpicture}[x=\BubbleStep, y=-\RowStep]
			\foreach \col in {1,...,\IDDigits}{
				\foreach \row in {0,...,9}{
					\draw[OMRColor, thick] (\col, \row) circle (\BubbleR)
					node[font=\tiny\bfseries, text=OMRColor] {\row};
				}
			}
		\end{tikzpicture}
	\end{minipage}
	
	% --- Bottom Row: Exam Version (full width) -----------------------------------
	\vspace{3mm}
	\noindent
	\textbf{Exam Version:}\par\vspace{3mm}
	\noindent
	\begin{tikzpicture}[x=\BubbleStep, y=0cm]
		\foreach \v [count=\i] in {A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z}{
			\ifnum\i>\NumVersions\else
			\draw[OMRColor, thick] (\i, 0) circle (\BubbleR)
			node[font=\tiny\bfseries, text=OMRColor] {\v};
			\fi
		}
	\end{tikzpicture}
	
	\noindent\rule{\linewidth}{0.6pt}
	\vspace{-2mm}
	
	% --- Answers Section (3 columns) --------------------------------------------
	\noindent\hspace*{-0.2cm}%
	\begin{tikzpicture}[x=\BubbleStep, y=-\RowStep]
		\pgfmathtruncatemacro{\RowsPerCol}{ceil(\NumQuestions/3)}
		\pgfmathsetmacro{\ColWidth}{\the\linewidth / \the\BubbleStep / 3}
		
		\foreach \q in {1,...,\NumQuestions}{
			\pgfmathtruncatemacro{\colIdx}{(\q-1)/\RowsPerCol}
			\pgfmathtruncatemacro{\rowIdx}{mod(\q-1,\RowsPerCol)}
			\pgfmathsetmacro{\xOff}{\colIdx * \ColWidth}
			
			\node[anchor=east, font=\scriptsize\bfseries] at (\xOff + 1.2, \rowIdx) {\q};
			
			\foreach \opt [count=\i] in {A,B,C,D,E,F,G,H}{
				\ifnum\i>\NumOptions\else
				\draw[OMRColor, thick]
				(\xOff + 0.6 + \i, \rowIdx) circle (\BubbleR)
				node[font=\tiny\bfseries, text=OMRColor] {\opt};
				\fi
			}
		}
	\end{tikzpicture}
	
\end{document}"""


class TemplateCompileError(Exception):
    """Raised when pdflatex compilation fails."""
    pass


class TemplateCompiler:
    """Compiles a LaTeX template from a TemplateConfig."""

    @staticmethod
    def find_pdflatex() -> str | None:
        """Locate pdflatex binary on the system."""
        # Try system PATH first
        path = shutil.which("pdflatex")
        if path:
            return path

        # Check TinyTeX default install paths
        home = Path.home()
        if platform.system() == "Windows":
            candidates = [
                home / "AppData" / "Roaming" / "TinyTeX" / "bin" / "windows" / "pdflatex.exe",
                home / "AppData" / "Roaming" / "TinyTeX" / "bin" / "win32" / "pdflatex.exe",
                Path("C:/TinyTeX/bin/windows/pdflatex.exe"),
            ]
        elif platform.system() == "Darwin":
            candidates = [
                home / "Library" / "TinyTeX" / "bin" / "universal-darwin" / "pdflatex",
                home / ".TinyTeX" / "bin" / "universal-darwin" / "pdflatex",
            ]
        else:
            candidates = [
                home / ".TinyTeX" / "bin" / "x86_64-linux" / "pdflatex",
                home / "bin" / "pdflatex",
            ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return None

    @staticmethod
    def build_latex_source(config: TemplateConfig) -> str:
        """Generate LaTeX source from template config by substituting placeholders."""
        source = LATEX_TEMPLATE
        source = source.replace("__INSTITUTION_NAME__", config.institution_name)
        source = source.replace("__ID_DIGITS__", str(config.id_digits))
        source = source.replace("__NUM_QUESTIONS__", str(config.num_questions))
        source = source.replace("__NUM_OPTIONS__", str(config.num_options))
        source = source.replace("__NUM_VERSIONS__", str(config.num_versions))
        return source

    @staticmethod
    def compile(
        config: TemplateConfig,
        logo_bytes: bytes | None = None,
        logo_ext: str = "png",
        log_callback=None,
        pdflatex_path: str | None = None,
    ) -> tuple[str, bytes]:
        """
        Compile a template and return (pdf_path, pdf_bytes).
        
        Args:
            config: Template configuration.
            logo_bytes: Raw bytes of the logo image, or None for default.
            logo_ext: Extension of the logo file (without dot).
            log_callback: Optional callable(str, str) for (message, level).
            pdflatex_path: Explicit pdflatex path, or None to auto-detect.
            
        Returns:
            Tuple of (pdf_path, pdf_bytes).
            
        Raises:
            TemplateCompileError: If compilation fails.
        """
        if pdflatex_path is None:
            pdflatex_path = TemplateCompiler.find_pdflatex()
        if pdflatex_path is None:
            raise TemplateCompileError("pdflatex not found on this system.")

        _log = log_callback or (lambda msg, level: None)

        # Create temp directory for compilation
        tmp_dir = tempfile.mkdtemp(prefix="euler_omr_compile_")
        tex_path = os.path.join(tmp_dir, "template.tex")
        assets_dir = os.path.join(tmp_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        try:
            # Write logo
            if logo_bytes:
                logo_file = os.path.join(assets_dir, f"logo.{logo_ext}")
                with open(logo_file, "wb") as f:
                    f.write(logo_bytes)
            else:
                # Copy the default logo from the app assets
                default_logo = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "assets", "logo.png"
                )
                if os.path.exists(default_logo):
                    shutil.copy2(default_logo, os.path.join(assets_dir, "logo.png"))
                else:
                    _log("Default logo not found; compilation may fail if \\includegraphics is used.", "WARNING")

            # Build and write LaTeX source
            source = TemplateCompiler.build_latex_source(config)
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(source)

            _log("Starting pdflatex compilation...", "INFO")

            # Run pdflatex
            process = subprocess.Popen(
                [pdflatex_path, "-interaction=nonstopmode", "-halt-on-error", "template.tex"],
                cwd=tmp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            last_error_line = ""
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    if line.startswith("!") or "Error" in line:
                        last_error_line = line
                        _log(line, "ERROR")
                    else:
                        _log(line, "DEBUG")

            process.wait()

            if process.returncode != 0:
                raise TemplateCompileError(
                    f"pdflatex failed (exit code {process.returncode}): {last_error_line}"
                )

            pdf_path = os.path.join(tmp_dir, "template.pdf")
            if not os.path.exists(pdf_path):
                raise TemplateCompileError("pdflatex ran but no PDF was produced.")

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            _log("Compilation successful.", "INFO")
            return pdf_path, pdf_bytes

        except TemplateCompileError:
            raise
        except Exception as e:
            raise TemplateCompileError(f"Unexpected error during compilation: {e}") from e
