"""Detección de carga intercambiable por especie/región.

Uso típico:
    from ant_tracker.detection import create_detector
    detector = create_detector(video)            # perfil activo
    detector = create_detector(video, "acromyrmex_lundi")
    prob = detector.probability(track)

Ver ``profiles.py`` para el formato de los perfiles.
"""
from .profiles import (ModelProfile, list_profiles, get_profile, get_active_profile_id,
                       set_active_profile_id, models_search_paths)
from .factory import create_detector

__all__ = ["ModelProfile", "list_profiles", "get_profile", "get_active_profile_id",
           "set_active_profile_id", "models_search_paths", "create_detector"]
