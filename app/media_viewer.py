from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageOps
from PySide6.QtCore import Qt, QUrl, QPoint
from PySide6.QtGui import QImage, QPixmap, QWheelEvent, QMouseEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QLabel, QSlider, QStackedWidget, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from .models import MediaFile, MediaType, FileStatus
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception: pass

class ImageLabel(QLabel):
    def __init__(self) -> None:
        super().__init__('Нет файла'); self.setAlignment(Qt.AlignmentFlag.AlignCenter); self.setMinimumHeight(360); self._pix: QPixmap|None=None; self.zoom=1.0; self.offset=QPoint(0,0); self.drag: QPoint|None=None
    def set_pixmap(self, pix: QPixmap) -> None: self._pix=pix; self.zoom=1.0; self.offset=QPoint(0,0); self._update()
    def _update(self) -> None:
        if not self._pix: return
        size = self.size()*self.zoom
        p = self._pix.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        canvas = QPixmap(self.size()); canvas.fill(Qt.GlobalColor.black)
        from PySide6.QtGui import QPainter
        painter=QPainter(canvas); x=(self.width()-p.width())//2+self.offset.x(); y=(self.height()-p.height())//2+self.offset.y(); painter.drawPixmap(x,y,p); painter.end(); self.setPixmap(canvas)
    def resizeEvent(self, e): self._update(); super().resizeEvent(e)
    def wheelEvent(self, e: QWheelEvent) -> None: self.zoom=max(0.2,min(5.0,self.zoom+(0.1 if e.angleDelta().y()>0 else -0.1))); self._update()
    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button()==Qt.MouseButton.LeftButton: self.drag=e.pos()
    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self.drag: self.offset += e.pos()-self.drag; self.drag=e.pos(); self._update()
    def mouseReleaseEvent(self, e: QMouseEvent) -> None: self.drag=None

class MediaViewer(QWidget):
    def __init__(self) -> None:
        super().__init__(); self.rotation=0; self.current: MediaFile|None=None
        self.stack=QStackedWidget(); self.image=ImageLabel(); self.video=QVideoWidget(); self.stack.addWidget(self.image); self.stack.addWidget(self.video)
        self.player=QMediaPlayer(self); self.audio=QAudioOutput(self); self.player.setAudioOutput(self.audio); self.player.setVideoOutput(self.video); self.audio.setVolume(0.5)
        self.play=QPushButton('▶/⏸'); self.pos=QSlider(Qt.Orientation.Horizontal); self.vol=QSlider(Qt.Orientation.Horizontal); self.vol.setRange(0,100); self.vol.setValue(50); self.time=QLabel('00:00 / 00:00')
        controls=QHBoxLayout(); [controls.addWidget(w) for w in (self.play,self.pos,self.time,QLabel('Громкость'),self.vol)]
        lay=QVBoxLayout(self); lay.addWidget(self.stack,1); lay.addLayout(controls)
        self.play.clicked.connect(self.toggle_video); self.pos.sliderMoved.connect(self.player.setPosition); self.vol.valueChanged.connect(lambda v: self.audio.setVolume(v/100)); self.player.positionChanged.connect(self._pos); self.player.durationChanged.connect(lambda d: self.pos.setRange(0,d))
    def show_media(self, media: MediaFile) -> None:
        self.current=media; self.rotation=0; self.player.stop()
        if media.media_type==MediaType.VIDEO:
            self.stack.setCurrentWidget(self.video); self.player.setSource(QUrl.fromLocalFile(str(media.path))); self.player.play()
        else:
            self.stack.setCurrentWidget(self.image); self._load_image(media.path)
        self.apply_status(media.status)
    def _load_image(self, path: Path) -> None:
        try:
            with Image.open(path) as im:
                im=ImageOps.exif_transpose(im); im.thumbnail((2400,1600));
                if self.rotation: im=im.rotate(-self.rotation, expand=True)
                im=im.convert('RGBA'); data=im.tobytes('raw','RGBA'); q=QImage(data, im.width, im.height, QImage.Format.Format_RGBA8888).copy(); self.image.set_pixmap(QPixmap.fromImage(q))
        except Exception as e: self.image.setText(f'Не удалось открыть изображение:\n{e}')
    def rotate(self) -> None:
        if self.current and self.current.media_type==MediaType.IMAGE: self.rotation=(self.rotation+90)%360; self._load_image(self.current.path)
    def toggle_video(self) -> None:
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState: self.player.pause()
        else: self.player.play()
    def _pos(self, p:int) -> None:
        d=self.player.duration(); self.pos.setValue(p); self.time.setText(f'{p//60000:02d}:{p//1000%60:02d} / {d//60000:02d}:{d//1000%60:02d}')
    def apply_status(self, status: FileStatus) -> None:
        colors={FileStatus.QUEUED:'#d7a900',FileStatus.COPYING:'#1683ff',FileStatus.COPIED:'#18a558',FileStatus.ERROR:'#d93025'}; c=colors.get(status,'#444'); self.stack.setStyleSheet(f'QStackedWidget{{border:4px solid {c}; background:black;}}')
