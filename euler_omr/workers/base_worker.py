"""QRunnable base with QObject signals mixin."""
from PySide6.QtCore import QRunnable, QObject, Signal, QMutex


class WorkerSignals(QObject):
    progress = Signal(int, int)        # current, total
    log = Signal(str, str)             # message, level
    finished = Signal()
    error = Signal(str)
    result = Signal(object)


class BaseWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self._cancel_mutex = QMutex()
        self._cancel_requested = False
        self.setAutoDelete(True)

    def cancel(self):
        self._cancel_mutex.lock()
        self._cancel_requested = True
        self._cancel_mutex.unlock()

    def is_cancelled(self) -> bool:
        self._cancel_mutex.lock()
        val = self._cancel_requested
        self._cancel_mutex.unlock()
        return val

    def _log(self, msg: str, level: str = "INFO"):
        self.signals.log.emit(msg, level)
