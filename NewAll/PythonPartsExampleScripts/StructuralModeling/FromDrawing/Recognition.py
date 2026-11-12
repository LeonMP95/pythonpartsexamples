"""Recunoașterea elementelor structurale (stâlpi, pereți, grinzi, plăci) dintr-o planșă 2D

Intrare: un Drawing2D (coordonate în mm), regulile de recunoaștere (RecognitionRules) și nivelul.
Ieșire: un StructuralModel cu elementele recunoscute și avertismentele (în română).

Modulul face doar geometrie plană: nu conține reguli din normă și nu dimensionează nimic.
Este Python pur (fără Allplan, fără dependențe externe), fără efecte secundare și determinist:
entitățile se sortează înainte de prelucrare, iar elementele rezultate se sortează după poziție
(y descrescător, apoi x crescător) și se numerotează S1.. / P1.. / G1.. / PL1...

Principiu: ce este ambiguu nu se ghicește, ci devine avertisment (tipul elementului, layerul,
coordonatele aproximative în mm).
"""

from __future__ import annotations

import math

from dataclasses import dataclass

from .Model2D import Drawing2D, Point2, Segment2D
from .RecognitionRules import RecognitionRules
from .StructuralModel import Beam, Column, Level, Slab, StructuralModel, Wall

Ring = tuple[Point2, ...]

_EPS = 1e-9                     # zero numeric pentru împărțiri [mm]
_SORT_DECIMALS = 1              # rotunjirea coordonatelor la sortare (elimină zgomotul numeric) [mm]

_LABEL = {"column": "Stâlp", "wall": "Perete", "beam": "Grindă", "slab": "Placă"}
_SOURCE_PRIORITY = {"polilinie": 0, "segmente": 1, "hașură": 2}


# ----------------------------------------------------------------------------------------------
# Geometrie elementară (toate lungimile în mm)
# ----------------------------------------------------------------------------------------------

def _dist(p_1: Point2, p_2: Point2) -> float:
    """distanța între două puncte [mm]"""
    return math.hypot(p_2[0] - p_1[0], p_2[1] - p_1[1])


def _mid(p_1: Point2, p_2: Point2) -> Point2:
    """mijlocul segmentului p_1 - p_2"""
    return (p_1[0] + p_2[0]) / 2, (p_1[1] + p_2[1]) / 2


def _line_distance(pnt: Point2, p_a: Point2, p_b: Point2) -> float:
    """distanța de la pnt la dreapta prin p_a, p_b [mm]; dacă p_a = p_b, distanța la p_a"""
    length = _dist(p_a, p_b)

    if length < _EPS:
        return _dist(pnt, p_a)

    return abs((p_b[0] - p_a[0]) * (pnt[1] - p_a[1]) - (p_b[1] - p_a[1]) * (pnt[0] - p_a[0])) / length


def _direction_deg(p_1: Point2, p_2: Point2) -> float:
    """direcția dreptei p_1 - p_2, în grade, în [0, 180)"""
    return math.degrees(math.atan2(p_2[1] - p_1[1], p_2[0] - p_1[0])) % 180.0


def _angle_diff_deg(angle_1: float, angle_2: float) -> float:
    """unghiul dintre două direcții (fără sens), în grade, în [0, 90]"""
    diff = abs(angle_1 - angle_2) % 180.0
    return min(diff, 180.0 - diff)


def _bbox(points: Ring) -> tuple[float, float, float, float]:
    """dreptunghiul încadrator (x_min, y_min, x_max, y_max) [mm]"""
    xs = [pnt[0] for pnt in points]
    ys = [pnt[1] for pnt in points]
    return min(xs), min(ys), max(xs), max(ys)


def _signed_area(points: Ring) -> float:
    """aria cu semn a poligonului (pozitivă în sens trigonometric) [mm²]"""
    pts = list(points)
    return sum(x_1 * y_2 - x_2 * y_1 for (x_1, y_1), (x_2, y_2) in zip(pts, pts[1:] + pts[:1])) / 2


def _ring_center(points: Ring) -> Point2:
    """centrul de greutate al poligonului; pentru poligoane degenerate, centrul dreptunghiului încadrator"""
    area = _signed_area(points)

    if abs(area) < _EPS:
        x_min, y_min, x_max, y_max = _bbox(points)
        return (x_min + x_max) / 2, (y_min + y_max) / 2

    pts = list(points)
    c_x = c_y = 0.0

    for (x_1, y_1), (x_2, y_2) in zip(pts, pts[1:] + pts[:1]):
        cross = x_1 * y_2 - x_2 * y_1
        c_x  += (x_1 + x_2) * cross
        c_y  += (y_1 + y_2) * cross

    return c_x / (6 * area), c_y / (6 * area)


