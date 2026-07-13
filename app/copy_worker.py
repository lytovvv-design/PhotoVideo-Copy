from __future__ import annotations
import os, time
from pathlib import Path
from PySide6.QtCore import QObject, QMutex, QWaitCondition, Signal, Slot
from .models import NameConflictPolicy
from .utils import sha256_file, unique_destination

class CopyWorker(QObject):
    file_started = Signal(str, str)
    file_progress = Signal(str, int, int)
    overall_progress = Signal(int, int)
    file_finished = Signal(str, str, bool, str)
    paused_for_error = Signal(str)
    queue_empty = Signal()
    def __init__(self) -> None:
        super().__init__(); self.queue: list[tuple[str,str,str,bool]] = []; self.total=0; self.done=0; self.running=True; self.paused=False; self.mutex=QMutex(); self.cond=QWaitCondition()
    @Slot(str, str, str, bool)
    def enqueue(self, src: str, dest_dir: str, policy: str, verify: bool) -> None:
        self.mutex.lock(); self.queue.append((src,dest_dir,policy,verify)); self.total += Path(src).stat().st_size if Path(src).exists() else 0; self.cond.wakeAll(); self.mutex.unlock()
    @Slot()
    def pause(self) -> None: self.paused = True
    @Slot()
    def resume(self) -> None: self.paused=False; self.cond.wakeAll()
    @Slot()
    def clear_pending(self) -> None:
        self.mutex.lock(); self.queue.clear(); self.mutex.unlock()
    @Slot()
    def stop(self) -> None: self.running=False; self.cond.wakeAll()
    @Slot()
    def process(self) -> None:
        while self.running:
            self.mutex.lock()
            while self.running and (self.paused or not self.queue): self.cond.wait(self.mutex, 500)
            if not self.running: self.mutex.unlock(); break
            src_s, dest_s, pol_s, verify = self.queue.pop(0); self.mutex.unlock()
            src, dest_dir = Path(src_s), Path(dest_s)
            try:
                if not src.exists(): raise FileNotFoundError('Исходный файл не найден')
                if not dest_dir.exists(): raise FileNotFoundError('Папка назначения недоступна')
                policy = NameConflictPolicy(pol_s)
                dest = dest_dir/src.name
                if dest.exists():
                    if policy == NameConflictPolicy.SKIP:
                        self.file_finished.emit(str(src), str(dest), False, 'Пропущен: файл уже существует'); continue
                    if policy == NameConflictPolicy.ADD_NUMBER: dest = unique_destination(dest_dir, src.name)
                self.file_started.emit(str(src), str(dest))
                copied = 0; size = src.stat().st_size
                with src.open('rb') as r, dest.open('wb') as w:
                    while True:
                        while self.paused and self.running: time.sleep(0.1)
                        block = r.read(1024*1024)
                        if not block: break
                        w.write(block); copied += len(block); self.file_progress.emit(str(src), copied, size); self.overall_progress.emit(self.done+copied, self.total)
                if not dest.exists() or dest.stat().st_size != size: raise IOError('Размер скопированного файла не совпадает')
                if verify and sha256_file(src) != sha256_file(dest): raise IOError('SHA-256 не совпадает')
                self.done += size; self.file_finished.emit(str(src), str(dest), True, 'Скопирован')
            except Exception as e:
                self.paused = not Path(dest_s).exists()
                if self.paused: self.paused_for_error.emit('Папка назначения недоступна. Подключите диск и нажмите «Продолжить».')
                self.file_finished.emit(src_s, '', False, str(e))
        self.queue_empty.emit()
