from __future__ import annotations
import logging
from pathlib import Path
from time import perf_counter
from PySide6.QtCore import QObject, QThread, Signal, Slot
from .models import MediaFile, MediaType
from .utils import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)


class FileScanner(QObject):
    files_batch_found = Signal(list, int)
    finished = Signal(list, int)
    failed = Signal(str, int)

    @Slot(list, bool, str, bool, int)
    def scan(self, folders: list[str], recursive: bool, sort_field: str, desc: bool, generation: int) -> None:
        total_started = perf_counter()
        try:
            result: list[MediaFile] = []
            seen: set[Path] = set()
            batch: list[MediaFile] = []
            batch_size = 100
            walk_time = 0.0
            list_time = 0.0
            metadata_time = 0.0
            thumbnail_time = 0.0

            for folder in folders:
                if QThread.currentThread().isInterruptionRequested():
                    return
                root = Path(folder)
                walk_started = perf_counter()
                iterator = root.rglob('*') if recursive else root.glob('*')
                for p in iterator:
                    if QThread.currentThread().isInterruptionRequested():
                        return
                    list_started = perf_counter()
                    if not p.is_file():
                        list_time += perf_counter() - list_started
                        continue
                    ext = p.suffix.lower()
                    kind = MediaType.IMAGE if ext in IMAGE_EXTENSIONS else MediaType.VIDEO if ext in VIDEO_EXTENSIONS else None
                    if not kind:
                        list_time += perf_counter() - list_started
                        continue
                    rp = p.absolute()
                    if rp in seen:
                        list_time += perf_counter() - list_started
                        continue
                    seen.add(rp)
                    # Initial scan is intentionally minimal: no stat(), no Pillow image open,
                    # no video probing, and no thumbnail generation for every file.
                    media = MediaFile(rp, kind, 0, 0.0)
                    result.append(media)
                    batch.append(media)
                    list_time += perf_counter() - list_started
                    if len(batch) >= batch_size:
                        self.files_batch_found.emit(batch, generation)
                        batch = []
                walk_time += perf_counter() - walk_started

            if batch:
                self.files_batch_found.emit(batch, generation)

            sort_started = perf_counter()
            if sort_field == 'name':
                result.sort(key=lambda m: m.path.name.lower(), reverse=desc)
            else:
                metadata_started = perf_counter()
                for media in result:
                    if QThread.currentThread().isInterruptionRequested():
                        return
                    try:
                        st = media.path.stat()
                        media.size = st.st_size
                        media.mtime = st.st_mtime
                    except OSError:
                        logger.exception('Не удалось получить stat() для %s', media.path)
                metadata_time = perf_counter() - metadata_started
                key = (lambda m: m.mtime) if sort_field == 'date' else (lambda m: m.size)
                result.sort(key=key, reverse=desc)
            sort_time = perf_counter() - sort_started

            logger.info('Обход новой папки завершён за %.3f сек.', walk_time)
            logger.info('Формирование списка файлов заняло %.3f сек.', list_time)
            logger.info('Получение метаданных заняло %.3f сек.', metadata_time)
            logger.info('Сортировка заняла %.3f сек.', sort_time)
            logger.info('Создание миниатюр заняло %.3f сек.', thumbnail_time)
            logger.info('Полное сканирование завершено за %.3f сек. Найдено файлов: %d', perf_counter() - total_started, len(result))
            self.finished.emit(result, generation)
        except Exception as e:
            logger.exception('Ошибка сканирования папки')
            self.failed.emit(str(e), generation)
