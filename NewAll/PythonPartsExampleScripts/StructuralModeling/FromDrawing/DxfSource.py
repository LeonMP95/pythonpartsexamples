"""Sursă de planșe: citirea directă a unui fișier DXF într-un Drawing2D

Folosește biblioteca ezdxf (licență MIT), importată doar la apelul read_dxf, astfel încât
restul proiectului funcționează și fără ea. Fișierul DXF este tratat ca date: se citesc doar
entitățile geometrice, nu se execută nimic din fișier.

Entități suportate (din modelspace): LINE, LWPOLYLINE, POLYLINE (2D/3D), CIRCLE, ARC, ELLIPSE,
SPLINE, HATCH, INSERT (explodat recursiv). Restul sunt ignorate și numărate într-un avertisment.
Coordonatele Z se ignoră (proiecție în planul XY); rezultatul este în mm.
"""

from __future__ import annotations

import math
import os

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from StructuralModeling.FromDrawing.Model2D import Drawing2D, Hatch2D, Point2, Polyline2D, Segment2D

MB = 1024 * 1024
DXF_EXTENSION = ".dxf"

INSUNITS_UNITLESS = 0
INSUNITS_MM       = 4

DUPLICATE_TOLERANCE_MM     = 1e-6     # puncte consecutive mai apropiate sunt considerate identice
MIN_SEGMENTS_FULL_CIRCLE   = 16       # număr minim de segmente pentru un cerc complet
MAX_SEGMENTS_PER_CURVE     = 10000    # limită de siguranță pentru discretizare
MAX_BLOCK_DEPTH            = 32       # adâncimea maximă a blocurilor imbricate
SPLINE_FRAME_VERTEX_FLAG   = 16       # vertex de control al unei polilinii netezite (se omite)
HATCH_PATH_EXTERNAL_FLAG   = 1        # cale externă a hașurii
MAX_ERROR_DETAIL_CHARS     = 200

BASE_LAYER = "0"

INSTALL_HINT = ("Biblioteca Python 'ezdxf' nu este instalată în interpretorul Allplan. "
                "Instalați-o cu unealta „Install Python Package” din PythonParts SDK "
                "(pachetul: ezdxf), apoi reporniți Allplan.")

XY = tuple[float, float]


class DxfSourceError(ValueError):
    """Fișier DXF care nu poate fi citit (lipsă, prea mare, corupt) sau parametri invalizi"""


# ----------------------------------------------------------------------------------------------
# Interfața publică
# ----------------------------------------------------------------------------------------------

def read_dxf(path                 : str,
             unit_to_mm           : float | None = None,
             max_file_size_mb     : float = 50.0,
             arc_segment_length_mm: float = 100.0) -> Drawing2D:
    """Citește entitățile 2D din modelspace-ul unui fișier DXF.

    Args:
        path:                  calea fișierului .dxf
        unit_to_mm:            factorul unitate desen -> mm; None = din header ($INSUNITS)
        max_file_size_mb:      mărimea maximă acceptată a fișierului [MB]
        arc_segment_length_mm: lungimea aproximativă a unui segment la discretizarea curbelor [mm]

    Returns:
        planșa 2D, cu coordonatele în mm

    Raises:
        DxfSourceError: fișier inexistent / prea mare / extensie greșită / corupt,
                        ezdxf lipsă sau parametri invalizi
    """
    _check_positive(max_file_size_mb, "max_file_size_mb")
    _check_positive(arc_segment_length_mm, "arc_segment_length_mm")

    if unit_to_mm is not None:
        _check_positive(unit_to_mm, "unit_to_mm")

    _check_file(path, max_file_size_mb)
    ezdxf = _import_ezdxf()
    doc   = _read_document(ezdxf, path)

    warnings: list[str] = []
    factor = unit_to_mm if unit_to_mm is not None else _unit_factor_from_header(doc, warnings)

    collector = _Collector(ezdxf, factor, arc_segment_length_mm / factor)

    for entity in doc.modelspace():
        collector.add(entity, None, 0)

    return collector.drawing(warnings)


# ----------------------------------------------------------------------------------------------
# Verificări și citire
# ----------------------------------------------------------------------------------------------

def _check_positive(value: float, name: str) -> None:
    """Eroare dacă parametrul nu este un număr finit pozitiv"""
    if not (isinstance(value, (int, float)) and math.isfinite(value) and value > 0):
        raise DxfSourceError(f"Parametrul {name} trebuie să fie un număr pozitiv (primit: {value!r}).")


