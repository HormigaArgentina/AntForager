"""Prueba rápida del modelo YOLOv8n-seg 'leaf' sobre un video.
Toma N frames repartidos a lo largo del video, corre el modelo y guarda
imágenes anotadas en la carpeta de salida + un resumen de detecciones.

Uso:
    python test_modelo_leaf.py VIDEO.mp4 PESOS.pt [N_FRAMES] [CARPETA_SALIDA]
"""
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

video = Path(sys.argv[1])
pesos = Path(sys.argv[2])
n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
out = Path(sys.argv[4]) if len(sys.argv) > 4 else Path("salida_test_leaf")
out.mkdir(parents=True, exist_ok=True)

model = YOLO(str(pesos))
print("Clases del modelo:", model.names)

cap = cv2.VideoCapture(str(video))
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
print(f"Video: {total} frames, {fps:.1f} fps, {total / fps / 60:.1f} min")

conteos = []
for i in range(n):
    idx = int((i + 0.5) * total / n)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    if not ok:
        continue
    res = model.predict(frame, conf=0.25, verbose=False)[0]
    k = 0 if res.boxes is None else len(res.boxes)
    conteos.append(k)
    cv2.imwrite(str(out / f"frame_{idx:07d}_{k}det.jpg"), res.plot())
    print(f"frame {idx}: {k} detecciones")

if conteos:
    print(f"\nPromedio: {sum(conteos) / len(conteos):.1f} detecciones/frame")
print(f"Imágenes anotadas en: {out.resolve()}")
