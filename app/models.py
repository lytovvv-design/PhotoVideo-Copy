from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"

class FileStatus(str, Enum):
    NOT_SELECTED = "Не выбран"
    QUEUED = "В очереди"
    COPYING = "Копируется"
    COPIED = "Скопирован"
    ERROR = "Ошибка"

class NameConflictPolicy(str, Enum):
    ADD_NUMBER = "Добавить номер к имени"
    SKIP = "Пропустить файл"
    ASK = "Спросить пользователя"
    OVERWRITE = "Перезаписать"

@dataclass(slots=True)
class MediaFile:
    path: Path
    media_type: MediaType
    size: int
    mtime: float
    resolution: str = "Неизвестно"
    status: FileStatus = FileStatus.NOT_SELECTED
    viewed: bool = False
    copied_to: Optional[Path] = None
    error: str = ""

@dataclass(slots=True)
class AppSettings:
    conflict_policy: NameConflictPolicy = NameConflictPolicy.ADD_NUMBER
    verify_checksum: bool = False
    recursive: bool = True
    sort_field: str = "name"
    sort_descending: bool = False

@dataclass(slots=True)
class SessionState:
    source_folders: list[str] = field(default_factory=list)
    destination_folder: str = ""
    current_index: int = 0
    selected_files: list[str] = field(default_factory=list)
    copied_files: list[str] = field(default_factory=list)
    viewed_files: list[str] = field(default_factory=list)
    settings: AppSettings = field(default_factory=AppSettings)
