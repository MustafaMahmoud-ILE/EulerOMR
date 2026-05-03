"""Runs template compilation in QThreadPool."""
from euler_omr.workers.base_worker import BaseWorker
from euler_omr.core.template_compiler import TemplateCompiler, TemplateCompileError
from euler_omr.models.template_model import TemplateConfig
from PySide6.QtCore import Signal


class CompileWorkerSignals:
    pass


class CompileWorker(BaseWorker):
    def __init__(self, config: TemplateConfig, logo_bytes=None, logo_ext="png"):
        super().__init__()
        self.config = config
        self.logo_bytes = logo_bytes
        self.logo_ext = logo_ext

    def run(self):
        try:
            self._log("Starting compilation...", "INFO")
            pdf_path, pdf_bytes = TemplateCompiler.compile(
                self.config,
                logo_bytes=self.logo_bytes,
                logo_ext=self.logo_ext,
                log_callback=self._log,
            )
            self.signals.result.emit((pdf_path, pdf_bytes))
            self.signals.finished.emit()
        except TemplateCompileError as e:
            self.signals.error.emit(str(e))
        except Exception as e:
            self.signals.error.emit(f"Unexpected error: {e}")
