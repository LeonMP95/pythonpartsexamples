"""Sursa de planșe din modelul Allplan: elementele 2D selectate -> Drawing2D (mm)

Planșa DWG/PDF este importată în Allplan cu importul nativ; utilizatorul selectează liniile,
poliliniile și hașurile/umpluturile. Grupurile, simbolurile și macro-urile sunt despachetate
(se coboară în elementele copil dacă elementul însuși nu are geometrie 2D acceptată).

Geometrie acceptată (tipul întors de BaseElementAdapter.GetModelGeometry()):
    -   Line2D                     -> Segment2D
    -   Polyline2D                 -> Polyline2D (închisă dacă primul punct = ultimul punct)
    -   Polygon2D                  -> Hatch2D (hașuri / umpluturi / suprafețe; componentele
                                      interioare devin goluri)
    -   Arc2D (și cercuri), Path2D -> Polyline2D discretizată cu AllplanGeo.DivisionPoints
Celelalte tipuri sunt ignorate și raportate în avertismente.

DE VERIFICAT ÎN ALLPLAN: tipul de geometrie întors pentru hașuri, umpluturi, simboluri și
macro-uri și împărțirea în componente a poligoanelor cu goluri (vezi README).

Unitatea internă Allplan este mm, deci coordonatele nu se scalează.
"""

from __future__ import annotations

import math

from collections import Counter
from typing import Any, Iterable

import NemAll_Python_BaseElements as AllplanBaseEle
import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_IFW_ElementAdapter as AllplanEleAdapter

from StructuralModeling.FromDrawing.Model2D import Drawing2D, Hatch2D, Point2, Polyline2D, Segment2D

POINT_TOLERANCE_MM  = 1e-3      # sub această distanță două puncte consecutive sunt identice
MAX_UNPACK_DEPTH    = 8         # adâncimea maximă de despachetare grupuri / macro-uri
DIVISION_EPSILON    = 0.0       # ca în GeometryExamples/DivisionPoints.pyp (Epsilon = 0)
MIN_SEGMENTS_CLOSED = 16        # minimul de segmente pentru o curbă închisă (cerc complet), ca în DxfSource
MIN_SEGMENTS_OPEN   = 4         # minimul pentru un arc deschis (unghiul la centru nu este citit din Arc2D)
MAX_SEGMENTS_CURVE  = 10000     # limită de siguranță pe curbă, ca în DxfSource.MAX_SEGMENTS_PER_CURVE
UNKNOWN_LAYER       = ""


def drawing_from_elements(elements             : Iterable[Any],
                          document_id          : Any,
                          arc_segment_length_mm: float = 100.0) -> Drawing2D:
    """Convertește elementele selectate din Allplan într-un Drawing2D

    Args:
        elements:              elementele selectate (BaseElementAdapter)
        document_id:           id-ul documentului (coord_input.GetInputViewDocumentID())
        arc_segment_length_mm: lungimea maximă a coardei la discretizarea arcelor [mm]

    Returns:
        planșa 2D, în mm, cu avertismente pentru geometria ignorată
    """
    _check_segment_length(arc_segment_length_mm)

    collector   = _Collector(document_id, arc_segment_length_mm)
    stack       = [(element, 0) for element in elements]

    while stack:
        element, depth = stack.pop()

        if collector.add_element(element):
            continue

        children = _child_elements(element) if depth < MAX_UNPACK_DEPTH else []

        if children:
            stack.extend((child, depth + 1) for child in children)
        else:
            collector.ignored[_type_name(element)] += 1

    return collector.drawing()


def is_supported_geometry(geo: Any) -> bool:
    """True dacă tipul de geometrie poate fi convertit"""
    return isinstance(geo, (AllplanGeo.Line2D, AllplanGeo.Polygon2D, AllplanGeo.Polyline2D,
                            AllplanGeo.Arc2D, AllplanGeo.Path2D))


