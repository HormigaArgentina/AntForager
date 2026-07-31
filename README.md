# AntForager

Software para analizar el comportamiento forrajero de hormigas cortadoras de hojas a partir de video: detecta cada hormiga que transita por un camino, la sigue, y determina si entra o sale del hormiguero cargada (hoja, palo, resto vegetal) o descargada.

## Origen y créditos

AntForager parte del código de **AntTracker**, desarrollado por Francisco Sturniolo ([repositorio original](https://github.com/fd-sturniolo/AntTracker)) y usado en el trabajo:

> "AntTracker: A low-cost and efficient computer vision approach to research leaf-cutter ants behavior", J. Sabattini, F. Sturniolo, M. Bollazzi y L. Bugnon (*Smart Agricultural Technology*, 2023).

Ese repositorio queda **congelado como la versión asociada al paper publicado** (ver [lbugnon/AntTracker](https://github.com/lbugnon/AntTracker), v1.0.10) y no se modifica acá. AntForager es un desarrollo nuevo que parte de ese motor de tracking para ampliar su alcance: nuevas especies/hábitats (incluyendo terrenos sin marcador de calibración), interfaz modernizada y un panel de resultados con salidas gráficas.

El README original de AntTracker se conserva sin cambios en [`docs/README_AntTracker_original.md`](docs/README_AntTracker_original.md).

También se evaluó como base alternativa el proyecto **Antnalyzer** (Quiroga y Vinzón, UTN FRP, tesis co-dirigida por Julián Sabattini) — ver `docs/plan_trabajo_antnalyzer_anttracker.docx` para la comparación completa y la justificación de por qué se eligió AntTracker como punto de partida.

## Estructura heredada de AntTracker

- `ant_tracker/tracker` — motor de segmentación, tracking y clasificación de carga (sin dependencias de GUI).
- `ant_tracker/tracker_gui` — interfaz de usuario actual (PySimpleGUI) y exportación de resultados a Excel.
- `ant_tracker/labeler` — herramienta de etiquetado semi-supervisado (PyQt5/pyforms), útil para generar datos de entrenamiento/validación.

## Estado del proyecto

En desarrollo activo. Ver `docs/plan_trabajo_antnalyzer_anttracker.docx` para el roadmap por fases (dashboard de resultados, modernización de GUI, actualización de dependencias, empaquetado).

## Instalación (heredada de AntTracker, en revisión)

Requisitos originales: `git`, `conda` (Miniconda o Anaconda), [`MakeNSIS`](https://nsis.sourceforge.io/Download). Ver `docs/README_AntTracker_original.md` para los pasos completos — se están revisando porque varias dependencias (Python 3.8, TensorFlow-Lite, NumPy 1.18) están desactualizadas.
