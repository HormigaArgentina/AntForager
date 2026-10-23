from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QFileDialog, QLabel, QListWidget, QMainWindow, QMessageBox,
                               QSplitter, QStackedWidget, QVBoxLayout, QWidget)

from ..project import Project
from .project_page import ProjectPage
from .videos_page import VideosPage
from .viewer_page import ViewerPage


class PlaceholderPage(QWidget):
    def __init__(self, title, text):
        super().__init__()
        lay = QVBoxLayout(self)
        t = QLabel(f"<h2>{title}</h2><p>{text}</p>")
        t.setWordWrap(True)
        t.setAlignment(Qt.AlignTop)
        lay.addWidget(t)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AntForager")
        self.resize(1200, 760)
        self.project: Project | None = None

        self.nav = QListWidget()
        self.nav.setFixedWidth(170)
        self.stack = QStackedWidget()
        self.page_project = ProjectPage(self)
        self.page_videos = VideosPage(self)
        self.page_viewer = ViewerPage(self)
        pages = [
            ("Proyecto", self.page_project),
            ("Videos", self.page_videos),
            ("Visor", self.page_viewer),
            ("Procesar", PlaceholderPage("Procesar", "Cola de procesamiento: copia cada fragmento a una carpeta temporal, "
                                                     "lo procesa y guarda los datos crudos en el proyecto. (Próxima etapa.)")),
            ("Resultados", PlaceholderPage("Resultados", "Tablas y gráficos de líneas dinámicos sobre los datos crudos, "
                                                         "con intervalo elegido por el investigador. (Fase 1.)")),
            ("Etiquetado", PlaceholderPage("Etiquetado", "Etiquetado asistido por modelo para armar datasets propios. (Fase 3.)")),
        ]
        for name, page in pages:
            self.nav.addItem(name)
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self._on_nav)
        self.nav.setCurrentRow(0)

        split = QSplitter()
        split.addWidget(self.nav)
        split.addWidget(self.stack)
        split.setStretchFactor(1, 1)
        self.setCentralWidget(split)

        self._build_menu()
        self.statusBar().showMessage("Creá o abrí un proyecto para empezar.")

    def _build_menu(self):
        m = self.menuBar().addMenu("&Proyecto")
        for text, fn in (("Nuevo proyecto...", self.new_project), ("Abrir proyecto...", self.open_project)):
            a = QAction(text, self)
            a.triggered.connect(fn)
            m.addAction(a)

    def _on_nav(self, row):
        self.stack.setCurrentIndex(row)
        w = self.stack.currentWidget()
        if hasattr(w, "refresh"):
            w.refresh()

    # --- proyectos ---
    def new_project(self):
        folder = QFileDialog.getExistingDirectory(self, "Elegí (o creá) la carpeta del proyecto")
        if not folder:
            return
        if (Path(folder) / Project.FILE).exists():
            QMessageBox.information(self, "AntForager", "Esa carpeta ya es un proyecto; se abrirá.")
            return self.set_project(Project.load(Path(folder)))
        self.set_project(Project.create(Path(folder), name=Path(folder).name))

    def open_project(self):
        folder = QFileDialog.getExistingDirectory(self, "Abrir carpeta de proyecto")
        if not folder:
            return
        try:
            self.set_project(Project.load(Path(folder)))
        except (OSError, ValueError):
            QMessageBox.warning(self, "AntForager", "Esa carpeta no tiene un proyecto.json válido.")

    def set_project(self, project: Project):
        self.project = project
        self.setWindowTitle(f"AntForager - {project.name}")
        self.statusBar().showMessage(f"Proyecto: {project.path}")
        for page in (self.page_project, self.page_videos, self.page_viewer):
            page.refresh()
        self.nav.setCurrentRow(0)
