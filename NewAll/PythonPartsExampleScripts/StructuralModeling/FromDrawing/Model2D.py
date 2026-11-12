"""Model 2D neutru al unei planșe (contract între surse și recunoaștere)

Toate sursele de planșe (selecție din modelul Allplan, fișier DXF etc.) produc un Drawing2D.
Coordonatele sunt ÎNTOTDEAUNA în mm; conversia unităților se face în sursă.
Modulul nu depinde de Allplan.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Point2 = tuple[float, float]


@dataclass(frozen=True)
class Segment2D:
    """Segment de dreaptă pe un layer"""

    start: Point2
    end  : Point2
    layer: str

    @property
    def length(self) -> float:
        """lungimea [mm]"""
        return ((self.end[0] - self.start[0]) ** 2 + (self.end[1] - self.start[1]) ** 2) ** 0.5


@dataclass(frozen=True)
class Polyline2D:
    """Polilinie (arcele sunt deja discretizate de sursă). Dacă closed = True,
    ultimul punct NU repetă primul punct."""

    points: tuple[Point2, ...]
    closed: bool
    layer : str

    def segments(self) -> list[Segment2D]:
        """segmentele poliliniei, inclusiv segmentul de închidere"""
        pts = list(self.points)

        if self.closed and len(pts) > 2:
            pts.append(pts[0])

        return [Segment2D(p1, p2, self.layer) for p1, p2 in zip(pts, pts[1:])]


@dataclass(frozen=True)
class Hatch2D:
    """Hașură / umplutură: contur exterior și goluri, toate închise"""

    outer: tuple[Point2, ...]
    holes: tuple[tuple[Point2, ...], ...]
    layer: str


@dataclass(frozen=True)
class Drawing2D:
    """Conținutul 2D al unei planșe (sau al unei selecții dintr-o planșă), în mm"""

    segments : tuple[Segment2D, ...]  = ()
    polylines: tuple[Polyline2D, ...] = ()
    hatches  : tuple[Hatch2D, ...]    = ()
    warnings : tuple[str, ...]        = field(default = ())

    @property
    def layers(self) -> set[str]:
        """toate layerele prezente"""
        return {ent.layer for ent in (*self.segments, *self.polylines, *self.hatches)}

    def on_layers(self, layers: set[str]) -> Drawing2D:
        """Sub-planșa care conține doar entitățile de pe layerele date"""
        return Drawing2D(tuple(ent for ent in self.segments if ent.layer in layers),
                         tuple(ent for ent in self.polylines if ent.layer in layers),
                         tuple(ent for ent in self.hatches if ent.layer in layers),
                         self.warnings)
