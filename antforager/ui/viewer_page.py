from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget)


class ViewerPage(QWidget):
    """Visor de video con detección opcional de carga usando el perfil de modelo del proyecto."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.cap = None
        self.n_frames = 0
        self.fps = 25.0
        self.frame_bgr = None
        self._model = None
        self._model_key = None

        lay = QVBoxLayout(self)
        self.title = QLabel("<h2>Visor</h2><p>Elegí un video en la pestaña Videos.</p>")
        lay.addWidget(self.title)
        self.view = QLabel()
        self.view.setMinimumSize(640, 400)
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background:#111;")
        lay.addWidget(self.view, 1)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.show_frame)
        lay.addWidget(self.slider)
        row = QHBoxLayout()
        self.play = QPushButton("▶ Reproducir")
        self.play.setCheckable(True)
        self.play.toggled.connect(self.toggle_play)
        self.detect = QCheckBox("Detectar carga (perfil del proyecto)")
        self.detect.toggled.connect(lambda _: self.show_frame(self.slider.value()))
        self.info = QLabel("")
        row.addWidget(self.play)
        row.addWidget(self.detect)
        row.addWidget(self.info, 1)
        lay.addLayout(row)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step)

    def refresh(self):
        pass

    def load_video(self, path: Path):
        self.play.setChecked(False)
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            self.title.setText(f"<h2>Visor</h2><p>No se pudo abrir {path.name}</p>")
            self.cap = None
            return
        self.n_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        self.title.setText(f"<h2>Visor</h2><p>{path.name}</p>")
        self.slider.blockSignals(True)
        self.slider.setRange(0, max(self.n_frames - 1, 0))
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self.show_frame(0)

    def toggle_play(self, on):
        self.play.setText("⏸ Pausa" if on else "▶ Reproducir")
        if on and self.cap:
            self.timer.start(int(1000 / min(self.fps, 30)))
        else:
            self.timer.stop()

    def step(self):
        v = self.slider.value() + 1
        if v >= self.n_frames:
            self.play.setChecked(False)
            return
        self.slider.setValue(v)  # dispara show_frame

    def show_frame(self, idx):
        if not self.cap:
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = self.cap.read()
        if not ok:
            return
        self.frame_bgr = frame
        out = self._draw_detections(frame.copy()) if self.detect.isChecked() else frame
        rgb = cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        img = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        self.view.setPixmap(QPixmap.fromImage(img).scaled(self.view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        t = idx / self.fps
        self.info.setText(f"cuadro {idx}/{self.n_frames}   {int(t // 60):02d}:{t % 60:04.1f}")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.cap:
            self.show_frame(self.slider.value())

    # --- detección ---
    def _get_model(self):
        p = self.win.project
        if p is None:
            return None, None
        try:
            from ant_tracker.detection import get_profile
            prof = get_profile(p.profile_id)
            if not prof.kind.startswith("yolo"):
                self.info.setText("El perfil del proyecto no es un modelo YOLO.")
                return None, None
            if self._model_key != prof.id:
                from ultralytics import YOLO
                self._model, self._model_key = YOLO(str(prof.weights)), prof.id
            return self._model, prof
        except Exception as e:
            self.info.setText(f"Detección no disponible: {e}")
            self.detect.blockSignals(True)
            self.detect.setChecked(False)
            self.detect.blockSignals(False)
            return None, None

    def _draw_detections(self, frame):
        model, prof = self._get_model()
        if model is None:
            return frame
        res = model.predict(frame, conf=prof.conf, imgsz=prof.imgsz, verbose=False)[0]
        if res.boxes is not None:
            for (x0, y0, x1, y1), c in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.conf.cpu().numpy()):
                cv2.rectangle(frame, (int(x0), int(y0)), (int(x1), int(y1)), (0, 255, 255), 2)
                cv2.putText(frame, f"{c:.2f}", (int(x0), max(int(y0) - 4, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        return frame