def convert_geometry(geo                  : Any,
                     layer                : str,
                     arc_segment_length_mm: float) -> list[Segment2D | Polyline2D | Hatch2D] | None:
    """Convertește un obiect de geometrie Allplan în entități Model2D

    Returns:
        lista de entități (poate fi goală pentru geometrie degenerată) sau None dacă tipul nu este acceptat
    """
    if isinstance(geo, AllplanGeo.Line2D):
        return [Segment2D(_xy(geo.StartPoint), _xy(geo.EndPoint), layer)]

    if isinstance(geo, AllplanGeo.Polygon2D):
        return _hatch_from_polygon(geo, layer)

    if isinstance(geo, AllplanGeo.Polyline2D):
        return _polyline_from_points([_xy(pnt) for pnt in geo.Points], layer)

    if isinstance(geo, AllplanGeo.Arc2D):
        start, end = _xy(geo.StartPoint), _xy(geo.EndPoint)
        path       = AllplanGeo.Path2D()
        path      += geo
        count      = segment_count(AllplanGeo.CalcLength(geo), arc_segment_length_mm, _same(start, end))
        return _polyline_from_points([start, *_division_points(path, count), end], layer)

    if isinstance(geo, AllplanGeo.Path2D):
        count = segment_count(AllplanGeo.CalcLength(geo), arc_segment_length_mm, False)
        return _polyline_from_points(_division_points(geo, count), layer)

    return None


class _Collector:
    """Acumulează entitățile și avertismentele conversiei"""

    def __init__(self, document_id: Any, arc_segment_length_mm: float):
        self.document_id           = document_id
        self.arc_segment_length_mm = arc_segment_length_mm
        self.segments : list[Segment2D]  = []
        self.polylines: list[Polyline2D] = []
        self.hatches  : list[Hatch2D]    = []
        self.ignored  : Counter          = Counter()
        self.degenerate                  = 0
        self.layer_cache: dict[Any, str] = {}
        self.missing_layers              = 0

    def add_element(self, element: Any) -> bool:
        """Adaugă geometria elementului; False dacă elementul nu are nicio geometrie acceptată"""
        geometries = element.GetModelGeometry()

        if not isinstance(geometries, list):       # ca în SelectDrawingGeometryForPythonPart.py:236
            geometries = [geometries]

        if not any(is_supported_geometry(geo) for geo in geometries):
            return False

        layer = self.layer_name(element)

        for geo in geometries:
            entities = convert_geometry(geo, layer, self.arc_segment_length_mm)

            if entities is None:
                self.ignored[type(geo).__name__] += 1
                continue

            if not entities:
                self.degenerate += 1

            for entity in entities:
                self._store(entity)

        return True

    def layer_name(self, element: Any) -> str:
        """Numele scurt al layerului elementului (cu memorare pe id)"""
        layer_id = element.GetCommonProperties().Layer

        if layer_id not in self.layer_cache:
            name = AllplanBaseEle.LayerService.GetShortNameByID(layer_id, self.document_id)
            self.layer_cache[layer_id] = str(name) if name else UNKNOWN_LAYER

            if not name:
                self.missing_layers += 1

        return self.layer_cache[layer_id]

    def _store(self, entity: Segment2D | Polyline2D | Hatch2D):
        if isinstance(entity, Segment2D):
            self.segments.append(entity)
        elif isinstance(entity, Polyline2D):
            self.polylines.append(entity)
        else:
            self.hatches.append(entity)

    def drawing(self) -> Drawing2D:
        """Planșa rezultată, cu avertismente"""
        warnings = []

        if self.ignored:
            details = ", ".join(f"{name}: {count}" for name, count in sorted(self.ignored.items()))
            warnings.append(f"Elemente ignorate (geometrie neacceptată): {details}")

        if self.degenerate:
            warnings.append(f"{self.degenerate} obiecte de geometrie degenerate (prea puține puncte) au fost ignorate")

        if self.missing_layers:
            warnings.append(f"{self.missing_layers} layere fără nume scurt: elementele lor nu pot fi recunoscute")

        return Drawing2D(tuple(self.segments), tuple(self.polylines), tuple(self.hatches), tuple(warnings))


def _child_elements(element: Any) -> list:
    """Elementele copil (grupuri, simboluri, macro-uri), ca în ShowObjectInformation.py:171"""
    children = AllplanEleAdapter.BaseElementAdapterChildElementsService.GetChildModelElementsFromTree(element)
    return list(children) if children else []


def _type_name(element: Any) -> str:
    try:
        return str(element.GetElementAdapterType().GetTypeName())
    except AttributeError:
        return type(element).__name__


def _xy(point: Any) -> Point2:
    return float(point.X), float(point.Y)


