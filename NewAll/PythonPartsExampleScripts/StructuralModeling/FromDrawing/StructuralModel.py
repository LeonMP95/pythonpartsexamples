"""Model structural neutru (contract între recunoaștere, crearea în Allplan și modulele de armare)

Modulele de armare pot depinde de acest fișier; acest fișier nu depinde de nimic din proiect.
Unități: mm. Modulul nu depinde de Allplan.

Convenții de nivel (pentru un etaj):
    -   stâlpii și pereții merg de la z_bottom la z_top;
    -   grinzile și plăcile au fața superioară la z_top.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from StructuralModeling.FromDrawing.Model2D import Point2


class StructuralModelError(ValueError):
    """Date structurale invalide"""


@dataclass(frozen=True)
class Level:
    """Un etaj: cotele absolute jos / sus [mm]"""

    name    : str
    z_bottom: float
    z_top   : float

    def __post_init__(self):
        if self.z_top <= self.z_bottom:
            raise StructuralModelError(f"Nivelul '{self.name}': cota de sus ({self.z_top}) trebuie să fie "
                                       f"mai mare decât cota de jos ({self.z_bottom})")

    @property
    def height(self) -> float:
        """înălțimea etajului [mm]"""
        return self.z_top - self.z_bottom


def _bbox(points: tuple[Point2, ...]) -> tuple[float, float, float, float]:
    xs = [pnt[0] for pnt in points]
    ys = [pnt[1] for pnt in points]
    return min(xs), min(ys), max(xs), max(ys)


@dataclass(frozen=True)
class Column:
    """Stâlp cu secțiune poligonală (contur în plan, sens oarecare)"""

    id     : str
    outline: tuple[Point2, ...]
    level  : Level

    @property
    def size(self) -> tuple[float, float]:
        """dimensiunile dreptunghiului încadrator (pe X, pe Y) [mm]"""
        x_min, y_min, x_max, y_max = _bbox(self.outline)
        return x_max - x_min, y_max - y_min

    @property
    def centroid(self) -> Point2:
        """centrul de greutate al conturului"""
        area = cx = cy = 0.0
        pts  = list(self.outline)

        for (x_1, y_1), (x_2, y_2) in zip(pts, pts[1:] + pts[:1]):
            cross = x_1 * y_2 - x_2 * y_1
            area += cross
            cx   += (x_1 + x_2) * cross
            cy   += (y_1 + y_2) * cross

        if abs(area) < 1e-9:
            x_min, y_min, x_max, y_max = _bbox(self.outline)
            return (x_min + x_max) / 2, (y_min + y_max) / 2

        return cx / (3 * area), cy / (3 * area)


@dataclass(frozen=True)
class Wall:
    """Perete definit prin axă și grosime (grosimea centrată pe axă)"""

    id       : str
    start    : Point2
    end      : Point2
    thickness: float
    level    : Level


@dataclass(frozen=True)
class Beam:
    """Grindă definită prin axă, lățime și înălțime (fața superioară la cota de sus a nivelului)"""

    id    : str
    start : Point2
    end   : Point2
    width : float
    depth : float
    level : Level


@dataclass(frozen=True)
class Slab:
    """Placă cu contur exterior și goluri (fața superioară la cota de sus a nivelului)"""

    id       : str
    outline  : tuple[Point2, ...]
    holes    : tuple[tuple[Point2, ...], ...]
    thickness: float
    level    : Level


@dataclass
class StructuralModel:
    """Elementele recunoscute pentru un etaj, plus avertismentele de recunoaștere"""

    columns : list[Column] = field(default_factory = list)
    walls   : list[Wall]   = field(default_factory = list)
    beams   : list[Beam]   = field(default_factory = list)
    slabs   : list[Slab]   = field(default_factory = list)
    warnings: list[str]    = field(default_factory = list)

    @property
    def element_count(self) -> int:
        """numărul total de elemente"""
        return len(self.columns) + len(self.walls) + len(self.beams) + len(self.slabs)

    def summary(self) -> str:
        """rezumat pe o linie"""
        return (f"{len(self.columns)} stâlpi, {len(self.walls)} pereți, {len(self.beams)} grinzi, "
                f"{len(self.slabs)} plăci, {len(self.warnings)} avertismente")