def _check_file(path: str, max_file_size_mb: float) -> None:
    """Verifică existența, extensia și mărimea fișierului"""
    if not os.path.isfile(path):
        raise DxfSourceError(f"Fișierul DXF nu există: {path}")

    if os.path.splitext(path)[1].lower() != DXF_EXTENSION:
        raise DxfSourceError(f"Fișierul nu are extensia {DXF_EXTENSION}: {path}")

    size_mb = os.path.getsize(path) / MB

    if size_mb > max_file_size_mb:
        raise DxfSourceError(f"Fișierul DXF este prea mare ({size_mb:.1f} MB > {max_file_size_mb:g} MB): {path}")


def _import_ezdxf() -> Any:
    """Importă ezdxf la cerere; dacă lipsește, eroare cu instrucțiuni de instalare"""
    try:
        import ezdxf
    except ImportError as exc:
        raise DxfSourceError(INSTALL_HINT) from exc

    return ezdxf


def _read_document(ezdxf: Any, path: str) -> Any:
    """Citește documentul DXF; orice eroare de parsare devine DxfSourceError"""
    try:
        return ezdxf.readfile(path)
    except Exception as exc:     # fișier extern, neverificat: orice eroare a parserului e o eroare de fișier
        detail = str(exc)[:MAX_ERROR_DETAIL_CHARS]
        raise DxfSourceError(f"Fișierul DXF nu poate fi citit (corupt sau format nesuportat): "
                             f"{path}\nDetalii: {type(exc).__name__}: {detail}") from exc


def _unit_factor_from_header(doc: Any, warnings: list[str]) -> float:
    """Factorul unitate desen -> mm din $INSUNITS; mm cu avertisment dacă lipsește sau e necunoscut"""
    from ezdxf import units

    insunits = doc.header.get("$INSUNITS", INSUNITS_UNITLESS)

    if insunits == INSUNITS_UNITLESS:
        warnings.append("Fișierul DXF nu are unități ($INSUNITS lipsă sau 0); se presupune că desenul este în mm.")
        return 1.0

    try:
        return units.conversion_factor(insunits, INSUNITS_MM)
    except (KeyError, TypeError, ValueError):
        warnings.append(f"Unitățile DXF ($INSUNITS = {insunits}) nu sunt suportate; se presupune mm.")
        return 1.0


# ----------------------------------------------------------------------------------------------
# Geometrie (în unitățile desenului)
# ----------------------------------------------------------------------------------------------

def _segment_count(length: float, segment_length: float, sweep_rad: float) -> int:
    """Numărul de segmente pentru o curbă de lungimea dată și unghiul la centru dat"""
    by_length = math.ceil(length / segment_length) if segment_length > 0 else 1
    by_angle  = math.ceil(MIN_SEGMENTS_FULL_CIRCLE * abs(sweep_rad) / (2 * math.pi))
    return min(max(by_length, by_angle, 1), MAX_SEGMENTS_PER_CURVE)


def _arc_points(center: XY, radius: float, start_rad: float, sweep_rad: float,
                segment_length: float) -> list[XY]:
    """Punctele unui arc (inclusiv capetele); sweep > 0 = sens trigonometric"""
    count = _segment_count(radius * abs(sweep_rad), segment_length, sweep_rad)
    return [(center[0] + radius * math.cos(start_rad + sweep_rad * i / count),
             center[1] + radius * math.sin(start_rad + sweep_rad * i / count)) for i in range(count + 1)]


def _ccw_sweep(start_deg: float, end_deg: float) -> float:
    """Unghiul la centru în sens trigonometric de la start la end [rad]; 0 înseamnă cerc complet"""
    sweep = (end_deg - start_deg) % 360.0
    return math.radians(sweep if sweep > 0 else 360.0)


def _bulge_arc(start: XY, end: XY, bulge: float, segment_length: float) -> list[XY]:
    """Punctele arcului definit de bulge între două vârfuri (inclusiv capetele)"""
    chord = math.dist(start, end)

    if chord == 0 or bulge == 0:
        return [start, end]

    sweep    = 4 * math.atan(bulge)
    radius   = chord * (1 + bulge * bulge) / (4 * abs(bulge))
    sagitta  = abs(bulge) * chord / 2
    unit     = ((end[0] - start[0]) / chord, (end[1] - start[1]) / chord)
    offset   = (radius - sagitta) * math.copysign(1.0, bulge)
    center   = ((start[0] + end[0]) / 2 - unit[1] * offset, (start[1] + end[1]) / 2 + unit[0] * offset)
    start_ra = math.atan2(start[1] - center[1], start[0] - center[0])
    points   = _arc_points(center, radius, start_ra, sweep, segment_length)
    return [start, *points[1:-1], end]


