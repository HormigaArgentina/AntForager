"""Ventana para ubicar el nido en un mapa (OpenStreetMap + vista satelital), con buscador de lugares.

Necesita internet. Si no hay, se pueden seguir cargando las coordenadas a mano o pegarlas.
"""
import json
import re
import urllib.parse
import urllib.request

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QVBoxLayout)

HTML = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#m{height:100%;margin:0}</style></head><body><div id="m"></div><script>
var osm=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap'});
var sat=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Esri World Imagery'});
var map=L.map('m',{layers:[osm]}).setView([__LAT__,__LON__],__ZOOM__);
L.control.layers({'Mapa':osm,'Satélite':sat}).addTo(map);
window.sel=null; var marker=null;
function setPos(lat,lon,zoom){
  window.sel=[lat,lon];
  if(marker){marker.setLatLng([lat,lon]);}
  else{marker=L.marker([lat,lon],{draggable:true}).addTo(map);
       marker.on('dragend',function(e){var p=e.target.getLatLng();window.sel=[p.lat,p.lng];});}
  if(zoom){map.setView([lat,lon],zoom);}
}
map.on('click',function(e){setPos(e.latlng.lat,e.latlng.lng,null);});
__INIT__
</script></body></html>"""


def parse_coords(text):
    """Acepta '-31.743, -60.515', '-31,743 -60,515', '31.8 S, 60.5 W' (S y W/O = negativo), etc.
    Devuelve (lat, lon) o None."""
    if re.search(r"[°º]\s*\d|['\u2032\"]", text):
        return None  # grados/minutos/segundos: ambiguo, no se admite (usar decimales)
    found = re.findall(r"(-?\d+(?:[.,]\d+)?)\s*°?\s*([NSEWOnsewo])?(?![A-Za-z])",
                       text.replace("\u2212", "-"))
    if len(found) < 2:
        return None
    vals = []
    for num, hemi in found[:2]:
        v = float(num.replace(",", "."))
        if hemi.upper() in ("S", "W", "O"):
            v = -abs(v)
        vals.append(v)
    lat, lon = vals
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def geocode(query, timeout=10):
    """Busca un lugar con Nominatim (OpenStreetMap). Devuelve (lat, lon, nombre) o None."""
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "AntForager/0.1 (research software)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", query)


class MapDialog(QDialog):
    def __init__(self, parent=None, lat=None, lon=None):
        super().__init__(parent)
        self.setWindowTitle("Ubicar el nido en el mapa")
        self.resize(900, 650)
        self.result_coords = None
        lay = QVBoxLayout(self)

        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar lugar (ej. 'Oro Verde, Entre Ríos') ...")
        self.search.returnPressed.connect(self.do_search)
        b = QPushButton("Buscar")
        b.clicked.connect(self.do_search)
        row.addWidget(self.search, 1)
        row.addWidget(b)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        self.paste = QLineEdit()
        self.paste.setPlaceholderText("O pegá coordenadas (ej. copiadas de Google Maps: -31.8, -60.5) y Enter")
        self.paste.returnPressed.connect(self.do_paste)
        row2.addWidget(self.paste, 1)
        lay.addLayout(row2)

        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            lay.addWidget(QLabel("No está disponible el componente de mapa (QtWebEngine). "
                                 "Usá el campo de arriba para pegar coordenadas."))
            self.web = None
        else:
            self.web = QWebEngineView()
            has = lat is not None and lon is not None
            init = f"setPos({lat},{lon},15);" if has else ""
            html = (HTML.replace("__LAT__", str(lat if has else -32.0))
                        .replace("__LON__", str(lon if has else -60.0))
                        .replace("__ZOOM__", "15" if has else "5")
                        .replace("__INIT__", init))
            self.web.setHtml(html, QUrl("https://antforager.local/"))
            lay.addWidget(self.web, 1)

        self.coord_label = QLabel("Hacé clic en el mapa para marcar el nido (se puede arrastrar el marcador).")
        lay.addWidget(self.coord_label)
        btns = QHBoxLayout()
        ok = QPushButton("Usar esta ubicación")
        ok.clicked.connect(self.accept_location)
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)

        self._sel = (lat, lon) if lat is not None and lon is not None else None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        if self.web:
            self.timer.start(400)

    # --- interacción con el mapa ---
    def _poll(self):
        self.web.page().runJavaScript("JSON.stringify(window.sel||null)", self._got_sel)

    def _got_sel(self, value):
        try:
            sel = json.loads(value) if value else None
        except (TypeError, ValueError):
            sel = None
        if sel:
            self._sel = (sel[0], sel[1])
            self.coord_label.setText(f"Ubicación marcada: {sel[0]:.6f}, {sel[1]:.6f}")

    def _go(self, lat, lon, zoom=15):
        self._sel = (lat, lon)
        self.coord_label.setText(f"Ubicación marcada: {lat:.6f}, {lon:.6f}")
        if self.web:
            self.web.page().runJavaScript(f"setPos({lat},{lon},{zoom});")

    def do_search(self):
        q = self.search.text().strip()
        if not q:
            return
        c = parse_coords(q)
        if c and re.fullmatch(r"[-−\d.,;\s°NSEWOnsewo]+", q):
            return self._go(*c)
        try:
            r = geocode(q)
        except Exception as e:
            QMessageBox.warning(self, "AntForager", f"No se pudo buscar (¿hay internet?).\n{e}")
            return
        if r is None:
            QMessageBox.information(self, "AntForager", "No se encontró ese lugar. Probá con otro nombre.")
            return
        self._go(r[0], r[1], 14)
        self.coord_label.setText(f"{r[2]}\n{r[0]:.6f}, {r[1]:.6f}")

    def do_paste(self):
        c = parse_coords(self.paste.text())
        if c is None:
            QMessageBox.information(self, "AntForager", "No pude leer las coordenadas. Formato: -31.8, -60.5")
            return
        self._go(*c)

    def accept_location(self):
        if self._sel is None:
            QMessageBox.information(self, "AntForager", "Marcá primero una ubicación en el mapa.")
            return
        self.result_coords = self._sel
        self.accept()
