from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget, QAbstractItemView)

from ..project import list_video_files, probe_video

COLS = ["Archivo", "Inicio (según nombre)", "Resolución", "fps", "Duración (min)"]


class VideosPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.videos = []
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.label = QLabel("<h2>Videos</h2>")
        btn = QPushButton("Elegir carpeta de videos...")
        btn.clicked.connect(self.choose)
        top.addWidget(self.label, 1)
        top.addWidget(btn)
        lay.addLayout(top)
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 380)
        self.table.cellDoubleClicked.connect(self.open_in_viewer)
        lay.addWidget(self.table)
        lay.addWidget(QLabel("Doble clic en un video para verlo en el Visor. Los videos no se copian: "
                             "se leen desde la carpeta elegida (por ejemplo, la de Drive o Dropbox)."))

    def refresh(self):
        p = self.win.project
        self.setEnabled(p is not None)
        if p is None:
            return
        self.label.setText(f"<h2>Videos</h2><p>{p.videos_dir or '(sin carpeta elegida)'}</p>")
        self.load(p.videos_dir)

    def choose(self):
        p = self.win.project
        folder = QFileDialog.getExistingDirectory(self, "Carpeta con los videos")
        if folder:
            p.videos_dir = folder
            p.save()
            self.refresh()

    def load(self, folder):
        self.videos = []
        self.table.setRowCount(0)
        if not folder:
            return
        files = list_video_files(folder)
        self.win.statusBar().showMessage(f"Leyendo {len(files)} videos...")
        for f in files:
            v = probe_video(f)
            self.videos.append(v)
            r = self.table.rowCount()
            self.table.insertRow(r)
            vals = [str(f.relative_to(folder)), v.start.strftime("%Y-%m-%d %H:%M:%S") if v.start else "?",
                    f"{v.width}x{v.height}", f"{v.fps:.1f}", f"{v.duration_s / 60:.1f}"]
            for c, t in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(t))
        self.win.statusBar().showMessage(f"{len(files)} videos.", 4000)

    def open_in_viewer(self, row, _col):
        if 0 <= row < len(self.videos):
            self.win.page_viewer.load_video(self.videos[row].path)
            self.win.nav.setCurrentRow(2)
