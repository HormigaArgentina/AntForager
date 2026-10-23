"""Genera hojas de validación: recortes ampliados de hormigas detectadas, numerados, con el
veredicto del modelo (rojo = CARGADA, verde = descargada). El investigador anota los números
donde el modelo se equivocó. Escribe además validacion.csv con el veredicto de cada recorte.

Uso: python hoja_validacion.py VIDEO HORMIGAS.pt CARGA.pt [N_RECORTES=60] [SALIDA]
"""
import csv
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

video, w_ants, w_load = map(Path, sys.argv[1:4])
n = int(sys.argv[4]) if len(sys.argv) > 4 else 60
out = Path(sys.argv[5]) if len(sys.argv) > 5 else Path("hoja_validacion")
out.mkdir(parents=True, exist_ok=True)
CONF_ANT, CONF_LOAD, MARGIN, PAD, ZOOM, COLS, TILE = 0.4, 0.5, 6, 18, 5, 6, 150
random.seed(1)

ants_m, load_m = YOLO(str(w_ants)), YOLO(str(w_load))
cap = cv2.VideoCapture(str(video))
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))


def boxes(res):
    return [] if res.boxes is None else res.boxes.xyxy.cpu().numpy().tolist()


def overlap(a, b):
    return not (a[2] < b[0] - MARGIN or a[0] > b[2] + MARGIN or a[3] < b[1] - MARGIN or a[1] > b[3] + MARGIN)


items = []
for idx in sorted(random.sample(range(total), 120)):
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, f = cap.read()
    if not ok:
        continue
    A = boxes(ants_m.predict(f, conf=CONF_ANT, verbose=False)[0])
    L = boxes(load_m.predict(f, conf=CONF_LOAD, verbose=False)[0])
    for a in A:
        items.append((idx, f, a, any(overlap(a, l) for l in L)))
    if len(items) >= n * 3:
        break
random.shuffle(items)
items = items[:n]

tiles, rows = [], []
for k, (idx, f, a, loaded) in enumerate(items, 1):
    x0, y0, x1, y1 = [int(v) for v in a]
    h, w = f.shape[:2]
    crop = f[max(y0 - PAD, 0):min(y1 + PAD, h), max(x0 - PAD, 0):min(x1 + PAD, w)]
    crop = cv2.resize(crop, None, fx=ZOOM, fy=ZOOM, interpolation=cv2.INTER_CUBIC)
    s = TILE / max(crop.shape[:2])
    crop = cv2.resize(crop, None, fx=s, fy=s)
    tile = np.zeros((TILE + 22, TILE, 3), np.uint8)
    tile[22:22 + crop.shape[0], :crop.shape[1]] = crop
    color = (0, 0, 255) if loaded else (0, 200, 0)
    cv2.rectangle(tile, (0, 0), (TILE - 1, TILE + 21), color, 2)
    cv2.putText(tile, f"#{k} {'CARGADA' if loaded else 'descargada'}", (4, 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
    tiles.append(tile)
    rows.append([k, idx, int(x0), int(y0), int(x1), int(y1), "cargada" if loaded else "descargada"])

per_sheet = COLS * 5
for s in range(0, len(tiles), per_sheet):
    chunk = tiles[s:s + per_sheet]
    while len(chunk) % COLS:
        chunk.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(chunk[i:i + COLS]) for i in range(0, len(chunk), COLS)])
    cv2.imwrite(str(out / f"hoja_{s // per_sheet + 1}.jpg"), sheet)

with open(out / "validacion.csv", "w", newline="") as fh:
    wr = csv.writer(fh)
    wr.writerow(["n", "frame", "x0", "y0", "x1", "y1", "modelo"])
    wr.writerows(rows)
print(f"{len(tiles)} recortes -> {out.resolve()}  (modelo: {sum(r[-1]=='cargada' for r in rows)} cargadas)")
