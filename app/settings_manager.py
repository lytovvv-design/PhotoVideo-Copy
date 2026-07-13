from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from .models import AppSettings, NameConflictPolicy
from .utils import app_data_dir

class SettingsManager:
    def __init__(self) -> None:
        self.path = app_data_dir()/'settings.json'
    def load(self) -> AppSettings:
        if not self.path.exists(): return AppSettings()
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            data['conflict_policy'] = NameConflictPolicy(data.get('conflict_policy', NameConflictPolicy.ADD_NUMBER.value))
            return AppSettings(**data)
        except Exception:
            return AppSettings()
    def save(self, settings: AppSettings) -> None:
        data = asdict(settings); data['conflict_policy'] = settings.conflict_policy.value
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
