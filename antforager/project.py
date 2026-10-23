"""Proyecto = una carpeta (puede estar en Drive/Dropbox) con un ``proyecto.json``.

    mi_proyecto/
      proyecto.json     configuración (lugar, lat/long, especie, perfil de modelo, carpeta de videos)
      datos/            datos crudos por video (se llena en etapas siguientes)
      resultados/       exportaciones

Los videos NO se copian al proyecto: se indica la carpeta donde están (ej. la carpeta sincronizada).
"""
import json
import re
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv"}


@dataclass
class Project:
    path: Path
    name: str = "Proyecto sin nombre"
    place: str = ""
    species: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    profile_id: str = "anttracker_legacy"
    videos_dir: str = ""
    mm_per_px: Optional[float] = None
    timezone: str = "America/Argentina/Buenos_Aires"   # hora local de los videos
    twilight_deg: float = -18.0                          # fin del crepúsculo (-6 civil, -12 náutico, -18 astronómico)
    notes: str = ""

    FILE = "proyecto.json"

    @classmethod
    def create(cls, path: Path, **kw) -> "Project":
        path = Path(path)
        (path / "datos").mkdir(parents=True, exist_ok=True)
        (path / "resultados").mkdir(exist_ok=True)
        p = cls(path=path, **kw)
        p.save()
        return p

    @classmethod
    def load(cls, path: Path) -> "Project":
        path = Path(path)
        data = json.loads((path / cls.FILE).read_text(encoding="utf-8"))
        known = set(cls.__dataclass_fields__) - {"path", "FILE"}
        return cls(path=path, **{k: v for k, v in data.items() if k in known})

    def save(self):
        data = asdict(self)
        data.pop("path")
        (self.path / self.FILE).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


_PATTERNS = [
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2})_(\d{2})_(\d{2})"), None),          # AntVideoRecord / AntTracker
    (re.compile(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})"), None),              # AntCam
]


def parse_start_time(filename: str) -> Optional[datetime]:
    """Hora de inicio a partir del nombre del archivo (formatos de AntVideoRecord y AntCam)."""
    for rx, _ in _PATTERNS:
        m = rx.search(filename)
        if m:
            try:
                return datetime(*map(int, m.groups()))
            except ValueError:
                continue
    return None


@dataclass
class VideoInfo:
    path: Path
    width: int = 0
    height: int = 0
    fps: float = 0.0
    frames: int = 0
    start: Optional[datetime] = None

    @property
    def duration_s(self) -> float:
        return self.frames / self.fps if self.fps else 0.0


def probe_video(path: Path) -> VideoInfo:
    import cv2
    cap = cv2.VideoCapture(str(path))
    info = VideoInfo(path=Path(path), start=parse_start_time(Path(path).name))
    if cap.isOpened():
        info.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        info.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        info.fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        info.frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    return info


def list_video_files(folder: Path) -> List[Path]:
    """Videos de la carpeta y subcarpetas, ordenados por nombre (los nombres llevan la fecha)."""
    folder = Path(folder)
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in VIDEO_EXT and not p.name.startswith("."))
