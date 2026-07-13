from __future__ import annotations
from pathlib import Path
from PIL import Image
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtMultimedia import QMediaPlayer
from .models import MediaFile, MediaType
from .utils import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

class FileScanner(QObject):
    finished = Signal(list)
    failed = Signal(str)
    @Slot(list, bool, str, bool)
    def scan(self, folders: list[str], recursive: bool, sort_field: str, desc: bool) -> None:
        try:
            result: list[MediaFile] = []
            seen: set[Path] = set()
            for folder in folders:
                root = Path(folder)
                it = root.rglob('*') if recursive else root.glob('*')
                for p in it:
                    if not p.is_file(): continue
                    ext = p.suffix.lower()
                    kind = MediaType.IMAGE if ext in IMAGE_EXTENSIONS else MediaType.VIDEO if ext in VIDEO_EXTENSIONS else None
                    if not kind: continue
                    rp = p.resolve()
                    if rp in seen: continue
                    seen.add(rp); st = p.stat(); res = 'Неизвестно'
                    if kind == MediaType.IMAGE:
                        try:
                            with Image.open(p) as im: res = f'{im.width}×{im.height}'
                        except Exception: pass
                    result.append(MediaFile(p, kind, st.st_size, st.st_mtime, res))
            key = {'name': lambda m: m.path.name.lower(), 'date': lambda m: m.mtime, 'size': lambda m: m.size}.get(sort_field, lambda m: m.path.name.lower())
            result.sort(key=key, reverse=desc)
            self.finished.emit(result)
        except Exception as e:
            self.failed.emit(str(e))
