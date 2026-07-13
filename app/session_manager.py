from __future__ import annotations
import json
from dataclasses import asdict
from .models import AppSettings, NameConflictPolicy, SessionState
from .utils import app_data_dir

class SessionManager:
    def __init__(self) -> None:
        self.path = app_data_dir()/'session.json'
    def exists(self) -> bool: return self.path.exists()
    def load(self) -> SessionState:
        data = json.loads(self.path.read_text(encoding='utf-8'))
        s = data.get('settings', {})
        s['conflict_policy'] = NameConflictPolicy(s.get('conflict_policy', NameConflictPolicy.ADD_NUMBER.value))
        data['settings'] = AppSettings(**s)
        return SessionState(**data)
    def save(self, state: SessionState) -> None:
        data = asdict(state); data['settings']['conflict_policy'] = state.settings.conflict_policy.value
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    def clear(self) -> None:
        if self.path.exists(): self.path.unlink()