def _point_in_polygon(pnt: Point2, polygon: Ring) -> bool:
    """True dacă punctul este în interiorul poligonului (raza orizontală; pe contur rezultatul e nedefinit)"""
    inside = False
    pts    = list(polygon)

    for (x_1, y_1), (x_2, y_2) in zip(pts, pts[1:] + pts[:1]):
        if (y_1 > pnt[1]) != (y_2 > pnt[1]):
            x_cross = x_1 + (pnt[1] - y_1) * (x_2 - x_1) / (y_2 - y_1)
            if pnt[0] < x_cross:
                inside = not inside

    return inside


def _ring_edges(points: Ring, layer: str) -> list[Segment2D]:
    """laturile unui contur închis"""
    pts = list(points)
    return [Segment2D(p_1, p_2, layer) for p_1, p_2 in zip(pts, pts[1:] + pts[:1])]


def _path_edges(points: Ring, layer: str) -> list[Segment2D]:
    """segmentele unei polilinii deschise"""
    return [Segment2D(p_1, p_2, layer) for p_1, p_2 in zip(points, points[1:])]


def _fmt(pnt: Point2) -> str:
    """coordonate aproximative pentru mesaje, rotunjite la mm"""
    return f"({pnt[0]:.0f}, {pnt[1]:.0f})"


def _sort_key(pnt: Point2) -> tuple[float, float]:
    """cheia de sortare a elementelor: y descrescător, apoi x crescător"""
    return -round(pnt[1], _SORT_DECIMALS), round(pnt[0], _SORT_DECIMALS)


def _canonical_axis(start: Point2, end: Point2, tolerance: float) -> tuple[Point2, Point2]:
    """orientează o axă de la stânga la dreapta (sau de jos în sus dacă e practic verticală)"""
    d_x = end[0] - start[0]
    d_y = end[1] - start[1]

    if d_x < -tolerance or (abs(d_x) <= tolerance and d_y < 0):
        return end, start

    return start, end


# ----------------------------------------------------------------------------------------------
# Curățarea conturilor
# ----------------------------------------------------------------------------------------------

def _dedupe_consecutive(points: Ring, tolerance: float) -> list[Point2]:
    """elimină punctele consecutive aflate la cel mult tolerance [mm]"""
    result: list[Point2] = []

    for pnt in points:
        if not result or _dist(pnt, result[-1]) > tolerance:
            result.append((float(pnt[0]), float(pnt[1])))

    return result


def _clean_ring(points: Ring, tolerance: float) -> Ring:
    """Contur închis fără puncte duplicate și fără puncte coliniare

    Un vârf este eliminat dacă se află la cel mult tolerance [mm] de dreapta prin vecinii săi.
    Rezultatul poate avea sub 3 puncte (contur degenerat); apelantul decide ce face cu el.
    """
    pts = _dedupe_consecutive(points, tolerance)

    while len(pts) > 1 and _dist(pts[0], pts[-1]) <= tolerance:
        pts.pop()

    removed = True

    while removed and len(pts) >= 3:
        removed = False

        for idx, pnt in enumerate(pts):
            if _line_distance(pnt, pts[idx - 1], pts[(idx + 1) % len(pts)]) <= tolerance:
                del pts[idx]
                removed = True
                break

    return tuple(pts)


def _same_ring(ring_1: Ring, ring_2: Ring, tolerance: float) -> bool:
    """True dacă două contururi au aceleași vârfuri (în tolerance [mm]), indiferent de sens și de primul punct"""
    if len(ring_1) != len(ring_2):
        return False

    return (all(any(_dist(p_1, p_2) <= tolerance for p_2 in ring_2) for p_1 in ring_1)
            and all(any(_dist(p_1, p_2) <= tolerance for p_1 in ring_1) for p_2 in ring_2))


# ----------------------------------------------------------------------------------------------
# Colectarea entităților de pe layerele unui tip de element
# ----------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class _Contour:
    """contur închis curățat, cu goluri (doar pentru hașuri) și sursa lui"""

    points: Ring
    holes : tuple[Ring, ...]
    layer : str
    source: str             # "polilinie", "segmente" sau "hașură"


@dataclass
class _Entities:
    """entitățile unui tip de element: contururi închise, polilinii deschise, segmente libere"""

    contours: list[_Contour]
    paths   : list[tuple[Ring, str]]
    segments: list[Segment2D]


def _segment_key(seg: Segment2D) -> tuple:
    return seg.layer, min(seg.start, seg.end), max(seg.start, seg.end)


def _contour_key(contour: _Contour) -> tuple:
    return contour.layer, _SOURCE_PRIORITY[contour.source], _bbox(contour.points), contour.points


