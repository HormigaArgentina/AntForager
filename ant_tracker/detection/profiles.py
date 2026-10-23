"""Perfiles de modelo: cada especie/región/escenario es una carpeta con un ``profile.json``
y su archivo de pesos. El investigador agrega perfiles sin tocar código.

Estructura::

    models/
      acromyrmex_lundi/
        profile.json
        weights.pt
      mi_especie/
        profile.json
        weights.pt

Campos de ``profile.json``:
    id           identificador (por defecto, el nombre de la carpeta)
    name         nombre para mostrar
    species      especie
    kind         "yolo_seg" | "yolo_det" | "tflite_legacy"
    weights      archivo de pesos, relativo a la carpeta del perfil
    load_classes lista de clases que significan "lleva carga" (ej. ["leaf"])
    conf         umbral de confianza de detección (0-1)
    imgsz        tamaño de imagen de entrada del modelo
    mode         "frame" (cuadro completo, recomendado) o "crop" (recorte alrededor de la hormiga)
    n_frames     cuántos cuadros de cada hormiga se evalúan
    decision     fracción de cuadros con carga necesaria para decidir "cargada" (default 0.4)
    author, trained_on, notes   metadatos libres
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

KINDS = ("yolo_seg", "yolo_det", "tflite_legacy")
LEGACY_ID = "anttracker_legacy"


@dataclass
class ModelProfile:
    id: str
    name: str
    kind: str
    weights: Path
    folder: Path
    species: str = ""
    load_classes: List[str] = field(default_factory=lambda: ["leaf"])
    conf: float = 0.5
    imgsz: int = 640
    mode: str = "frame"
    n_frames: int = 12
    decision: float = 0.4
    author: str = ""
    trained_on: str = ""
    notes: str = ""

    @classmethod
    def from_folder(cls, folder: Path) -> "ModelProfile":
        data = json.loads((folder / "profile.json").read_text(encoding="utf-8"))
        kind = data.get("kind", "yolo_seg")
        if kind not in KINDS:
            raise ValueError(f"{folder.name}: 'kind' inválido '{kind}' (use {KINDS})")
        weights = data.get("weights")
        if not weights:
            raise ValueError(f"{folder.name}: falta el campo 'weights'")
        known = {f for f in cls.__dataclass_fields__}
        extra = {k: v for k, v in data.items() if k in known and k not in ("id", "name", "kind", "weights", "folder")}
        prof = cls(id=data.get("id", folder.name), name=data.get("name", folder.name), kind=kind,
                   weights=(folder / weights), folder=folder, **extra)
        if not 0 <= prof.conf <= 1:
            raise ValueError(f"{prof.id}: 'conf' debe estar entre 0 y 1")
        if prof.mode not in ("frame", "crop"):
            raise ValueError(f"{prof.id}: 'mode' debe ser 'frame' o 'crop'")
        return prof

    @property
    def available(self) -> bool:
        return self.weights.exists()


def models_search_paths() -> List[Path]:
    """Carpetas donde se buscan perfiles (las primeras tienen prioridad):
    1. variable de entorno ANTFORAGER_MODELS
    2. ~/AntForager/models  (perfiles propios del usuario)
    3. <repo>/models        (perfiles incluidos con el software)
    """
    paths = []
    env = os.environ.get("ANTFORAGER_MODELS")
    if env:
        paths.append(Path(env))
    paths.append(Path.home() / "AntForager" / "models")
    paths.append(Path(__file__).resolve().parent.parent.parent / "models")
    return paths


def list_profiles(include_unavailable=False) -> Dict[str, ModelProfile]:
    found: Dict[str, ModelProfile] = {}
    for base in models_search_paths():
        if not base.is_dir():
            continue
        for folder in sorted(base.iterdir()):
            if not (folder / "profile.json").exists():
                continue
            try:
                prof = ModelProfile.from_folder(folder)
            except Exception as e:  # un perfil roto no debe tirar abajo a los demás
                print(f"[detection] perfil ignorado ({folder}): {e}")
                continue
            if prof.id in found:
                continue  # el de mayor prioridad ya está
            if prof.available or include_unavailable:
                found[prof.id] = prof
    return found


def _config_path() -> Path:
    return Path.home() / "AntForager" / "config.json"


def get_active_profile_id() -> str:
    env = os.environ.get("ANTFORAGER_PROFILE")
    if env:
        return env
    try:
        return json.loads(_config_path().read_text(encoding="utf-8")).get("active_profile", LEGACY_ID)
    except (OSError, ValueError):
        return LEGACY_ID


def set_active_profile_id(profile_id: str):
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    cfg["active_profile"] = profile_id
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def get_profile(profile_id: Optional[str] = None) -> ModelProfile:
    profile_id = profile_id or get_active_profile_id()
    profiles = list_profiles()
    if profile_id not in profiles:
        disponibles = ", ".join(profiles) or "(ninguno)"
        raise KeyError(f"Perfil '{profile_id}' no encontrado o sin archivo de pesos. Disponibles: {disponibles}")
    return profiles[profile_id]
