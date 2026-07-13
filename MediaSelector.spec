# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('PySide6.QtMultimedia') + collect_submodules('PySide6.QtMultimediaWidgets')
datas = collect_data_files('PySide6')

a = Analysis(['main.py'], pathex=[], binaries=[], datas=datas, hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='MediaSelector', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name='MediaSelector')
