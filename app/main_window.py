from __future__ import annotations
import csv
from pathlib import Path
from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import *
from .copy_manager import CopyManager
from .file_scanner import FileScanner
from .media_viewer import MediaViewer
from .models import AppSettings, FileStatus, MediaFile, NameConflictPolicy, SessionState
from .session_manager import SessionManager
from .settings_manager import SettingsManager
from .utils import format_dt, free_space, human_size, log_dir, open_in_explorer

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__(); self.setWindowTitle('MediaSelector — безопасное копирование фото и видео'); self.resize(1280,900)
        self.settings_mgr=SettingsManager(); self.session_mgr=SessionManager(); self.settings=self.settings_mgr.load(); self.files:list[MediaFile]=[]; self.index=0; self.sources:list[str]=[]; self.destination=''; self.selected:set[str]=set(); self.copied:set[str]=set(); self.viewed:set[str]=set(); self.queue_count=0; self.current_copy=''
        self.copy=CopyManager(); self.copy.file_started.connect(self.copy_started); self.copy.file_progress.connect(self.copy_progress); self.copy.overall_progress.connect(self.overall_progress); self.copy.file_finished.connect(self.copy_finished); self.copy.paused_for_error.connect(lambda m: QMessageBox.warning(self,'Копирование приостановлено',m))
        self._ui(); self._shortcuts(); self._maybe_restore(); self.autosave=QTimer(self); self.autosave.timeout.connect(self.save_session); self.autosave.start(5000)
    def _ui(self):
        cw=QWidget(); self.setCentralWidget(cw); root=QVBoxLayout(cw)
        top=QHBoxLayout(); root.addLayout(top)
        left=QGroupBox('Куда копировать'); l=QVBoxLayout(left); self.dest_edit=QLineEdit(); self.free_lbl=QLabel('Свободное место: —'); b=QPushButton('Выбрать папку'); b.clicked.connect(self.choose_dest); l.addWidget(self.dest_edit); l.addWidget(b); l.addWidget(self.free_lbl); top.addWidget(left)
        right=QGroupBox('Где находятся фотографии и видео'); r=QVBoxLayout(right); self.src_edit=QLineEdit(); bs=QPushButton('Выбрать папки'); bs.clicked.connect(self.choose_sources); self.rec=QCheckBox('Просматривать вложенные папки'); self.rec.setChecked(self.settings.recursive); self.sort=QComboBox(); self.sort.addItems(['по имени','по дате','по размеру']); self.order=QComboBox(); self.order.addItems(['сначала старые / А-Я','сначала новые / Я-А']); start=QPushButton('Начать просмотр'); start.clicked.connect(self.start_scan); r.addWidget(self.src_edit); r.addWidget(bs); r.addWidget(self.rec); r.addWidget(self.sort); r.addWidget(self.order); r.addWidget(start); top.addWidget(right)
        opts=QHBoxLayout(); self.conflict=QComboBox(); self.conflict.addItems([p.value for p in NameConflictPolicy]); self.conflict.setCurrentText(self.settings.conflict_policy.value); self.sha=QCheckBox('Проверять контрольную сумму после копирования'); opts.addWidget(QLabel('Совпадение имён:')); opts.addWidget(self.conflict); opts.addWidget(self.sha); root.addLayout(opts)
        self.viewer=MediaViewer(); root.addWidget(self.viewer,1)
        tools=QHBoxLayout(); rot=QPushButton('Повернуть 90°'); rot.clicked.connect(self.viewer.rotate); show=QPushButton('Показать файл в Проводнике'); show.clicked.connect(self.show_current); un=QPushButton('Убрать отметку выбора'); un.clicked.connect(self.unselect_current); nxt=QPushButton('Следующий непросмотренный'); nxt.clicked.connect(self.next_unviewed); [tools.addWidget(w) for w in (rot,show,un,nxt)]; root.addLayout(tools)
        self.info=QLabel('Выберите папки и начните просмотр'); self.info.setWordWrap(True); root.addWidget(self.info)
        q=QGroupBox('Очередь копирования'); gl=QGridLayout(q); self.q_lbl=QLabel('В очереди: 0'); self.now_lbl=QLabel('Сейчас: —'); self.total_bar=QProgressBar(); self.file_bar=QProgressBar(); self.bytes_lbl=QLabel('Выбрано: 0 Б, скопировано: 0 Б'); pause=QPushButton('Пауза'); pause.clicked.connect(self.copy.pause); resume=QPushButton('Продолжить'); resume.clicked.connect(self.copy.resume); clear=QPushButton('Очистить очередь'); clear.clicked.connect(self.clear_queue); op=QPushButton('Открыть папку назначения'); op.clicked.connect(lambda: open_in_explorer(Path(self.destination)) if self.destination else None)
        for i,w in enumerate([self.q_lbl,self.now_lbl,self.total_bar,self.file_bar,self.bytes_lbl,pause,resume,clear,op]): gl.addWidget(w,i//3,i%3)
        root.addWidget(q)
    def _shortcuts(self):
        data=[('Right',self.next_file),('Left',self.prev_file),('Return',self.enqueue_current),('Enter',self.enqueue_current),('Delete',self.unselect_current),('Space',self.viewer.toggle_video),('Home',lambda:self.go(0)),('End',lambda:self.go(len(self.files)-1)),('Ctrl+O',self.choose_sources),('Ctrl+S',self.choose_dest),('F11',self.toggle_full),('Escape',lambda:self.showNormal()),('N',self.next_unviewed)]
        for key, cb in data: a=QAction(self); a.setShortcut(QKeySequence(key)); a.triggered.connect(cb); self.addAction(a)
    def choose_dest(self):
        d=QFileDialog.getExistingDirectory(self,'Куда копировать',self.destination); 
        if d: self.destination=d; self.dest_edit.setText(d); self.update_free()
    def choose_sources(self):
        d=QFileDialog.getExistingDirectory(self,'Добавить папку-источник');
        if d and d not in self.sources: self.sources.append(d); self.src_edit.setText('; '.join(self.sources))
    def start_scan(self):
        self.settings.recursive=self.rec.isChecked(); self.settings.sort_field=['name','date','size'][self.sort.currentIndex()]; self.settings.sort_descending=self.order.currentIndex()==1; self.settings.conflict_policy=NameConflictPolicy(self.conflict.currentText()); self.settings.verify_checksum=self.sha.isChecked(); self.settings_mgr.save(self.settings)
        self.scan_thread=QThread(); self.scanner=FileScanner(); self.scanner.moveToThread(self.scan_thread); self.scan_thread.started.connect(lambda:self.scanner.scan(self.sources,self.settings.recursive,self.settings.sort_field,self.settings.sort_descending)); self.scanner.finished.connect(self.scan_done); self.scanner.failed.connect(lambda e: QMessageBox.critical(self,'Ошибка сканирования',e)); self.scan_thread.start()
    def scan_done(self, files):
        self.files=files; [setattr(f,'status', FileStatus.COPIED if str(f.path) in self.copied else FileStatus.QUEUED if str(f.path) in self.selected else FileStatus.NOT_SELECTED) for f in self.files]; self.scan_thread.quit(); self.go(min(self.index,len(self.files)-1) if self.files else 0)
    def go(self,i:int):
        if not self.files: return
        self.index=max(0,min(i,len(self.files)-1)); f=self.files[self.index]; f.viewed=True; self.viewed.add(str(f.path)); self.viewer.show_media(f); self.update_info(); self.save_session()
    def next_file(self): self.go(self.index+1)
    def prev_file(self): self.go(self.index-1)
    def next_unviewed(self):
        for j in range(self.index+1,len(self.files)):
            if str(self.files[j].path) not in self.viewed: self.go(j); return
    def enqueue_current(self):
        if not self.files or not self.destination: return
        f=self.files[self.index]; p=str(f.path)
        try:
            if not f.path.exists(): raise Exception('Файл не существует')
            if not Path(self.destination).exists(): raise Exception('Папка назначения недоступна')
            if free_space(Path(self.destination)) < f.size: raise Exception('Недостаточно свободного места')
            if p in self.selected or p in self.copied: return
            if self.settings.conflict_policy == NameConflictPolicy.ASK and (Path(self.destination)/f.path.name).exists():
                answer = QMessageBox.question(self, 'Файл уже существует', f'Файл {f.path.name} уже есть в папке назначения. Перезаписать?', QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes: return
                self.settings.conflict_policy = NameConflictPolicy.OVERWRITE
            self.selected.add(p); f.status=FileStatus.QUEUED; self.queue_count+=1; self.copy.enqueue(p,self.destination,self.settings); self.update_info(); self.update_queue()
        except Exception as e: QMessageBox.warning(self,'Нельзя добавить файл',str(e))
    def unselect_current(self):
        if not self.files: return
        f=self.files[self.index]; self.selected.discard(str(f.path));
        if f.status==FileStatus.QUEUED: f.status=FileStatus.NOT_SELECTED
        self.update_info(); self.update_queue()
    def clear_queue(self): self.selected={p for p in self.selected if p==self.current_copy}; self.copy.clear_pending(); self.update_queue()
    def copy_started(self, src,dest): self.current_copy=src; self._status(src,FileStatus.COPYING); self.now_lbl.setText('Сейчас: '+Path(src).name); self.update_info()
    def copy_progress(self, src, done,total): self.file_bar.setValue(int(done*100/max(total,1)))
    def overall_progress(self, done,total): self.total_bar.setValue(int(done*100/max(total,1))); self.bytes_lbl.setText(f'Выбрано: {human_size(total)}, скопировано: {human_size(done)}')
    def copy_finished(self, src,dest,ok,msg):
        self.queue_count=max(0,self.queue_count-1); self.current_copy=''; self.selected.discard(src); self.copied.add(src) if ok else None; self._status(src, FileStatus.COPIED if ok else FileStatus.ERROR); self._log(src,dest,'OK' if ok else 'ERROR: '+msg); self.update_info(); self.update_queue(); self.save_session()
    def _status(self, src, status):
        for f in self.files:
            if str(f.path)==src: f.status=status; self.viewer.apply_status(status) if self.files and self.files[self.index] is f else None; break
    def update_info(self):
        if not self.files: return
        f=self.files[self.index]; self.info.setText(f"{f.path.name}\n{f.path}\n{self.index+1} из {len(self.files)} | {human_size(f.size)} | {format_dt(f.mtime)} | {f.resolution} | {f.status.value}\nПросмотрено: {len(self.viewed)} | Выбрано: {len(self.selected)}")
    def update_queue(self): self.q_lbl.setText(f'В очереди: {self.queue_count}')
    def update_free(self):
        try: self.free_lbl.setText('Свободное место: '+human_size(free_space(Path(self.destination))))
        except Exception: self.free_lbl.setText('Свободное место: недоступно')
    def show_current(self):
        if self.files: open_in_explorer(self.files[self.index].path)
    def toggle_full(self): self.showNormal() if self.isFullScreen() else self.showFullScreen()
    def _log(self, src,dest,result):
        p=log_dir()/'copy_log.csv'; new=not p.exists()
        with p.open('a',newline='',encoding='utf-8') as f: w=csv.writer(f); (w.writerow(['date','source','destination','result']) if new else None); w.writerow([format_dt(__import__('time').time()),src,dest,result])
    def save_session(self):
        self.session_mgr.save(SessionState(self.sources,self.destination,self.index,list(self.selected),list(self.copied),list(self.viewed),self.settings))
    def _maybe_restore(self):
        if self.session_mgr.exists() and QMessageBox.question(self,'Восстановить сеанс?','Продолжить предыдущий сеанс?', QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            s=self.session_mgr.load(); self.sources=s.source_folders; self.destination=s.destination_folder; self.index=s.current_index; self.selected=set(s.selected_files); self.copied=set(s.copied_files); self.viewed=set(s.viewed_files); self.settings=s.settings; self.src_edit.setText('; '.join(self.sources)); self.dest_edit.setText(self.destination); self.rec.setChecked(self.settings.recursive); self.update_free(); self.start_scan()
    def closeEvent(self,e): self.save_session(); self.copy.shutdown(); super().closeEvent(e)
