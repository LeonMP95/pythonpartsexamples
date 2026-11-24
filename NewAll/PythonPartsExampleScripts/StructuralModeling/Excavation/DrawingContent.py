"""Conținutul neutru al planșei de săpătură (primitive de desen, fără Allplan sau Revit)

Convenții:
- Toate coordonatele și lungimile sunt în mm.
- Coordonatele unui element sunt în sistemul LOCAL al grupului (DrawingGroup): coordonate de model pentru plan
  (de ex. scale = 100 pentru 1:100) sau coordonate de foaie pentru secțiuni desenate la scară, tabele și note
  (scale = 1).
- Punctul de pe foaie = group.origin + punct_local / group.scale.
- Înălțimile de text (Text.height) sunt ÎNTOTDEAUNA în mm pe foaie, indiferent de scara grupului.
- Stilul este un nume simbolic (STYLES); fiecare program îl traduce în pen, culoare, layer, tip de linie.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, fields, is_dataclass

Point2 = tuple[float, float]
Bounds = tuple[float, float, float, float]

STYLES = frozenset({
    "contur_baza", "cap_taluz", "fundatie", "teren", "cota", "text", "tabel", "hasura_sapatura", "axa",
})
TEXT_ALIGNS = frozenset({"left", "center", "right"})

JSON_DECIMALS = 1                 # rotunjire la 0,1 mm în JSON
TEXT_WIDTH_FACTOR = 0.8           # lățimea aproximativă a unui caracter / înălțimea textului
TABLE_TEXT_HEIGHT_MM = 2.5        # înălțimea implicită a textului din tabel [mm pe foaie]
TABLE_CELL_PADDING_MM = 1.5       # distanța textului față de marginea stângă a celulei [mm pe foaie]
DIM_TEXT_HEIGHT_MM = 2.5          # înălțimea textului de cotă [mm pe foaie]
ELEVATION_SYMBOL_MM = 3.0         # mărimea simbolului de cotă de nivel [mm pe foaie]
MM_PER_CM = 10.0
MM_PER_M = 1000.0


# ---------------------------------------------------------------- utilitare

def _as_point(point) -> Point2:
    """convertește o pereche de numere într-un punct (tuple) și verifică valorile"""
    try:
        x_mm, y_mm = (float(value) for value in point)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Punct invalid: {point!r} (se așteaptă două numere)") from error
    if not (math.isfinite(x_mm) and math.isfinite(y_mm)):
        raise ValueError(f"Punct cu coordonate nefinite: {point!r}")
    return (x_mm, y_mm)


def _as_points(points, min_count: int, what: str) -> tuple[Point2, ...]:
    """convertește o listă de puncte în tuple și verifică numărul minim"""
    result = tuple(_as_point(point) for point in points)
    if len(result) < min_count:
        raise ValueError(f"{what}: sunt necesare cel puțin {min_count} puncte, s-au primit {len(result)}")
    return result


def _check_style(style: str) -> None:
    if style not in STYLES:
        raise ValueError(f"Stil necunoscut: {style!r}. Stiluri permise: {', '.join(sorted(STYLES))}")


def _check_positive(value: float, what: str) -> None:
    if not (isinstance(value, (int, float)) and math.isfinite(value) and value > 0):
        raise ValueError(f"{what} trebuie să fie un număr pozitiv, s-a primit {value!r}")


def _points_bounds(points, scale: float) -> Bounds:
    """dreptunghiul de încadrare al punctelor, împărțite la scară (mm pe foaie)"""
    xs = [point[0] / scale for point in points]
    ys = [point[1] / scale for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def merge_bounds(bounds_list) -> Bounds:
    """reuniunea dreptunghiurilor de încadrare"""
    bounds_list = list(bounds_list)
    if not bounds_list:
        raise ValueError("Nu există elemente pentru calculul dreptunghiului de încadrare")
    return (min(b[0] for b in bounds_list), min(b[1] for b in bounds_list),
            max(b[2] for b in bounds_list), max(b[3] for b in bounds_list))


def text_width_mm(text: str, height_mm: float) -> float:
    """lățimea aproximativă a textului pe foaie [mm] (cel mai lung rând)"""
    longest = max((len(line) for line in text.split("\n")), default=0)
    return longest * height_mm * TEXT_WIDTH_FACTOR


def format_decimal(value: float, decimals: int) -> str:
    """număr cu virgulă zecimală (convenția românească)"""
    return f"{value:.{decimals}f}".replace(".", ",")


def format_elevation_m(z_mm: float) -> str:
    """cota de nivel în metri, cu semn: ±0,00 / +1,25 / -2,40"""
    z_m = round(z_mm / MM_PER_M, 2)
    if z_m == 0:
        return "±0,00"
    sign = "+" if z_m > 0 else "-"
    return sign + format_decimal(abs(z_m), 2)


# ---------------------------------------------------------------- primitive

@dataclass(frozen=True)
class Line:
    """Segment de dreaptă"""

    start: Point2
    end  : Point2
    style: str = "contur_baza"

    def __post_init__(self):
        object.__setattr__(self, "start", _as_point(self.start))
        object.__setattr__(self, "end", _as_point(self.end))
        _check_style(self.style)

    def bounds(self, scale: float = 1.0) -> Bounds:
        """dreptunghiul de încadrare pe foaie [mm], relativ la originea grupului"""
        return _points_bounds((self.start, self.end), scale)


@dataclass(frozen=True)
class Polyline:
    """Polilinie; dacă closed = True, ultimul punct NU repetă primul punct"""

    points: tuple[Point2, ...]
    closed: bool = False
    style : str = "contur_baza"

    def __post_init__(self):
        object.__setattr__(self, "points", _as_points(self.points, 2, "Polilinie"))
        _check_style(self.style)

    def bounds(self, scale: float = 1.0) -> Bounds:
        return _points_bounds(self.points, scale)


@dataclass(frozen=True)
class Hatch:
    """Suprafață hașurată: contur exterior și goluri (fiecare închis, fără repetarea primului punct)"""

    outer: tuple[Point2, ...]
    holes: tuple[tuple[Point2, ...], ...] = ()
    style: str = "hasura_sapatura"

    def __post_init__(self):
        object.__setattr__(self, "outer", _as_points(self.outer, 3, "Hașură (contur exterior)"))
        holes = tuple(_as_points(hole, 3, "Hașură (gol)") for hole in self.holes)
        object.__setattr__(self, "holes", holes)
        _check_style(self.style)

    def bounds(self, scale: float = 1.0) -> Bounds:
        return _points_bounds(self.outer, scale)


@dataclass(frozen=True)
class Text:
    """Text; pos = punctul de inserție (linia de bază, după align), height în mm pe foaie, rotation în grade"""

    pos     : Point2
    text    : str
    height  : float = TABLE_TEXT_HEIGHT_MM
    rotation: float = 0.0
    align   : str = "left"
    style   : str = "text"

    def __post_init__(self):
        object.__setattr__(self, "pos", _as_point(self.pos))
        object.__setattr__(self, "text", str(self.text))
        _check_positive(self.height, "Înălțimea textului")
        object.__setattr__(self, "rotation", float(self.rotation))
        if self.align not in TEXT_ALIGNS:
            raise ValueError(f"Aliniere necunoscută: {self.align!r}. Permise: {', '.join(sorted(TEXT_ALIGNS))}")
        _check_style(self.style)

    def bounds(self, scale: float = 1.0) -> Bounds:
        """încadrare aproximativă (lățimea din TEXT_WIDTH_FACTOR), ținând cont de rotație"""
        width = text_width_mm(self.text, self.height)
        lines = self.text.count("\n") + 1
        shift = {"left": 0.0, "center": -width / 2, "right": -width}[self.align]
        corners = [(shift, 0.0), (shift + width, 0.0), (shift, lines * self.height),
                   (shift + width, lines * self.height)]
        angle = math.radians(self.rotation)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        base_x, base_y = self.pos[0] / scale, self.pos[1] / scale
        rotated = [(base_x + x * cos_a - y * sin_a, base_y + x * sin_a + y * cos_a) for x, y in corners]
        return _points_bounds(rotated, 1.0)


@dataclass(frozen=True)
class LinearDim:
    """Cotă liniară între p1 și p2; linia de cotă e decalată perpendicular cu offset (unități locale,
    pozitiv spre stânga direcției p1 -> p2). Textul implicit = lungimea în cm."""

    p1           : Point2
    p2           : Point2
    offset       : float = 0.0
    text_override: str | None = None
    style        : str = "cota"

    def __post_init__(self):
        object.__setattr__(self, "p1", _as_point(self.p1))
        object.__setattr__(self, "p2", _as_point(self.p2))
        object.__setattr__(self, "offset", float(self.offset))
        if self.length == 0:
            raise ValueError(f"Cotă de lungime zero între {self.p1} și {self.p2}")
        _check_style(self.style)

    @property
    def length(self) -> float:
        """lungimea cotată [mm, unități locale]"""
        return math.hypot(self.p2[0] - self.p1[0], self.p2[1] - self.p1[1])

    def display_text(self) -> str:
        """textul afișat: text_override sau lungimea în cm"""
        if self.text_override is not None:
            return self.text_override
        return format_decimal(self.length / MM_PER_CM, 0)

    def dim_line_points(self) -> tuple[Point2, Point2]:
        """capetele liniei de cotă (decalate cu offset)"""
        normal_x = -(self.p2[1] - self.p1[1]) / self.length
        normal_y = (self.p2[0] - self.p1[0]) / self.length
        dx, dy = normal_x * self.offset, normal_y * self.offset
        return ((self.p1[0] + dx, self.p1[1] + dy), (self.p2[0] + dx, self.p2[1] + dy))

    def bounds(self, scale: float = 1.0) -> Bounds:
        """încadrare: punctele cotate, linia de cotă și o margine pentru text"""
        box = _points_bounds((self.p1, self.p2) + self.dim_line_points(), scale)
        margin = DIM_TEXT_HEIGHT_MM * 2
        return (box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin)


@dataclass(frozen=True)
class ElevationMark:
    """Cotă de nivel: pos = vârful simbolului, z în mm (afișat în m), label = text înainte de valoare"""

    pos  : Point2
    z    : float
    label: str = ""
    style: str = "cota"

    def __post_init__(self):
        object.__setattr__(self, "pos", _as_point(self.pos))
        if not math.isfinite(float(self.z)):
            raise ValueError(f"Cotă de nivel nefinită: {self.z!r}")
        object.__setattr__(self, "z", float(self.z))
        _check_style(self.style)

    def display_text(self) -> str:
        """de exemplu „CF -2,40” sau „+0,15”"""
        value = format_elevation_m(self.z)
        return f"{self.label} {value}" if self.label else value

    def bounds(self, scale: float = 1.0) -> Bounds:
        base_x, base_y = self.pos[0] / scale, self.pos[1] / scale
        width = max(ELEVATION_SYMBOL_MM, text_width_mm(self.display_text(), DIM_TEXT_HEIGHT_MM))
        return (base_x - ELEVATION_SYMBOL_MM, base_y,
                base_x + width, base_y + ELEVATION_SYMBOL_MM + DIM_TEXT_HEIGHT_MM)


@dataclass(frozen=True)
class Table:
    """Tabel; origin = colțul stânga-sus, rândurile cresc în jos. Dimensiunile sunt în unități locale
    (de regulă mm pe foaie, grup cu scale = 1)."""

    origin     : Point2
    rows       : tuple[tuple[str, ...], ...]
    col_widths : tuple[float, ...]
    row_height : float
    text_height: float = TABLE_TEXT_HEIGHT_MM
    style      : str = "tabel"

    def __post_init__(self):
        object.__setattr__(self, "origin", _as_point(self.origin))
        object.__setattr__(self, "col_widths", tuple(float(width) for width in self.col_widths))
        object.__setattr__(self, "rows", tuple(tuple(str(cell) for cell in row) for row in self.rows))
        self._validate()

    def _validate(self) -> None:
        if not self.col_widths:
            raise ValueError("Tabelul trebuie să aibă cel puțin o coloană")
        for width in self.col_widths:
            _check_positive(width, "Lățimea coloanei")
        _check_positive(self.row_height, "Înălțimea rândului")
        _check_positive(self.text_height, "Înălțimea textului din tabel")
        for index, row in enumerate(self.rows, start=1):
            if len(row) > len(self.col_widths):
                raise ValueError(f"Rândul {index} al tabelului are {len(row)} celule, "
                                 f"dar tabelul are {len(self.col_widths)} coloane")
        _check_style(self.style)

    @property
    def width(self) -> float:
        return sum(self.col_widths)

    @property
    def height(self) -> float:
        return self.row_height * len(self.rows)

    def bounds(self, scale: float = 1.0) -> Bounds:
        x0, y0 = self.origin
        return _points_bounds(((x0, y0 - self.height), (x0 + self.width, y0)), scale)

    def to_primitives(self) -> list:
        """desface tabelul în linii (orizontale apoi verticale) și texte (celulele nevide, rând cu rând)"""
        return self._grid_lines() + self._cell_texts()

    def _grid_lines(self) -> list[Line]:
        x0, y0 = self.origin
        horizontal = [Line((x0, y0 - i * self.row_height), (x0 + self.width, y0 - i * self.row_height), self.style)
                      for i in range(len(self.rows) + 1)]
        column_x = [x0 + sum(self.col_widths[:j]) for j in range(len(self.col_widths) + 1)]
        vertical = [Line((x, y0), (x, y0 - self.height), self.style) for x in column_x]
        return horizontal + vertical

    def _cell_texts(self) -> list[Text]:
        x0, y0 = self.origin
        baseline_offset = (self.row_height - self.text_height) / 2
        texts = []
        for i, row in enumerate(self.rows):
            baseline_y = y0 - (i + 1) * self.row_height + baseline_offset
            for j, cell in enumerate(row):
                if cell:
                    cell_x = x0 + sum(self.col_widths[:j]) + TABLE_CELL_PADDING_MM
                    texts.append(Text((cell_x, baseline_y), cell, self.text_height, style="text"))
        return texts


PRIMITIVE_TYPES = (Line, Polyline, Hatch, Text, LinearDim, ElevationMark, Table)


# ---------------------------------------------------------------- grupuri și desen

@dataclass(frozen=True)
class DrawingGroup:
    """Grup de primitive (plan, o secțiune, tabel, note, cartuș).
    origin = poziția pe foaie [mm] a originii locale; scale = numitorul scării (100 pentru 1:100)."""

    name  : str
    items : tuple = ()
    origin: Point2 = (0.0, 0.0)
    scale : float = 1.0

    def __post_init__(self):
        if not str(self.name).strip():
            raise ValueError("Grupul de desen trebuie să aibă un nume")
        items = tuple(self.items)
        for item in items:
            if not isinstance(item, PRIMITIVE_TYPES):
                raise ValueError(f"Element necunoscut în grupul {self.name!r}: {type(item).__name__}")
        object.__setattr__(self, "items", items)
        object.__setattr__(self, "origin", _as_point(self.origin))
        _check_positive(self.scale, f"Scara grupului {self.name!r}")

    def local_bounds(self) -> Bounds:
        """încadrarea pe foaie [mm], relativ la originea grupului"""
        return merge_bounds(item.bounds(self.scale) for item in self.items)

    def sheet_bounds(self) -> Bounds:
        """încadrarea pe foaie [mm], în coordonatele foii"""
        x_min, y_min, x_max, y_max = self.local_bounds()
        ox, oy = self.origin
        return (x_min + ox, y_min + oy, x_max + ox, y_max + oy)

    def size(self) -> tuple[float, float]:
        """lățimea și înălțimea pe foaie [mm]"""
        x_min, y_min, x_max, y_max = self.local_bounds()
        return (x_max - x_min, y_max - y_min)

    def moved_to(self, origin: Point2) -> DrawingGroup:
        """copie a grupului cu altă origine pe foaie"""
        return DrawingGroup(self.name, self.items, origin, self.scale)


@dataclass(frozen=True)
class Drawing:
    """Conținutul complet al planșei"""

    groups: tuple[DrawingGroup, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "groups", tuple(self.groups))

    def to_dict(self) -> dict:
        """grupurile sortate stabil după nume; ordinea elementelor din grup se păstrează (ordinea de desen)"""
        ordered = sorted(self.groups, key=lambda group: group.name)
        return {"groups": [_to_plain(group) for group in ordered]}

    def to_json(self) -> str:
        """JSON determinist: chei sortate, numere rotunjite la 0,1 mm"""
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _round_number(value: float):
    rounded = round(float(value), JSON_DECIMALS)
    return 0.0 if rounded == 0 else rounded          # fără „-0.0”


def _to_plain(value):
    """conversie recursivă în tipuri JSON (dataclass -> dict cu „type”)"""
    if is_dataclass(value):
        plain = {"type": type(value).__name__}
        plain.update({field.name: _to_plain(getattr(value, field.name)) for field in fields(value)})
        return plain
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return _round_number(value)
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    raise ValueError(f"Valoare neserializabilă în desen: {value!r}")
