import pathlib
from ant_tracker.tracker.main import main
from ant_tracker.tracker.info import TracksInfo

VIDEO = pathlib.Path("clip_test.mp4")
OUTDIR = pathlib.Path("data")
OUTDIR.mkdir(exist_ok=True)

main(VIDEO, "high", 1, False, str(OUTDIR))

trk_files = sorted(OUTDIR.glob("*.trk"))
info = TracksInfo.load(trk_files[-1])

print(f"\n--- Resultado ---")
print(f"Hormigas (tracks) detectadas: {len(info.tracks)}")
for t in info.tracks:
    origen, destino = t.direction_of_travel(info.video_shape)
    print(f"  Track {t.id}: {len(t.blobs)} frames, {origen.name} -> {destino.name}")
