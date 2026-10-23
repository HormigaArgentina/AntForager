"""Fotoperíodo: posición del sol y fase de luz ("luz") para cualquier momento y lugar.

Se calcula con las ecuaciones solares de NOAA (precisión de ~1 minuto en horarios de salida y
puesta, suficiente para ecología). No necesita internet ni librerías externas.

Fases (por la altura del sol sobre el horizonte, h):
    "luz"                    h > -0.833°     (día; incluye refracción y tamaño del disco solar)
    "crepúsculo matutino"    entre -0.833° y ``twilight_deg``, antes del mediodía solar
    "crepúsculo vespertino"  entre -0.833° y ``twilight_deg``, después del mediodía solar
    "oscuro"                 h <= twilight_deg

``twilight_deg`` define dónde termina el crepúsculo (decisión del investigador):
    -6  = crepúsculo civil, -12 = náutico, -18 = astronómico (noche completa). Por defecto -18.

Uso por línea de comandos:
    python -m antforager.photoperiod LAT LON AAAA-MM-DD [zona_horaria] [twilight_deg]
"""
import math
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

SUN_LIMIT_DEG = -0.833
PHASES = ("oscuro", "crepúsculo matutino", "luz", "crepúsculo vespertino")


def _julian_day(dt_utc: datetime) -> float:
    dt = dt_utc.astimezone(timezone.utc)
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + (dt.minute + (dt.second + dt.microsecond / 1e6) / 60) / 60) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def solar_position(dt_utc: datetime, lat: float, lon: float) -> Tuple[float, float, float]:
    """(elevación sobre el horizonte en grados, declinación en grados, ecuación del tiempo en minutos)."""
    jc = (_julian_day(dt_utc) - 2451545.0) / 36525.0
    geom_mean_long = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    geom_mean_anom = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    ecc = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    ma = math.radians(geom_mean_anom)
    eq_center = (math.sin(ma) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
                 + math.sin(2 * ma) * (0.019993 - 0.000101 * jc)
                 + math.sin(3 * ma) * 0.000289)
    true_long = geom_mean_long + eq_center
    omega = 125.04 - 1934.136 * jc
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    mean_obliq = 23 + (26 + ((21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813)))) / 60) / 60
    obliq = mean_obliq + 0.00256 * math.cos(math.radians(omega))
    decl = math.degrees(math.asin(math.sin(math.radians(obliq)) * math.sin(math.radians(app_long))))
    y = math.tan(math.radians(obliq / 2)) ** 2
    lm = math.radians(geom_mean_long)
    eq_time = 4 * math.degrees(y * math.sin(2 * lm) - 2 * ecc * math.sin(ma)
                               + 4 * ecc * y * math.sin(ma) * math.cos(2 * lm)
                               - 0.5 * y * y * math.sin(4 * lm) - 1.25 * ecc * ecc * math.sin(2 * ma))
    dt = dt_utc.astimezone(timezone.utc)
    minutes = dt.hour * 60 + dt.minute + dt.second / 60
    true_solar_time = (minutes + eq_time + 4 * lon) % 1440
    hour_angle = true_solar_time / 4 - 180
    if hour_angle < -180:
        hour_angle += 360
    la, de, ha = math.radians(lat), math.radians(decl), math.radians(hour_angle)
    cos_zen = math.sin(la) * math.sin(de) + math.cos(la) * math.cos(de) * math.cos(ha)
    elevation = 90 - math.degrees(math.acos(max(-1.0, min(1.0, cos_zen))))
    return elevation, decl, eq_time


def sun_elevation(dt_utc: datetime, lat: float, lon: float) -> float:
    return solar_position(dt_utc, lat, lon)[0]


def _to_utc(dt: datetime, tz_name: Optional[str]) -> datetime:
    """Si ``dt`` no tiene zona horaria, se interpreta en ``tz_name`` (hora local del video)."""
    if dt.tzinfo is None:
        if not tz_name:
            raise ValueError("Falta la zona horaria para interpretar una hora sin zona.")
        from zoneinfo import ZoneInfo
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    return dt.astimezone(timezone.utc)


def light_phase(dt: datetime, lat: float, lon: float, tz_name: Optional[str] = None,
                twilight_deg: float = -18.0) -> str:
    """Una de ``PHASES`` para el momento ``dt`` (hora local si no tiene zona; ver ``tz_name``)."""
    utc = _to_utc(dt, tz_name)
    elev, _, eqt = solar_position(utc, lat, lon)
    if elev > SUN_LIMIT_DEG:
        return "luz"
    if elev <= twilight_deg:
        return "oscuro"
    # mañana o tarde: comparar con el mediodía solar (hora solar verdadera < o > 720 min)
    minutes = utc.hour * 60 + utc.minute + utc.second / 60
    tst = (minutes + eqt + 4 * lon) % 1440
    return "crepúsculo matutino" if tst < 720 else "crepúsculo vespertino"


def day_events(day: date, lat: float, lon: float, tz_name: str, twilight_deg: float = -18.0) -> Dict[str, Optional[datetime]]:
    """Hora local de: inicio de crepúsculo matutino, salida del sol, puesta, fin de crepúsculo vespertino
    (None si no ocurre ese día, por ejemplo cerca de los polos). Resolución de 1 minuto."""
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(tz_name)
    t0 = datetime(day.year, day.month, day.day, tzinfo=tz)
    prev = None
    ev: Dict[str, Optional[datetime]] = {"inicio_crepusculo_matutino": None, "salida_sol": None,
                                         "puesta_sol": None, "fin_crepusculo_vespertino": None}
    for k in range(0, 24 * 60 + 1):
        t = t0 + timedelta(minutes=k)
        e = sun_elevation(t.astimezone(timezone.utc), lat, lon)
        if prev is not None:
            if prev <= twilight_deg < e:
                ev["inicio_crepusculo_matutino"] = t
            if prev <= SUN_LIMIT_DEG < e:
                ev["salida_sol"] = t
            if prev > SUN_LIMIT_DEG >= e:
                ev["puesta_sol"] = t
            if prev > twilight_deg >= e:
                ev["fin_crepusculo_vespertino"] = t
        prev = e
    return ev


def _main(argv):
    if len(argv) < 4:
        print(__doc__)
        return
    lat, lon, day = float(argv[1]), float(argv[2]), date.fromisoformat(argv[3])
    tz = argv[4] if len(argv) > 4 else "America/Argentina/Buenos_Aires"
    tw = float(argv[5]) if len(argv) > 5 else -18.0
    for k, v in day_events(day, lat, lon, tz, tw).items():
        print(f"{k:28s} {v.strftime('%H:%M') if v else '-'}")


if __name__ == "__main__":
    _main(sys.argv)
