from typing import Optional

from .profiles import ModelProfile, get_profile, LEGACY_ID


def create_detector(video, profile_id: Optional[str] = None):
    """Devuelve un detector con la interfaz ``probability(track) -> float`` para el perfil pedido
    (o el activo). Si ``profile_id`` no existe lanza KeyError con los perfiles disponibles."""
    profile = get_profile(profile_id)
    print(f"[detection] usando perfil '{profile.id}' ({profile.name}), tipo {profile.kind}")
    return build_detector(profile, video)


def build_detector(profile: ModelProfile, video):
    if profile.kind == "tflite_legacy":
        from ..tracker.leafdetect import TFLiteLeafDetector
        return TFLiteLeafDetector(str(profile.weights), video)
    if profile.kind in ("yolo_seg", "yolo_det"):
        from .yolo_load import YoloLoadDetector
        return YoloLoadDetector(profile, video)
    raise ValueError(f"Tipo de perfil no soportado: {profile.kind}")
