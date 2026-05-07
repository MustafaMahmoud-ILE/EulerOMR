import os
import sys

# Ensure project root is in path
sys.path.insert(0, r"d:\Euler OMR")

from euler_omr.file_io.eomrt_handler import EomrtHandler
from euler_omr.core.template_compiler import TemplateCompiler

template_path = r"d:\Euler OMR\experiment\Materials\EUI.eomrt"

print(f"Loading template from: {template_path}")
try:
    template_data = EomrtHandler.load(template_path)
    config = template_data["config"]
    logo_bytes = template_data["logo_bytes"]
except Exception as e:
    print(f"❌ Failed to load template: {e}")
    sys.exit(1)

print(f"Compiling template: {config.institution_name}")
print("Auto-install is enabled via PyTinyTeX.")

def log_cb(msg, level):
    print(f"[{level}] {msg}")

try:
    # Note: we don't pass pdflatex_path anymore, let pytinytex find it
    pdf_path, pdf_bytes = TemplateCompiler.compile(
        config=config,
        logo_bytes=logo_bytes,
        log_callback=log_cb
    )
    
    output_pdf = r"d:\Euler OMR\experiment\EUI_pytinytex.pdf"
    with open(output_pdf, "wb") as f:
        f.write(pdf_bytes)
        
    print(f"\n✅ Success! Template recompiled using PyTinyTeX.")
    print(f"PDF saved to: {output_pdf}")
except Exception as e:
    print(f"\n❌ Compilation failed: {e}")
    import traceback
    traceback.print_exc()
