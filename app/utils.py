from __future__ import annotations
import hashlib, os, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime

IMAGE_EXTENSIONS = {'.jpg','.jpeg','.png','.webp','.bmp','.gif','.tiff','.tif','.heic','.heif'}
VIDEO_EXTENSIONS = {'.mp4','.mov','.avi','.mkv','.wmv','.m4v','.webm','.vob'}

def app_data_dir() -> Path:
    base = os.environ.get('APPDATA') if sys.platform.startswith('win') else os.environ.get('XDG_DATA_HOME')
    root = Path(base) if base else Path.home()/'.local'/'share'
    p = root/'MediaSelector'
    p.mkdir(parents=True, exist_ok=True)
    return p

def human_size(num: int) -> str:
    n = float(num)
    for unit in ['Б','КБ','МБ','ГБ','ТБ']:
        if n < 1024 or unit == 'ТБ': return f"{n:.1f} {unit}" if unit!='Б' else f"{int(n)} {unit}"
        n /= 1024
    return f"{num} Б"

def format_dt(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime('%d.%m.%Y %H:%M:%S')

def free_space(path: Path) -> int:
    return shutil.disk_usage(path).free

def sha256_file(path: Path, chunk: int = 1024*1024) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        while True:
            b = f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()

def unique_destination(dest_dir: Path, name: str) -> Path:
    candidate = dest_dir/name
    if not candidate.exists(): return candidate
    stem, suffix = Path(name).stem, Path(name).suffix
    i = 1
    while True:
        candidate = dest_dir/f"{stem} ({i}){suffix}"
        if not candidate.exists(): return candidate
        i += 1

def open_in_explorer(path: Path) -> None:
    if sys.platform.startswith('win'):
        if path.is_file(): subprocess.Popen(['explorer', '/select,', str(path)])
        else: os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == 'darwin': subprocess.Popen(['open', str(path)])
    else: subprocess.Popen(['xdg-open', str(path)])

def log_dir() -> Path:
    p = Path.cwd()/'logs'; p.mkdir(exist_ok=True); return p
