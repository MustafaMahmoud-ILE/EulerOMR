"""Utility to verify LaTeX availability before compilation.

This module provides a pre-flight check that MUST be called from the
main (UI) thread, because it may show a QDialog to let the user install
TinyTeX on the spot.
"""


def ensure_latex_available(parent=None) -> bool:
    """
    Check whether a LaTeX engine (pdflatex) is reachable.

    If not, show the TinyTeX installation dialog and wait for the user
    to complete or cancel the installation.

    Returns True if pdflatex is available after the check, False otherwise.
    """
    # 1. Try pytinytex's managed installation
    try:
        import pytinytex
        engine = pytinytex.get_pdflatex_engine()
        if engine:
            return True
    except Exception:
        pass

    # 2. Fallback: check if pdflatex is on PATH (e.g. TeX Live, MiKTeX)
    import shutil
    if shutil.which("pdflatex"):
        return True

    # 3. Nothing found — show the installation dialog (must be on UI thread)
    from euler_omr.ui.dialogs.tinytex_dialog import TinyTexInstallDialog
    dialog = TinyTexInstallDialog(parent)
    dialog.exec()

    # 4. Re-check after the dialog closes
    try:
        import pytinytex
        if pytinytex.get_pdflatex_engine():
            return True
    except Exception:
        pass

    if shutil.which("pdflatex"):
        return True

    return False
