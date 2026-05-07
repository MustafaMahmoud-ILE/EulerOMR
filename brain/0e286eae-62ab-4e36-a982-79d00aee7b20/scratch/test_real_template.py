import json
import os
import sys
import base64

# Ensure project root is in path
sys.path.insert(0, r"d:\Euler OMR")

from euler_omr.file_io.eomrt_handler import EomrtHandler
from euler_omr.core.template_compiler import TemplateCompiler

template_path = r"d:\Euler OMR\experiment\Materials\EUI.eomrt"
pdflatex_path = r"d:\Euler OMR\experiment\tinytex_installed\TinyTeX\bin\windows\pdflatex.exe"

print(f"Loading template from: {template_path}")
try:
    template_data = EomrtHandler.load(template_path)
    config = template_data["config"]
    logo_bytes = template_data["logo_bytes"]
except Exception as e:
    print(f"❌ Failed to load template: {e}")
    sys.exit(1)

print(f"Compiling real template: {config.institution_name}")

def log_cb(msg, level):
    # Only print INFO and ERROR to keep output clean
    if level in ["INFO", "ERROR"]:
        print(f"[{level}] {msg}")

try:
    pdf_path, pdf_bytes = TemplateCompiler.compile(
        config=config,
        logo_bytes=logo_bytes,
        pdflatex_path=pdflatex_path,
        log_callback=log_cb
    )
    
    # Save the result to experiment folder for verification
    output_pdf = r"d:\Euler OMR\experiment\EUI_recompiled.pdf"
    with open(output_pdf, "wb") as f:
        f.write(pdf_bytes)
        
    print(f"\n✅ Success! Real template recompiled.")
    print(f"PDF saved to: {output_pdf}")
    print(f"Size: {len(pdf_bytes)} bytes")
except Exception as e:
    print(f"\n❌ Compilation failed: {e}")
    import traceback
    traceback.print_exc()