def _collect(drawing: Drawing2D, layers: set[str], tolerance: float, label: str,
             warnings: list[str]) -> _Entities:
    """Colectează și curăță entitățile de pe layerele date

    -   segmentele cu lungimea <= tolerance [mm] sunt ignorate, cu avertisment;
    -   o polilinie deschisă cu capetele în tolerance este tratată ca închisă;
    -   contururile degenerate (sub 3 vârfuri după curățare) sunt ignorate, cu avertisment.
    """
    sub = drawing.on_layers(layers)
    ent = _Entities([], [], [])

    for seg in sub.segments:
        if seg.length <= tolerance:
            warnings.append(f"{label}: segment degenerat (lungime {seg.length:.1f} mm) pe layerul "
                            f"'{seg.layer}' la {_fmt(seg.start)}, ignorat.")
        else:
            ent.segments.append(seg)

    for poly in sub.polylines:
        pts = _dedupe_consecutive(poly.points, tolerance)
        closes = poly.closed or (len(pts) >= 4 and _dist(pts[0], pts[-1]) <= tolerance)

        if closes:
            _add_contour(ent, _clean_ring(tuple(pts), tolerance), (), poly.layer, "polilinie", label, warnings)
        elif len(pts) < 2:
            warnings.append(f"{label}: polilinie degenerată pe layerul '{poly.layer}' la "
                            f"{_fmt(poly.points[0]) if poly.points else '(?)'}, ignorată.")
        else:
            ent.paths.append((tuple(pts), poly.layer))

    for hatch in sub.hatches:
        holes = tuple(hole for hole in (_clean_ring(h, tolerance) for h in hatch.holes) if len(hole) >= 3)
        _add_contour(ent, _clean_ring(hatch.outer, tolerance), holes, hatch.layer, "hașură", label, warnings)

    ent.segments.sort(key = _segment_key)
    ent.paths.sort(key = lambda path: (path[1], path[0]))
    ent.contours = _unique_contours(sorted(ent.contours, key = _contour_key), tolerance)
    return ent


def _add_contour(ent: _Entities, ring: Ring, holes: tuple[Ring, ...], layer: str, source: str,
                 label: str, warnings: list[str]) -> None:
    """adaugă un contur închis curățat sau un avertisment dacă e degenerat"""
    if len(ring) < 3:
        where = _fmt(ring[0]) if ring else "(?)"
        warnings.append(f"{label}: contur ({source}) degenerat pe layerul '{layer}' la {where}, ignorat.")
        return

    ent.contours.append(_Contour(ring, holes, layer, source))


def _unique_contours(contours: list[_Contour], tolerance: float) -> list[_Contour]:
    """Contururile identice (în tolerance [mm]) de pe același layer devin unul singur

    Se păstrează conturul cu prioritatea cea mai mare (polilinie, apoi segmente, apoi hașură);
    golurile se reunesc.
    """
    result: list[_Contour] = []

    for contour in contours:
        for idx, kept in enumerate(result):
            if kept.layer == contour.layer and _same_ring(kept.points, contour.points, tolerance):
                extra = tuple(hole for hole in contour.holes
                              if not any(_same_ring(hole, old, tolerance) for old in kept.holes))
                result[idx] = _Contour(kept.points, kept.holes + extra, kept.layer, kept.source)
                break
        else:
            result.append(contour)

    return result


# ----------------------------------------------------------------------------------------------
# Dreptunghiuri
# ----------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class _RectAxis:
    """axa longitudinală a unui dreptunghi: pe mijlocul laturilor scurte"""

    start : Point2
    end   : Point2
    width : float           # latura scurtă [mm]
    length: float           # latura lungă [mm]


def _rectangle_axis(ring: Ring, angle_tolerance_deg: float) -> _RectAxis | None:
    """Axa unui contur dreptunghiular sau None dacă nu e dreptunghi

    Dreptunghi = 4 vârfuri, toate unghiurile 90° ± angle_tolerance_deg.
    Laturile opuse se mediază. Pentru un pătrat axa e arbitrară; apelantul verifică width ≈ length.
    """
    if len(ring) != 4:
        return None

    for idx in range(4):
        angle = _angle_diff_deg(_direction_deg(ring[idx - 1], ring[idx]),
                                _direction_deg(ring[idx], ring[(idx + 1) % 4]))
        if abs(90.0 - angle) > angle_tolerance_deg:
            return None

    p_0, p_1, p_2, p_3 = ring
    side_a = (_dist(p_0, p_1) + _dist(p_2, p_3)) / 2
    side_b = (_dist(p_1, p_2) + _dist(p_3, p_0)) / 2

    if side_a >= side_b:
        return _RectAxis(_mid(p_3, p_0), _mid(p_1, p_2), side_b, side_a)

    return _RectAxis(_mid(p_0, p_1), _mid(p_2, p_3), side_a, side_b)