def _same(pnt_1: Point2, pnt_2: Point2) -> bool:
    return abs(pnt_1[0] - pnt_2[0]) <= POINT_TOLERANCE_MM and abs(pnt_1[1] - pnt_2[1]) <= POINT_TOLERANCE_MM


def _dedupe(points: Iterable[Point2]) -> list[Point2]:
    """Elimină punctele consecutive identice"""
    result: list[Point2] = []

    for pnt in points:
        if not result or not _same(result[-1], pnt):
            result.append(pnt)

    return result


def _check_segment_length(segment_length_mm: float):
    """lungimea segmentului de discretizare: număr finit pozitiv"""
    if isinstance(segment_length_mm, bool) or not isinstance(segment_length_mm, (int, float)) \
            or not math.isfinite(segment_length_mm) or segment_length_mm <= 0:
        raise ValueError(f"Lungimea segmentului de discretizare a arcelor trebuie să fie un număr pozitiv "
                         f"(primit: {segment_length_mm!r})")


def segment_count(length_mm: float, segment_length_mm: float, closed: bool) -> int:
    """Numărul de segmente al unei curbe: după lungime, cu minim (16 pe curbă închisă) și maxim 10000

    Lungimea curbei vine din AllplanGeo.CalcLength (GeometryExamples/.../CalcLength.py:152).
    """
    _check_segment_length(segment_length_mm)

    minimum = MIN_SEGMENTS_CLOSED if closed else MIN_SEGMENTS_OPEN

    if not math.isfinite(length_mm) or length_mm <= 0:
        return minimum

    return min(max(math.ceil(length_mm / segment_length_mm), minimum), MAX_SEGMENTS_CURVE)


def _division_points(path: Any, count: int) -> list[Point2]:
    """Punctele de împărțire în `count` părți egale (varianta cu număr de diviziuni din
    GeometryExamples/DivisionPoints.py:163-168). DE VERIFICAT în Allplan dacă include capetele;
    capetele duble sunt eliminate oricum."""
    division = AllplanGeo.DivisionPoints(path, int(count), DIVISION_EPSILON)
    return [_xy(pnt) for pnt in division.GetPoints()]


def _polyline_from_points(points: list[Point2], layer: str) -> list[Segment2D | Polyline2D | Hatch2D]:
    """Polilinie din puncte; închisă dacă primul punct coincide cu ultimul (ultimul nu se repetă)"""
    pts    = _dedupe(points)
    closed = len(pts) > 3 and _same(pts[0], pts[-1])

    if closed:
        pts = pts[:-1]

    if len(pts) < 2:
        return []

    return [Polyline2D(tuple(pts), closed, layer)]


def _ring_area(points: list[Point2]) -> float:
    """aria cu semn (formula lui Gauss), doar pentru alegerea conturului exterior"""
    return sum(x_1 * y_2 - x_2 * y_1 for (x_1, y_1), (x_2, y_2) in zip(points, points[1:] + points[:1])) / 2


def split_polygon_components(points: list[Point2]) -> list[list[Point2]]:
    """Împarte punctele unui Polygon2D în componente închise

    Un Polygon2D Allplan cu goluri are componentele consecutive, fiecare închisă prin repetarea
    primului ei punct. DE VERIFICAT ÎN ALLPLAN pentru hașurile cu goluri.
    """
    components: list[list[Point2]] = []
    current   : list[Point2]       = []

    for pnt in points:
        if len(current) >= 3 and _same(current[0], pnt):
            components.append(current)
            current = []
            continue

        current.append(pnt)

    if len(current) >= 3:
        components.append(current)

    return [ring for ring in (_dedupe(comp) for comp in components) if len(ring) >= 3]


def _hatch_from_polygon(polygon: Any, layer: str) -> list[Segment2D | Polyline2D | Hatch2D]:
    """Hașură din Polygon2D: componenta cu aria cea mai mare este conturul, restul sunt goluri"""
    rings = split_polygon_components([_xy(pnt) for pnt in polygon.Points])

    if not rings:
        return []

    outer_index = max(range(len(rings)), key = lambda index: abs(_ring_area(rings[index])))
    holes       = tuple(tuple(ring) for index, ring in enumerate(rings) if index != outer_index)

    return [Hatch2D(tuple(rings[outer_index]), holes, layer)]
