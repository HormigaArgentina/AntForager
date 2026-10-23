"""Detector de carga basado en YOLO (segmentación o cajas) entrenado por el usuario.

Idea: para cada hormiga (track) se toman ``n_frames`` cuadros repartidos a lo largo de su
recorrido; en cada uno se corre el modelo y se mira si alguna detección de clase "carga"
se superpone con el recuadro de la hormiga. La probabilidad de carga de la hormiga es la
fracción de cuadros con carga, reescalada para que ``decision`` (por defecto 0.4) equivalga a 0.5,
que es el umbral que usa el resto de AntTracker (``Track.load_prediction``).

NOTA: es una primera versión. El umbral ``decision`` y ``conf`` deben calibrarse contra un
conjunto de hormigas verificadas a mano antes de usar los resultados científicamente.
"""
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..tracker.blob import Blob
from ..tracker.leafdetect import LeafDetector, _get_blob_rect
from ..tracker.track import Track
from .profiles import ModelProfile

# (x0, y0, x1, y1, confianza, nombre_de_clase) en coordenadas del cuadro de entrada
Detection = Tuple[float, float, float, float, float, str]


class YoloLoadDetector(LeafDetector):
    def __init__(self, profile: ModelProfile, video, margin=6, cache_size=64):
        super().__init__(video, extra_pixels=15, n_frames=profile.n_frames)
        self.profile = profile
        self.margin = margin
        self._cache: Dict[int, List[Detection]] = {}
        self._cache_size = cache_size
        self._load_model()

    # --- modelo -------------------------------------------------------------
    def _load_model(self):
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ImportError("Este perfil necesita 'ultralytics' (pip install ultralytics).") from e
        self.model = YOLO(str(self.profile.weights))
        names = set(self.model.names.values())
        missing = [c for c in self.profile.load_classes if c not in names]
        if missing:
            raise ValueError(f"Perfil '{self.profile.id}': las clases {missing} no existen en el modelo "
                             f"(clases del modelo: {sorted(names)}). Corrija 'load_classes' en profile.json.")

    def _predict(self, frame_rgb: np.ndarray) -> List[Detection]:
        bgr = np.ascontiguousarray(frame_rgb[..., ::-1])  # ultralytics espera BGR en arrays numpy
        res = self.model.predict(bgr, conf=self.profile.conf, imgsz=self.profile.imgsz, verbose=False)[0]
        out: List[Detection] = []
        if res.boxes is None:
            return out
        for (x0, y0, x1, y1), conf, cls in zip(res.boxes.xyxy.cpu().numpy(),
                                               res.boxes.conf.cpu().numpy(),
                                               res.boxes.cls.cpu().numpy()):
            out.append((float(x0), float(y0), float(x1), float(y1), float(conf), self.model.names[int(cls)]))
        return out

    # --- lógica -------------------------------------------------------------
    def _detections(self, frame_n: int, blob: Blob) -> Tuple[List[Detection], Tuple[int, int]]:
        """Detecciones del cuadro, y el desplazamiento (ox, oy) a sumar para llevarlas a coordenadas del cuadro."""
        image = self.video[frame_n]
        if self.profile.mode == "crop":
            rect = _get_blob_rect(blob, image.shape, extra_pixels=40, square=True)
            if rect is None:
                return [], (0, 0)
            x0, x1, y0, y1 = rect.xxyy
            return self._predict(image[y0:y1, x0:x1, :]), (x0, y0)
        if frame_n not in self._cache:
            if len(self._cache) >= self._cache_size:
                self._cache.pop(next(iter(self._cache)))
            self._cache[frame_n] = self._predict(image)
        return self._cache[frame_n], (0, 0)

    def _overlaps(self, det: Detection, ant, offset) -> bool:
        ox, oy = offset
        dx0, dy0, dx1, dy1 = det[0] + ox, det[1] + oy, det[2] + ox, det[3] + oy
        ax0, ax1, ay0, ay1 = ant.xxyy
        m = self.margin
        return not (dx1 < ax0 - m or dx0 > ax1 + m or dy1 < ay0 - m or dy0 > ay1 + m)

    def frames_with_load(self, track: Track) -> Optional[Tuple[int, int]]:
        """(cuadros con carga, cuadros evaluados), o None si la hormiga no tiene cuadros útiles."""
        blobs = track.get_safe_blobs(percentage=0.05) or track.get_safe_blobs(percentage=0.025)
        if not blobs:
            return None
        frames = sorted(blobs)
        idx = np.unique(np.round(np.linspace(0, len(frames) - 1, self.n_frames)).astype(int))
        hits = 0
        for i in idx:
            f = frames[i]
            blob = blobs[f]
            dets, offset = self._detections(f, blob)
            ant = blob.bbox
            if any(d[5] in self.profile.load_classes and self._overlaps(d, ant, offset) for d in dets):
                hits += 1
        return hits, len(idx)

    @staticmethod
    def fraction_to_probability(fraction: float, decision: float) -> float:
        """Lleva ``fraction == decision`` a 0.5 (lineal por tramos), 0 -> 0 y 1 -> 1."""
        if fraction <= decision:
            return 0.5 * fraction / decision
        return 0.5 + 0.5 * (fraction - decision) / (1 - decision)

    def probability(self, track: Track) -> float:
        r = self.frames_with_load(track)
        if r is None:
            return 0.0
        hits, total = r
        return self.fraction_to_probability(hits / total, self.profile.decision)

    def call_model(self, model_input):  # no se usa: la interfaz base lo exige
        raise NotImplementedError