# ----------------------------------------------------------------------------------------------
# Stâlpi
# ----------------------------------------------------------------------------------------------

def _chain_loops(segments: list[Segment2D], tolerance: float) -> tuple[list[Ring], list[Segment2D]]:
    """Înlănțuie segmente în contururi închise (capete în tolerance [mm])

    Lanțul pornește dintr-un segment și continuă cât timp există exact un segment nefolosit
    cu un capăt în capătul curent; o ramificație (mai multe candidate) oprește lanțul (nu se ghicește).
    Returnează contururile închise (necurățate) și segmentele rămase.
    """
    used = [False] * len(segments)
    loops: list[Ring] = []

    for first, seg in enumerate(segments):
        if used[first]:
            continue

        chain, points = [first], [seg.start, seg.end]

        while not (len(chain) >= 3 and _dist(points[-1], points[0]) <= tolerance):
            candidates = [idx for idx, other in enumerate(segments)
                          if not used[idx] and idx not in chain
                          and min(_dist(other.start, points[-1]), _dist(other.end, points[-1])) <= tolerance]
            if len(candidates) != 1:
                break

            other = segments[candidates[0]]
            chain.append(candidates[0])
            points.append(other.end if _dist(other.start, points[-1]) <= tolerance else other.start)
        else:
            for idx in chain:
                used[idx] = True
            loops.append(tuple(points[:-1]))

    return loops, [seg for idx, seg in enumerate(segments) if not used[idx]]


def _column_contours(ent: _Entities, rules: RecognitionRules, warnings: list[str]) -> list[_Contour]:
    """contururile de stâlpi: cele închise plus cele obținute prin înlănțuirea segmentelor libere"""
    tol  = rules.point_tolerance
    free = list(ent.segments) + [seg for pts, layer in ent.paths for seg in _path_edges(pts, layer)]
    contours = list(ent.contours)

    for layer in sorted({seg.layer for seg in free}):
        loops, leftover = _chain_loops([seg for seg in free if seg.layer == layer], tol)

        for loop in loops:
            _add_contour_from_loop(contours, _clean_ring(loop, tol), layer, warnings)

        for seg in leftover:
            warnings.append(f"Stâlp: segment care nu formează un contur închis pe layerul '{layer}', "
                            f"de la {_fmt(seg.start)} la {_fmt(seg.end)}, ignorat.")

    return _unique_contours(sorted(contours, key = _contour_key), tol)


def _add_contour_from_loop(contours: list[_Contour], ring: Ring, layer: str, warnings: list[str]) -> None:
    if len(ring) < 3:
        warnings.append(f"Stâlp: segmente înlănțuite într-un contur degenerat pe layerul '{layer}', ignorate.")
    else:
        contours.append(_Contour(ring, (), layer, "segmente"))


def _recognize_columns(drawing: Drawing2D, layers: set[str], rules: RecognitionRules,
                       warnings: list[str]) -> list[Ring]:
    """Regula 1 (stâlpi): contururile închise cu ambele laturi ale dreptunghiului încadrator
    în [column_min_size, column_max_size] [mm]

    Hașurile cu goluri și contururile în afara limitelor devin avertismente.
    Returnează contururile (curățate) ale stâlpilor.
    """
    ent      = _collect(drawing, layers, rules.point_tolerance, _LABEL["column"], warnings)
    outlines = []

    for contour in _column_contours(ent, rules, warnings):
        x_min, y_min, x_max, y_max = _bbox(contour.points)
        size_x, size_y = x_max - x_min, y_max - y_min
        where = _fmt(_ring_center(contour.points))

        if contour.holes:
            warnings.append(f"Stâlp: conturul ({contour.source}) de pe layerul '{contour.layer}' din jurul {where} "
                            f"are goluri; stâlpii cu goluri nu sunt recunoscuți, ignorat.")
        elif not all(rules.column_min_size <= size <= rules.column_max_size for size in (size_x, size_y)):
            warnings.append(f"Stâlp: conturul ({contour.source}) de pe layerul '{contour.layer}' din jurul {where} "
                            f"are {size_x:.0f} x {size_y:.0f} mm, în afara limitelor "
                            f"[{rules.column_min_size:.0f}, {rules.column_max_size:.0f}] mm; nu s-a creat stâlpul.")
        else:
            outlines.append(contour.points)

    return outlines


# ----------------------------------------------------------------------------------------------
# Pereți
# ----------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class _WallAxis:
    """perete recunoscut, înainte de numerotare"""

    start    : Point2
    end      : Point2
    thickness: float

    @property
    def length(self) -> float:
        return _dist(self.start, self.end)


