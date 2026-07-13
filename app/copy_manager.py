from __future__ import annotations
from PySide6.QtCore import QObject, QThread, Signal
from .copy_worker import CopyWorker
from .models import AppSettings

class CopyManager(QObject):
    file_started = Signal(str, str); file_progress = Signal(str, int, int); overall_progress = Signal(int, int); file_finished = Signal(str, str, bool, str); paused_for_error = Signal(str)
    def __init__(self) -> None:
        super().__init__(); self.thread=QThread(); self.worker=CopyWorker(); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.process)
        self.worker.file_started.connect(self.file_started); self.worker.file_progress.connect(self.file_progress); self.worker.overall_progress.connect(self.overall_progress); self.worker.file_finished.connect(self.file_finished); self.worker.paused_for_error.connect(self.paused_for_error); self.thread.start()
    def enqueue(self, src: str, dest: str, settings: AppSettings) -> None: self.worker.enqueue(src, dest, settings.conflict_policy.value, settings.verify_checksum)
    def pause(self) -> None: self.worker.pause()
    def resume(self) -> None: self.worker.resume()
    def clear_pending(self) -> None: self.worker.clear_pending()
    def shutdown(self) -> None: self.worker.stop(); self.thread.quit(); self.thread.wait(3000)
