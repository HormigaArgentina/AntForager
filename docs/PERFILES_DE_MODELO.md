# Perfiles de modelo (especie / región / escenario)

AntForager no trae un modelo fijo: cada **perfil** es una carpeta con sus pesos y un `profile.json`.

## Agregar un perfil propio
1. Entrená tu modelo (YOLOv8 segmentación o cajas) con tus imágenes, p. ej. en Roboflow. Una clase debe representar "hormiga con carga" (puede llamarse como quieras).
2. Creá una carpeta en `~/AntForager/models/mi_especie/` con tu `weights.pt` y un `profile.json` (copiá y editá el de `models/acromyrmex_lundi/`).
3. Verificá: `python -m ant_tracker.detection check mi_especie`
4. Activalo: `python -m ant_tracker.detection activate mi_especie`

## Comandos
- `python -m ant_tracker.detection list` — perfiles disponibles y activo
- `python -m ant_tracker.detection activate <id>`
- `python -m ant_tracker.detection check <id>` — valida clases y pesos

## Campos de profile.json
`id`, `name`, `species`, `kind` (`yolo_seg` | `yolo_det` | `tflite_legacy`), `weights`, `load_classes` (clases que significan "lleva carga"), `conf` (umbral de confianza), `imgsz`, `mode` (`frame` | `crop`), `n_frames`, `decision`, y metadatos libres (`author`, `trained_on`, `notes`).

## Importante
`conf` y `decision` son valores iniciales: calibralos contra hormigas verificadas a mano en TU escenario antes de usar los resultados en un análisis.
Prioridad de búsqueda: variable `ANTFORAGER_MODELS` > `~/AntForager/models` > `models/` del repo.