def _face_pair(face_a: Segment2D, face_b: Segment2D, rules: RecognitionRules) -> _WallAxis | None:
    """Peretele format de două fețe sau None

    Condiții: fețe paralele (± parallel_tolerance_deg), suprapunere în proiecție pe direcția
    lui face_a >= wall_min_length [mm], distanța între fețe (media la capetele zonei de suprapunere)
    în [wall_min_thickness, wall_max_thickness] [mm]. Axa = linia mediană pe zona de suprapunere.
    """
    if _angle_diff_deg(_direction_deg(face_a.start, face_a.end),
                       _direction_deg(face_b.start, face_b.end)) > rules.parallel_tolerance_deg:
        return None

    u_x = (face_a.end[0] - face_a.start[0]) / face_a.length
    u_y = (face_a.end[1] - face_a.start[1]) / face_a.length
    origin = face_a.start

    def to_frame(pnt: Point2) -> tuple[float, float]:
        d_x, d_y = pnt[0] - origin[0], pnt[1] - origin[1]
        return d_x * u_x + d_y * u_y, -d_x * u_y + d_y * u_x

    (t_0, h_0), (t_1, h_1) = sorted((to_frame(face_b.start), to_frame(face_b.end)))
    s_0, s_1 = max(0.0, t_0), min(face_a.length, t_1)

    if s_1 - s_0 < rules.wall_min_length or t_1 - t_0 < _EPS:
        return None

    h_s0 = h_0 + (s_0 - t_0) * (h_1 - h_0) / (t_1 - t_0)
    h_s1 = h_0 + (s_1 - t_0) * (h_1 - h_0) / (t_1 - t_0)
    thickness = (abs(h_s0) + abs(h_s1)) / 2

    if h_s0 * h_s1 <= 0 or not rules.wall_min_thickness <= thickness <= rules.wall_max_thickness:
        return None

    start = (origin[0] + u_x * s_0 - u_y * h_s0 / 2, origin[1] + u_y * s_0 + u_x * h_s0 / 2)
    end   = (origin[0] + u_x * s_1 - u_y * h_s1 / 2, origin[1] + u_y * s_1 + u_x * h_s1 / 2)
    return _WallAxis(*_canonical_axis(start, end, rules.point_tolerance), thickness)


def _pair_faces(faces: list[Segment2D], rules: RecognitionRules) -> tuple[list[_WallAxis], list[Segment2D]]:
    """Împerechează fețele de pe un layer: fiecare față în cel mult o pereche, în ordinea
    crescătoare a distanței dintre fețe (fața opusă cea mai apropiată). Returnează pereții și fețele rămase."""
    candidates = []

    for idx_a in range(len(faces)):
        for idx_b in range(idx_a + 1, len(faces)):
            axis = _face_pair(faces[idx_a], faces[idx_b], rules)
            if axis is not None:
                candidates.append((axis.thickness, idx_a, idx_b, axis))

    candidates.sort(key = lambda cand: cand[:3])
    used: set[int] = set()
    walls = []

    for _, idx_a, idx_b, axis in candidates:
        if idx_a not in used and idx_b not in used:
            used.update((idx_a, idx_b))
            walls.append(axis)

    return walls, [face for idx, face in enumerate(faces) if idx not in used]


def _wall_from_rectangle(contour: _Contour, rect: _RectAxis, rules: RecognitionRules,
                         warnings: list[str]) -> _WallAxis | None:
    """Perete dintr-un contur dreptunghiular cu latura scurtă în [wall_min_thickness, wall_max_thickness]:
    axa pe direcția lungă, grosimea = latura scurtă [mm]

    Pătratele (direcție ambiguă) și lungimile sub wall_min_length devin avertismente.
    """
    where = f"pe layerul '{contour.layer}' din jurul {_fmt(_ring_center(contour.points))}"

    if rect.length - rect.width <= rules.point_tolerance:
        warnings.append(f"Perete: contur pătrat ({rect.width:.0f} x {rect.length:.0f} mm) {where}; "
                        f"direcția peretelui este ambiguă, ignorat.")
    elif rect.length < rules.wall_min_length:
        warnings.append(f"Perete: contur dreptunghiular {where} cu lungimea {rect.length:.0f} mm, sub "
                        f"lungimea minimă {rules.wall_min_length:.0f} mm, ignorat.")
    else:
        return _WallAxis(*_canonical_axis(rect.start, rect.end, rules.point_tolerance), rect.width)

    return None


