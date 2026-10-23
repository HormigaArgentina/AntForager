from PySide6.QtWidgets import (QHBoxLayout, QComboBox, QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QPushButton,
                               QWidget, QVBoxLayout, QPlainTextEdit)

from ..project import Project
from .map_dialog import MapDialog


class ProjectPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        self.info = QLabel("<h2>Proyecto</h2><p>Creá un proyecto nuevo o abrí uno existente.</p>")
        lay.addWidget(self.info)
        bar = QHBoxLayout()
        b_new = QPushButton("Nuevo proyecto...")
        b_open = QPushButton("Abrir proyecto...")
        b_new.clicked.connect(win.new_project)
        b_open.clicked.connect(win.open_project)
        bar.addWidget(b_new)
        bar.addWidget(b_open)
        bar.addStretch()
        lay.addLayout(bar)
        self.box = QWidget()
        box_lay = QVBoxLayout(self.box)
        box_lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.box)
        form = QFormLayout()
        self.name = QLineEdit()
        self.place = QLineEdit()
        self.species = QLineEdit()
        self.lat = QDoubleSpinBox()
        self.lon = QDoubleSpinBox()
        for sb, lo, hi in ((self.lat, -90, 90), (self.lon, -180, 180)):
            sb.setRange(lo, hi)
            sb.setDecimals(6)
        self.profile = QComboBox()
        self.tz = QLineEdit()
        self.twi = QComboBox()
        for deg, txt in ((-6.0, "Civil (-6°)"), (-12.0, "Náutico (-12°)"), (-18.0, "Astronómico (-18°), noche completa")):
            self.twi.addItem(txt, deg)
        self.mm = QDoubleSpinBox()
        self.mm.setDecimals(5)
        self.mm.setRange(0, 100)
        self.mm.setSpecialValueText("sin calibrar")
        self.notes = QPlainTextEdit()
        self.notes.setFixedHeight(70)
        form.addRow("Nombre", self.name)
        form.addRow("Lugar", self.place)
        form.addRow("Especie", self.species)
        form.addRow("Latitud del nido (°)", self.lat)
        form.addRow("Longitud del nido (°)", self.lon)
        b_map = QPushButton("Ubicar en el mapa / buscar lugar...")
        b_map.clicked.connect(self.pick_on_map)
        form.addRow("", b_map)
        form.addRow("Zona horaria de los videos", self.tz)
        form.addRow("El crepúsculo termina con el sol en", self.twi)
        form.addRow("Perfil de modelo", self.profile)
        form.addRow("Escala (mm por píxel)", self.mm)
        form.addRow("Notas", self.notes)
        box_lay.addLayout(form)
        btn = QPushButton("Guardar")
        btn.clicked.connect(self.save)
        box_lay.addWidget(btn)
        lay.addStretch()
        self.box.setEnabled(False)

    def refresh(self):
        p = self.win.project
        self.box.setEnabled(p is not None)
        if p is None:
            return
        self.info.setText(f"<h2>{p.name}</h2><p>{p.path}</p>")
        self.name.setText(p.name)
        self.place.setText(p.place)
        self.species.setText(p.species)
        self.lat.setValue(p.lat or 0.0)
        self.lon.setValue(p.lon or 0.0)
        self.mm.setValue(p.mm_per_px or 0.0)
        self.tz.setText(p.timezone)
        self.twi.setCurrentIndex(max(self.twi.findData(p.twilight_deg), 0))
        self.notes.setPlainText(p.notes)
        self.profile.clear()
        try:
            from ant_tracker.detection import list_profiles
            profs = list_profiles()
        except Exception:
            profs = {}
        for pid, prof in profs.items():
            self.profile.addItem(f"{prof.name}  [{pid}]", pid)
        i = self.profile.findData(p.profile_id)
        if i >= 0:
            self.profile.setCurrentIndex(i)

    def pick_on_map(self):
        dlg = MapDialog(self, self.lat.value() or None, self.lon.value() or None)
        if dlg.exec() and dlg.result_coords:
            self.lat.setValue(dlg.result_coords[0])
            self.lon.setValue(dlg.result_coords[1])

    def save(self):
        p = self.win.project
        p.name = self.name.text().strip() or p.name
        p.place = self.place.text().strip()
        p.species = self.species.text().strip()
        p.lat = self.lat.value() or None
        p.lon = self.lon.value() or None
        p.mm_per_px = self.mm.value() or None
        tz = self.tz.text().strip() or p.timezone
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(tz)
        except Exception:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "AntForager", f"Zona horaria desconocida: {tz}\nEjemplo: America/Argentina/Buenos_Aires")
            return
        p.timezone = tz
        p.twilight_deg = self.twi.currentData()
        p.notes = self.notes.toPlainText()
        if self.profile.currentData():
            p.profile_id = self.profile.currentData()
        p.save()
        self.win.setWindowTitle(f"AntForager - {p.name}")
        self.win.statusBar().showMessage("Proyecto guardado.", 4000)
