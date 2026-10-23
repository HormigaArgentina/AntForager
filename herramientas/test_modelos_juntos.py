"""Corre el detector de hormigas y el de carga sobre los mismos cuadros y dibuja ambos.
Una hormiga se marca CARGADA (rojo) si una detección de carga se superpone con su caja;
si no, DESCARGADA (verde). Carga sin hormiga asociada se dibuja en amarillo (posible falso positivo
o carga suelta).

Uso: python test_modelos_juntos.py VIDEO HORMIGAS.pt CARGA.pt [N_FRAMES] [SALIDA]
"""
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

video, w_ants, w_load = map(Path, sys.argv[1:4])
n = int(sys.argv[4]) if len(sys.argv) > 4 else 12
out = Path(sys.argv[5]) if len(sys.argv) > 5 else Path("salida_test_juntos")
out.mkdir(parents=True, exist_ok=True)
CONF_ANT, CONF_LOAD, MARGIN = 0.4, 0.5, 6

ants_m, load_m = YOLO(str(w_ants)), YOLO(str(w_load))
print("Clases hormigas:", ants_m.names, "| clases carga:", load_m.names)


def boxes(res):
    return [] if res.boxes is None else [tuple(b) for b in res.boxes.xyxy.cpu().numpy().tolist()]


def overlap(a, b, m=MARGIN):
    return not (a[2] < b[0] - m or a[0] > b[2] + m or a[3] < b[1] - m or a[1] > b[3] + m)


cap = cv2.VideoCapture(str(video))
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
tot_a = tot_c = 0
for i in range(n):
    idx = int((i + 0.5) * total / n)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    if not ok:
        continue
    A = boxes(ants_m.predict(frame, conf=CONF_ANT, verbose=False)[0])
    L = boxes(load_m.predict(frame, conf=CONF_LOAD, verbose=False)[0])
    used = set()
    loaded = 0
    for a in A:
        hit = [j for j, l in enumerate(L) if overlap(a, l)]
        used.update(hit)
        color = (0, 0, 255) if hit else (0, 200, 0)
        loaded += bool(hit)
        cv2.rectangle(frame, (int(a[0]), int(a[1])), (int(a[2]), int(a[3])), color, 1)
    for j, l in enumerate(L):
        if j not in used:
            cv2.rectangle(frame, (int(l[0]), int(l[1])), (int(l[2]), int(l[3])), (0, 255, 255), 1)
    tot_a += len(A)
    tot_c += loaded
    cv2.putText(frame, f"hormigas {len(A)}  cargadas {loaded}  carga sin hormiga {len(L) - len(used)}",
                (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imwrite(str(out / f"frame_{idx:07d}.jpg"), frame)
    print(f"frame {idx}: {len(A)} hormigas, {loaded} cargadas, {len(L) - len(used)} cargas sin hormiga")
print(f"\nTotal: {tot_a} hormigas, {tot_c} cargadas ({100 * tot_c / max(tot_a, 1):.0f}%)")
print("Imágenes en:", out.resolve())