def _try_merge(wall_a: _WallAxis, wall_b: _WallAxis, rules: RecognitionRules) -> _WallAxis | None:
    """Unește doi pereți coliniari consecutivi (aceeași axă și grosime în point_tolerance, paraleli în
    parallel_tolerance_deg, un capăt comun în point_tolerance) sau None"""
    tol = rules.point_tolerance

    if (abs(wall_a.thickness - wall_b.thickness) > tol
            or _angle_diff_deg(_direction_deg(wall_a.start, wall_a.end),
                               _direction_deg(wall_b.start, wall_b.end)) > rules.parallel_tolerance_deg
            or _line_distance(wall_b.start, wall_a.start, wall_a.end) > tol
            or _line_distance(wall_b.end, wall_a.start, wall_a.end) > tol
            or not any(_dist(p_a, p_b) <= tol for p_a in (wall_a.start, wall_a.end)
                       for p_b in (wall_b.start, wall_b.end))):
        return None

    u_x = (wall_a.end[0] - wall_a.start[0]) / wall_a.length
    u_y = (wall_a.end[1] - wall_a.start[1]) / wall_a.length
    ends = sorted((wall_a.start, wall_a.end, wall_b.start, wall_b.end),
                  key = lambda pnt: (pnt[0] - wall_a.start[0]) * u_x + (pnt[1] - wall_a.start[1]) * u_y)
    thickness = ((wall_a.thickness * wall_a.length + wall_b.thickness * wall_b.length)
                 / (wall_a.length + wall_b.length))
    return _WallAxis(*_canonical_axis(ends[0], ends[-1], tol), thickness)


def _merge_walls(walls: list[_WallAxis], rules: RecognitionRules) -> list[_WallAxis]:
    """unește repetat perechile de pereți coliniari consecutivi până nu mai există niciuna"""
    items  = list(walls)
    merged = True

    while merged:
        merged = False

        for idx_a in range(len(items)):
            for idx_b in range(idx_a + 1, len(items)):
                joined = _try_merge(items[idx_a], items[idx_b], rules)
                if joined is not None:
                    items[idx_a] = joined
                    del items[idx_b]
                    merged = True
                    break
            if merged:
                break

    return items


def _recognize_walls(drawing: Drawing2D, layers: set[str], rules: RecognitionRules,
                     warnings: list[str]) -> list[_WallAxis]:
    """Regula 2 (pereți)

    -   contururile dreptunghiulare fără goluri, cu latura scurtă în [wall_min_thickness,
        wall_max_thickness] [mm], devin pereți direct (_wall_from_rectangle);
    -   laturile celorlalte contururi (de ex. conturul exterior și cel interior al unui inel de pereți), polilinii deschise și segmentele libere sunt fețe care se
        împerechează pe fiecare layer (_pair_faces); fețele fără pereche devin avertismente;
    -   pereții coliniari consecutivi se unesc (_merge_walls).
    """
    ent   = _collect(drawing, layers, rules.point_tolerance, _LABEL["wall"], warnings)
    walls = []
    faces = list(ent.segments) + [seg for pts, layer in ent.paths for seg in _path_edges(pts, layer)]

    for contour in ent.contours:
        rect = None if contour.holes else _rectangle_axis(contour.points, rules.parallel_tolerance_deg)

        if rect is not None and rules.wall_min_thickness <= rect.width <= rules.wall_max_thickness:
            wall = _wall_from_rectangle(contour, rect, rules, warnings)
            walls.extend([wall] if wall is not None else [])
        else:
            for ring in (contour.points, *contour.holes):
                faces.extend(_ring_edges(ring, contour.layer))

    for layer in sorted({face.layer for face in faces}):
        paired, unpaired = _pair_faces(sorted((f for f in faces if f.layer == layer), key = _segment_key), rules)
        walls.extend(paired)

        for face in unpaired:
            warnings.append(f"Perete: linie fără față opusă pe layerul '{layer}', de la {_fmt(face.start)} "
                            f"la {_fmt(face.end)} (lungime {face.length:.0f} mm), ignorată.")

    return _merge_walls(walls, rules)


# ----------------------------------------------------------------------------------------------
# Grinzi
# ----------------------------------------------------------------------------------------------