def _bulge_polyline(vertices: Sequence[tuple[float, float, float]], closed: bool,
                    segment_length: float) -> list[XY]:
    """Punctele unei polilinii cu bulge-uri (x, y, bulge), cu arcele discretizate"""
    points: list[XY] = []
    count = len(vertices)
    spans = count if closed else count - 1

    for i in range(spans):
        x1, y1, bulge = vertices[i]
        x2, y2, _     = vertices[(i + 1) % count]
        points.extend(_bulge_arc((x1, y1), (x2, y2), bulge, segment_length)[:-1])

    if count and not closed:
        points.append((vertices[-1][0], vertices[-1][1]))

    return points if count > 1 else [(v[0], v[1]) for v in vertices]


def _ellipse_points(ellipse: Any, segment_length: float) -> list[Any]:
    """Punctele unei elipse ezdxf (ConstructionEllipse), inclusiv capetele"""
    major = ellipse.major_axis.magnitude
    minor = major * ellipse.ratio
    perimeter = math.pi * (3 * (major + minor) - math.sqrt((3 * major + minor) * (major + 3 * minor)))
    span  = ellipse.param_span
    count = _segment_count(perimeter * span / (2 * math.pi), segment_length, span)
    return list(ellipse.vertices(ellipse.params(count + 1)))


def _spline_points(bspline: Any, segment_length: float) -> list[Any]:
    """Punctele unui B-spline ezdxf; lungimea se estimează din poligonul de control"""
    control = list(bspline.control_points)
    length  = sum(p1.distance(p2) for p1, p2 in zip(control, control[1:]))
    return list(bspline.approximate(_segment_count(length, segment_length, 0.0)))


def _ocs_to_wcs(entity: Any, points: Iterable[XY], elevation: float) -> list[XY]:
    """Transformă puncte din OCS-ul entității în WCS și le proiectează în planul XY"""
    from ezdxf.math import Vec3

    ocs = entity.ocs()
    return [(p.x, p.y) for p in ocs.points_to_wcs(Vec3(x, y, elevation) for x, y in points)]


def _xy(points: Iterable[Any]) -> list[XY]:
    """Proiecția în planul XY a unor puncte ezdxf (Vec2/Vec3)"""
    return [(p[0], p[1]) for p in points]


def _ring_area(points: Sequence[Point2]) -> float:
    """Aria (în valoare absolută) a unui contur închis"""
    total = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, (*points[1:], points[0])))
    return abs(total) / 2


def _clean_points(points: Iterable[XY], factor: float, closed: bool) -> list[Point2]:
    """Scalează în mm, elimină punctele consecutive duplicate și ultimul punct = primul la închise"""
    result: list[Point2] = []

    for x, y in points:
        point = (x * factor, y * factor)

        if not result or math.dist(result[-1], point) > DUPLICATE_TOLERANCE_MM:
            result.append(point)

    if closed and len(result) > 1 and math.dist(result[0], result[-1]) <= DUPLICATE_TOLERANCE_MM:
        result.pop()

    return result


# ----------------------------------------------------------------------------------------------
# Hașuri
# ----------------------------------------------------------------------------------------------

def _edge_points(edge: Any, segment_length: float) -> list[XY]:
    """Punctele unei muchii de hașură (în OCS), în sensul de parcurgere al căii"""
    kind = type(edge).__name__

    if kind == "LineEdge":
        return [(edge.start.x, edge.start.y), (edge.end.x, edge.end.y)]

    if kind == "ArcEdge":
        sweep  = _ccw_sweep(edge.start_angle, edge.end_angle)
        points = _arc_points((edge.center.x, edge.center.y), edge.radius,
                             math.radians(edge.start_angle), sweep, segment_length)
    elif kind == "EllipseEdge":
        points = _xy(_ellipse_points(edge.construction_tool(), segment_length))
    elif kind == "SplineEdge":
        return _xy(_spline_points(edge.construction_tool(), segment_length))
    else:
        raise ValueError(f"muchie de hașură necunoscută: {kind}")

    return points if edge.ccw else points[::-1]


