"""Reads all PDF pages sequentially; emits per-page ScanResult and progress."""
from euler_omr.workers.base_worker import BaseWorker
from euler_omr.core.scan_reader import ScanReader
from PySide6.QtCore import Signal


class ScanWorkerSignals:
    pass


class ScanWorker(BaseWorker):
    def __init__(self, pdf_path: str, reader: ScanReader):
        super().__init__()
        self.pdf_path = pdf_path
        self.reader = reader
        # Extra signal for per-page results
        self.signals.page_result = Signal(object)

    def run(self):
        try:
            page_count = ScanReader.get_pdf_page_count(self.pdf_path)
            self._log(f"Reading {page_count} pages...", "INFO")
            results = []
            for i in range(page_count):
                if self.is_cancelled():
                    self._log("Scan cancelled by user", "WARNING")
                    break
                img = ScanReader.load_pdf_page(self.pdf_path, i)
                result = self.reader.read_page(img, page_no=i + 1, log_callback=self._log)
                results.append(result)
                self.signals.result.emit(result)
                self.signals.progress.emit(i + 1, page_count)
            self.signals.result.emit(results)
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(f"Scan error: {e}")