def _recognize_beams(drawing: Drawing2D, layers: set[str], rules: RecognitionRules,
                     warnings: list[str]) -> list[tuple[Point2, Point2, float]]:
    """Regula 3 (grinzi): returnează (start, end, lățime [mm])

    -   segmentele libere și fiecare segment al poliliniilor deschise sunt axe, cu lățimea
        rules.beam_width (vârfurile intermediare ale poliliniilor se păstrează: pot marca reazeme);
    -   contururile dreptunghiulare: axa pe mijlocul laturilor scurte, lățimea = latura scurtă;
    -   pătratele, contururile nedreptunghiulare și cele cu goluri devin avertismente.
    """
    ent   = _collect(drawing, layers, rules.point_tolerance, _LABEL["beam"], warnings)
    tol   = rules.point_tolerance
    axes  = list(ent.segments) + [seg for pts, layer in ent.paths for seg in _path_edges(pts, layer)]
    beams = [(*_canonical_axis(seg.start, seg.end, tol), rules.beam_width) for seg in axes]

    for contour in ent.contours:
        rect  = None if contour.holes else _rectangle_axis(contour.points, rules.parallel_tolerance_deg)
        where = f"pe layerul '{contour.layer}' din jurul {_fmt(_ring_center(contour.points))}"

        if rect is None:
            warnings.append(f"Grindă: contur ({contour.source}) {where} nu este un dreptunghi fără goluri, ignorat.")
        elif rect.length - rect.width <= tol:
            warnings.append(f"Grindă: contur pătrat ({rect.width:.0f} x {rect.length:.0f} mm) {where}; "
                            f"direcția grinzii este ambiguă, ignorat.")
        else:
            beams.append((*_canonical_axis(rect.start, rect.end, tol), rect.width))

    return beams


# ----------------------------------------------------------------------------------------------
# Plăci
# ----------------------------------------------------------------------------------------------

def _segment_distance(pnt: Point2, p_a: Point2, p_b: Point2) -> float:
    """distanța de la pnt la segmentul p_a - p_b [mm]"""
    length_sq = (p_b[0] - p_a[0]) ** 2 + (p_b[1] - p_a[1]) ** 2

    if length_sq < _EPS:
        return _dist(pnt, p_a)

    par = ((pnt[0] - p_a[0]) * (p_b[0] - p_a[0]) + (pnt[1] - p_a[1]) * (p_b[1] - p_a[1])) / length_sq
    par = min(1.0, max(0.0, par))
    return _dist(pnt, (p_a[0] + par * (p_b[0] - p_a[0]), p_a[1] + par * (p_b[1] - p_a[1])))


def _position(pnt: Point2, polygon: Ring, tolerance: float) -> int:
    """poziția punctului față de poligon: 1 = în interior, 0 = pe contur (în tolerance [mm]), -1 = în exterior"""
    pts = list(polygon)

    if any(_segment_distance(pnt, p_1, p_2) <= tolerance for p_1, p_2 in zip(pts, pts[1:] + pts[:1])):
        return 0

    return 1 if _point_in_polygon(pnt, polygon) else -1


def _contains(outer: Ring, inner: Ring, tolerance: float) -> bool:
    """True dacă inner are aria mai mică, niciun vârf în exteriorul lui outer și cel puțin unul în interior
    (vârfurile pe contur, în tolerance [mm], sunt admise)"""
    positions = [_position(pnt, outer, tolerance) for pnt in inner]
    return abs(_signed_area(inner)) < abs(_signed_area(outer)) and -1 not in positions and 1 in positions


def _recognize_slabs(drawing: Drawing2D, layers: set[str], rules: RecognitionRules,
                     warnings: list[str]) -> list[tuple[Ring, tuple[Ring, ...]]]:
    """Regula 4 (plăci): returnează (contur, goluri)

    -   fiecare contur închis care nu este în interiorul altuia este o placă (cu golurile hașurii);
    -   un contur aflat complet în interiorul exact unui alt contur devine gol al acestuia;
    -   contururile incluse în mai multe contururi (placă în gol), suprapunerile parțiale,
        segmentele și poliliniile deschise devin avertismente.
    """
    tol = rules.point_tolerance
    ent = _collect(drawing, layers, tol, _LABEL["slab"], warnings)
    _warn_open_slab_entities(ent, warnings)

    contours = ent.contours
    parents  = [[idx for idx, other in enumerate(contours) if idx != pos and other.layer == cnt.layer
                 and _contains(other.points, cnt.points, tol)] for pos, cnt in enumerate(contours)]
    _warn_partial_overlaps(contours, parents, tol, warnings)

    slabs = []

    for pos, contour in enumerate(contours):
        if parents[pos]:
            if len(parents[pos]) > 1:
                warnings.append(f"Placă: conturul de pe layerul '{contour.layer}' din jurul "
                                f"{_fmt(_ring_center(contour.points))} este în interiorul unui gol "
                                f"(incluziune multiplă); interpretarea este ambiguă, ignorat.")
            continue

        holes = list(contour.holes)

        for child, child_parents in enumerate(parents):
            if child_parents == [pos] and not any(_same_ring(contours[child].points, hole, tol) for hole in holes):
                holes.append(contours[child].points)

        slabs.append((contour.points, tuple(holes)))

    return slabs