def _boundary_path_points(path: Any, segment_length: float) -> list[XY]:
    """Punctele (OCS) unei căi de contur a hașurii: polilinie sau muchii"""
    if hasattr(path, "edges"):
        return [point for edge in path.edges for point in _edge_points(edge, segment_length)]

    vertices = [(v[0], v[1], v[2] if len(v) > 2 else 0.0) for v in path.vertices]
    return _bulge_polyline(vertices, True, segment_length)


def _outer_index(flags: Sequence[int], rings: Sequence[Sequence[Point2]]) -> int:
    """Indexul conturului exterior: prima cale externă, altfel cel cu aria cea mai mare"""
    for index, flag in enumerate(flags):
        if flag & HATCH_PATH_EXTERNAL_FLAG:
            return index

    return max(range(len(rings)), key = lambda i: _ring_area(rings[i]))


# ----------------------------------------------------------------------------------------------
# Colectarea entităților
# ----------------------------------------------------------------------------------------------

@dataclass
class _Collector:
    """Adună entitățile convertite și statisticile de entități ignorate / eronate"""

    ezdxf         : Any
    factor        : float     # unitate desen -> mm
    segment_length: float     # lungimea segmentului de discretizare, în unitatea desenului

    segments : list[Segment2D]  = field(default_factory = list)
    polylines: list[Polyline2D] = field(default_factory = list)
    hatches  : list[Hatch2D]    = field(default_factory = list)
    ignored  : Counter          = field(default_factory = Counter)
    failed   : Counter          = field(default_factory = Counter)
    too_deep : int              = 0

    def add(self, entity: Any, parent_layer: str | None, depth: int) -> None:
        """Convertește o entitate; erorile de date se numără, nu opresc citirea"""
        layer = _effective_layer(entity.dxf.get("layer", BASE_LAYER), parent_layer)
        kind  = entity.dxftype()

        try:
            self._dispatch(entity, kind, layer, depth)
        except (self.ezdxf.DXFError, ValueError, TypeError, IndexError, ArithmeticError, AttributeError):
            self.failed[kind] += 1

    def _dispatch(self, entity: Any, kind: str, layer: str, depth: int) -> None:
        """Alege conversia după tipul entității"""
        handlers = {"LINE"      : self._add_line,
                    "LWPOLYLINE": self._add_lwpolyline,
                    "POLYLINE"  : self._add_polyline,
                    "CIRCLE"    : self._add_circle,
                    "ARC"       : self._add_arc,
                    "ELLIPSE"   : self._add_ellipse,
                    "SPLINE"    : self._add_spline,
                    "HATCH"     : self._add_hatch}

        if kind == "INSERT":
            self._add_insert(entity, layer, depth)
        elif kind in handlers:
            handlers[kind](entity, layer)
        else:
            self.ignored[kind] += 1

    def _add_line(self, entity: Any, layer: str) -> None:
        """LINE -> Segment2D (coordonatele LINE sunt deja în WCS)"""
        points = _clean_points(_xy((entity.dxf.start, entity.dxf.end)), self.factor, False)

        if len(points) == 2:
            self.segments.append(Segment2D(points[0], points[1], layer))

    def _add_points(self, points: Iterable[XY], closed: bool, layer: str) -> None:
        """Adaugă o polilinie din puncte în unitatea desenului (WCS)"""
        cleaned = _clean_points(points, self.factor, closed)

        if len(cleaned) >= 2:
            self.polylines.append(Polyline2D(tuple(cleaned), closed and len(cleaned) > 2, layer))

    def _add_lwpolyline(self, entity: Any, layer: str) -> None:
        """LWPOLYLINE -> Polyline2D, cu bulge-urile discretizate"""
        vertices = [(x, y, b) for x, y, b in entity.get_points("xyb")]
        points   = _bulge_polyline(vertices, entity.closed, self.segment_length)
        self._add_points(_ocs_to_wcs(entity, points, entity.dxf.elevation), entity.closed, layer)

    def _add_polyline(self, entity: Any, layer: str) -> None:
        """POLYLINE 2D (cu bulge, în OCS) sau 3D (proiectată) -> Polyline2D; plasele se ignoră"""
        if entity.is_3d_polyline:
            self._add_points(_xy(entity.points()), entity.is_closed, layer)
            return

        if not entity.is_2d_polyline:
            self.ignored["POLYLINE (plasă)"] += 1
            return

        vertices = [(v.dxf.location.x, v.dxf.location.y, v.dxf.bulge) for v in entity.vertices
                    if not v.dxf.flags & SPLINE_FRAME_VERTEX_FLAG]
        points   = _bulge_polyline(vertices, entity.is_closed, self.segment_length)
        self._add_points(_ocs_to_wcs(entity, points, entity.dxf.elevation.z), entity.is_closed, layer)

    def _add_circle(self, entity: Any, layer: str) -> None:
        """CIRCLE -> Polyline2D închisă"""
        center = entity.dxf.center
        points = _arc_points((center.x, center.y), entity.dxf.radius, 0.0, 2 * math.pi, self.segment_length)
        self._add_points(_ocs_to_wcs(entity, points, center.z), True, layer)

    def _add_arc(self, entity: Any, layer: str) -> None:
        """ARC -> Polyline2D deschisă"""
        center = entity.dxf.center
        sweep  = _ccw_sweep(entity.dxf.start_angle, entity.dxf.end_angle)
        points = _arc_points((center.x, center.y), entity.dxf.radius,
                             math.radians(entity.dxf.start_angle), sweep, self.segment_length)
        self._add_points(_ocs_to_wcs(entity, points, center.z), False, layer)

    def _add_ellipse(self, entity: Any, layer: str) -> None:
        """ELLIPSE -> Polyline2D (închisă dacă elipsa este completă)"""
        ellipse = entity.construction_tool()
        closed  = math.isclose(ellipse.param_span, 2 * math.pi)
        self._add_points(_xy(_ellipse_points(ellipse, self.segment_length)), closed, layer)

    def _add_spline(self, entity: Any, layer: str) -> None:
        """SPLINE -> Polyline2D discretizată"""
        points = _xy(_spline_points(entity.construction_tool(), self.segment_length))
        self._add_points(points, bool(entity.closed), layer)

    def _add_hatch(self, entity: Any, layer: str) -> None:
        """HATCH -> Hatch2D: conturul exterior și golurile"""
        elevation = entity.dxf.elevation.z
        flags: list[int] = []
        rings: list[list[Point2]] = []

        for path in entity.paths:
            points = _ocs_to_wcs(entity, _boundary_path_points(path, self.segment_length), elevation)
            ring   = _clean_points(points, self.factor, True)

            if len(ring) >= 3:
                flags.append(path.path_type_flags)
                rings.append(ring)

        if not rings:
            return

        outer = _outer_index(flags, rings)
        holes = tuple(tuple(ring) for i, ring in enumerate(rings) if i != outer)
        self.hatches.append(Hatch2D(tuple(rings[outer]), holes, layer))

    def _add_insert(self, entity: Any, layer: str, depth: int) -> None:
        """INSERT -> entitățile blocului, transformate și explodate recursiv"""
        if depth >= MAX_BLOCK_DEPTH:
            self.too_deep += 1
            return

        inserts = entity.multi_insert() if entity.mcount > 1 else (entity,)

        for insert in inserts:
            for child in insert.virtual_entities():
                self.add(child, layer, depth + 1)

    def drawing(self, warnings: list[str]) -> Drawing2D:
        """Planșa rezultată, cu avertismentele sumare"""
        all_warnings = [*warnings, *self._summary_warnings()]
        return Drawing2D(tuple(self.segments), tuple(self.polylines), tuple(self.hatches), tuple(all_warnings))

    def _summary_warnings(self) -> list[str]:
        """Avertismente pentru entitățile ignorate, eronate și blocurile prea adânci"""
        warnings = []

        if self.ignored:
            warnings.append("Entități ignorate (nesuportate): " + _format_counter(self.ignored))

        if self.failed:
            warnings.append("Entități care nu au putut fi citite (date invalide): " + _format_counter(self.failed))

        if self.too_deep:
            warnings.append(f"{self.too_deep} inserări de bloc ignorate: imbricare mai adâncă de {MAX_BLOCK_DEPTH} niveluri.")

        return warnings


def _effective_layer(layer: str, parent_layer: str | None) -> str:
    """Layerul efectiv: entitățile din bloc aflate pe layerul "0" moștenesc layerul inserției"""
    if parent_layer is not None and layer == BASE_LAYER:
        return parent_layer

    return layer


def _format_counter(counter: Counter) -> str:
    """Text sumar „TIP: n, TIP: m”, sortat după tip"""
    return ", ".join(f"{kind}: {count}" for kind, count in sorted(counter.items()))
