"""Herramientas de línea de comandos.

    python -m ant_tracker.detection list
    python -m ant_tracker.detection activate <id>
    python -m ant_tracker.detection check <id>     # valida el perfil y sus pesos
"""
import sys

from .profiles import list_profiles, get_profile, get_active_profile_id, set_active_profile_id, models_search_paths


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "list"
    if cmd == "list":
        active = get_active_profile_id()
        print("Carpetas de búsqueda:", *[str(p) for p in models_search_paths()], sep="\n  ")
        profs = list_profiles(include_unavailable=True)
        if not profs:
            print("No hay perfiles.")
        for p in profs.values():
            flag = "*" if p.id == active else " "
            est = "" if p.available else "  [FALTA ARCHIVO DE PESOS]"
            print(f"{flag} {p.id:28s} {p.kind:14s} {p.name}{est}")
        print("\n* = activo")
    elif cmd == "activate" and len(argv) > 2:
        get_profile(argv[2])  # valida que exista
        set_active_profile_id(argv[2])
        print(f"Perfil activo: {argv[2]}")
    elif cmd == "check" and len(argv) > 2:
        p = get_profile(argv[2])
        print(p)
        if p.kind.startswith("yolo"):
            from ultralytics import YOLO
            names = YOLO(str(p.weights)).names
            print("Clases del modelo:", names)
            missing = [c for c in p.load_classes if c not in names.values()]
            print("OK" if not missing else f"ERROR: clases inexistentes en el modelo: {missing}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