def _warn_open_slab_entities(ent: _Entities, warnings: list[str]) -> None:
    for seg in ent.segments:
        warnings.append(f"Placă: segment liber pe layerul '{seg.layer}', de la {_fmt(seg.start)} la "
                        f"{_fmt(seg.end)}; plăcile se recunosc doar din contururi închise, ignorat.")

    for pts, layer in ent.paths:
        warnings.append(f"Placă: polilinie deschisă pe layerul '{layer}', de la {_fmt(pts[0])} la "
                        f"{_fmt(pts[-1])}; plăcile se recunosc doar din contururi închise, ignorată.")


def _warn_partial_overlaps(contours: list[_Contour], parents: list[list[int]], tolerance: float,
                           warnings: list[str]) -> None:
    """avertisment pentru contururile de pe același layer, fără incluziune, cu vârfuri unul în interiorul
    celuilalt (vârfurile pe contur, în tolerance [mm], nu contează: plăcile alăturate nu se semnalează)"""
    for pos_a, cnt_a in enumerate(contours):
        for pos_b in range(pos_a + 1, len(contours)):
            cnt_b = contours[pos_b]

            if cnt_a.layer != cnt_b.layer or pos_a in parents[pos_b] or pos_b in parents[pos_a]:
                continue

            inside = [_position(pnt, cnt_a.points, tolerance) == 1 for pnt in cnt_b.points]
            inside += [_position(pnt, cnt_b.points, tolerance) == 1 for pnt in cnt_a.points]

            if any(inside):
                warnings.append(f"Placă: contururile de pe layerul '{cnt_a.layer}' din jurul "
                                f"{_fmt(_ring_center(cnt_a.points))} și {_fmt(_ring_center(cnt_b.points))} "
                                f"se suprapun parțial; verificați plăcile create.")


# ----------------------------------------------------------------------------------------------
# Funcția publică
# ----------------------------------------------------------------------------------------------

def recognize(drawing: Drawing2D, rules: RecognitionRules, level: Level) -> StructuralModel:
    """Recunoaște stâlpii, pereții, grinzile și plăcile dintr-o planșă 2D

    Args:
        drawing: planșa, toate coordonatele în mm
        rules:   regulile de recunoaștere (layere, limite și toleranțe în mm / grade)
        level:   nivelul atribuit tuturor elementelor

    Returns:
        modelul structural: elementele sortate după poziție (y descrescător, apoi x crescător;
        punctul de referință = centrul de greutate al conturului sau mijlocul axei) și numerotate
        S1.. (stâlpi), P1.. (pereți), G1.. (grinzi), PL1.. (plăci); avertismentele în română.

    Domeniu: geometrie plană; arcele trebuie discretizate de sursă. Layerele care nu se potrivesc
    nicio regulă se ignoră. Avertismentele din drawing.warnings (ale sursei) NU se copiază în model.
    """
    warnings: list[str] = []
    found = drawing.layers
    by_type = {element: rules.layers_for(element, found) for element in _LABEL}

    if not any(by_type.values()):
        listed = ", ".join(f"'{layer}'" for layer in sorted(found)) if found else "niciunul (planșă goală)"
        warnings.append(f"Planșă: niciun layer nu se potrivește cu regulile de recunoaștere. Layere găsite: {listed}.")

    columns = sorted(_recognize_columns(drawing, by_type["column"], rules, warnings),
                     key = _ring_center_key)
    walls   = sorted(_recognize_walls(drawing, by_type["wall"], rules, warnings),
                     key = lambda wall: _sort_key(_mid(wall.start, wall.end)))
    beams   = sorted(_recognize_beams(drawing, by_type["beam"], rules, warnings),
                     key = lambda beam: _sort_key(_mid(beam[0], beam[1])))
    slabs   = sorted(_recognize_slabs(drawing, by_type["slab"], rules, warnings),
                     key = lambda slab: _ring_center_key(slab[0]))

    return StructuralModel(
        columns  = [Column(f"S{nr}", outline, level) for nr, outline in enumerate(columns, start = 1)],
        walls    = [Wall(f"P{nr}", wall.start, wall.end, wall.thickness, level)
                    for nr, wall in enumerate(walls, start = 1)],
        beams    = [Beam(f"G{nr}", start, end, width, rules.beam_depth, level)
                    for nr, (start, end, width) in enumerate(beams, start = 1)],
        slabs    = [Slab(f"PL{nr}", outline, holes, rules.slab_thickness, level)
                    for nr, (outline, holes) in enumerate(slabs, start = 1)],
        warnings = warnings)


def _ring_center_key(ring: Ring) -> tuple[float, float]:
    return _sort_key(_ring_center(ring))
