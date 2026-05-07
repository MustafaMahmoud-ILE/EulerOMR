import subprocess
import os

pdflatex_path = r"d:\Euler OMR\experiment\tinytex_installed\TinyTeX\bin\windows\pdflatex.exe"
test_dir = r"d:\Euler OMR\experiment\latex_test"
os.makedirs(test_dir, exist_ok=True)

tex_content = r"""
\documentclass{article}
\begin{document}
Hello from TinyTeX in Euler OMR!
\end{document}
"""

tex_file = os.path.join(test_dir, "test.tex")
with open(tex_file, "w") as f:
    f.write(tex_content)

print(f"Testing pdflatex at: {pdflatex_path}")
try:
    result = subprocess.run(
        [pdflatex_path, "-interaction=nonstopmode", "test.tex"],
        cwd=test_dir,
        capture_output=True,
        text=True
    )
    print(f"Exit code: {result.returncode}")
    if result.returncode == 0:
        print("Success! PDF generated.")
        pdf_file = os.path.join(test_dir, "test.pdf")
        if os.path.exists(pdf_file):
            print(f"Found PDF at: {pdf_file}")
    else:
        print("Failed to generate PDF.")
        print("Stdout:", result.stdout)
        print("Stderr:", result.stderr)
except Exception as e:
    print(f"Error running pdflatex: {e}")
