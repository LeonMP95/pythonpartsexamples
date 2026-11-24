"""Așezarea grupurilor de desen pe foaie (format, margini, cartuș, note) - fără Allplan sau Revit

Algoritm simplu pe rânduri: grupurile se așază în ordinea primită, de la stânga-sus spre dreapta;
când un grup nu mai încape pe rând (sau ar suprapune cartușul), se trece la rândul următor.
Grupurile care nu încap pe foaie nu se așază și produc un avertisment.
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass

from StructuralModeling.Excavation.DrawingContent import (
    TEXT_WIDTH_FACTOR,
    Bounds,
    DrawingGroup,
    Polyline,
    Table,
    Text,
)

SHEET_FORMATS_MM = {            # dimensiuni ISO 216, orientare orizontală (lățime, înălțime)
    "A0": (1189.0, 841.0),
    "A1": (841.0, 594.0),
    "A2": (594.0, 420.0),
    "A3": (420.0, 297.0),
    "A4": (297.0, 210.0),
}
ORIENTATION_LANDSCAPE = "orizontal"
ORIENTATION_PORTRAIT = "vertical"

DEFAULT_NOTES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ExecutionNotes.txt")
MAX_NOTES_FILE_BYTES = 100 * 1024

TITLE_BLOCK_COLUMN_WIDTHS_MM = (40.0, 140.0)
TITLE_BLOCK_ROW_HEIGHT_MM = 8.0
TITLE_BLOCK_TEXT_HEIGHT_MM = 3.5
NOTES_TEXT_HEIGHT_MM = 2.5
NOTES_LINE_SPACING = 1.6        # distanța dintre rânduri / înălțimea textului
NOTES_TITLE = "NOTE:"
FRAME_GROUP_NAME = "chenar"
TITLE_BLOCK_GROUP_NAME = "cartus"
NOTES_GROUP_NAME = "note"


@dataclass(frozen=True)
class SheetSettings:
    """Formatul foii și marginile [mm]; margin_left_mm include zona de îndosariere"""

    paper_format  : str = "A1"
    orientation   : str = ORIENTATION_LANDSCAPE
    margin_mm     : float = 10.0
    margin_left_mm: float = 20.0
    gap_mm        : float = 10.0

    def __post_init__(self):
        if self.paper_format not in SHEET_FORMATS_MM:
            raise ValueError(f"Format de foaie necunoscut: {self.paper_format!r}. "
                             f"Permise: {', '.join(SHEET_FORMATS_MM)}")
        if self.orientation not in (ORIENTATION_LANDSCAPE, ORIENTATION_PORTRAIT):
            raise ValueError(f"Orientare necunoscută: {self.orientation!r}. "
                             f"Permise: {ORIENTATION_LANDSCAPE}, {ORIENTATION_PORTRAIT}")
        for name in ("margin_mm", "margin_left_mm", "gap_mm"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} nu poate fi negativ")

    def sheet_size(self) -> tuple[float, float]:
        """lățimea și înălțimea foii [mm]"""
        width, height = SHEET_FORMATS_MM[self.paper_format]
        return (width, height) if self.orientation == ORIENTATION_LANDSCAPE else (height, width)

    def frame_bounds(self) -> Bounds:
        """chenarul interior (zona utilă) [mm]"""
        width, height = self.sheet_size()
        return (self.margin_left_mm, self.margin_mm, width - self.margin_mm, height - self.margin_mm)


@dataclass(frozen=True)
class TitleBlock:
    """Datele cartușului (se dau ca parametri, nu se generează)"""

    title       : str
    project     : str
    sheet_number: str
    scale_text  : str
    date        : str

    def rows(self) -> list[list[str]]:
        return [["Proiect", self.project], ["Titlu", self.title], ["Planșa nr.", self.sheet_number],
                ["Scara", self.scale_text], ["Data", self.date]]


@dataclass(frozen=True)
class SheetLayoutResult:
    """Rezultatul așezării: grupurile așezate (cu origin pe foaie), chenarul, cartușul și avertismentele"""

    sheet_size: tuple[float, float]
    groups    : tuple[DrawingGroup, ...]
    unplaced  : tuple[str, ...]
    warnings  : tuple[str, ...]


# ---------------------------------------------------------------- note

def load_notes(path: str = DEFAULT_NOTES_PATH) -> list[str]:
    """citește notele de execuție: un paragraf = o notă (paragrafele separate prin rând gol);
    rândurile care încep cu „#” sunt comentarii. Fișier UTF-8, maxim 100 kB."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Fișierul cu note de execuție nu există: {path}")
    size = os.path.getsize(path)
    if size > MAX_NOTES_FILE_BYTES:
        raise ValueError(f"Fișierul cu note de execuție este prea mare ({size} octeți; "
                         f"maxim {MAX_NOTES_FILE_BYTES} octeți): {path}")
    try:
        with open(path, encoding="utf-8-sig") as notes_file:
            content = notes_file.read()
    except UnicodeDecodeError as error:
        raise ValueError(f"Fișierul cu note de execuție nu este text UTF-8: {path}") from error
    return parse_notes(content)


def parse_notes(content: str) -> list[str]:
    """împarte textul în note (paragrafe); rândurile unui paragraf se unesc cu spațiu"""
    notes, current = [], []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            continue
        if line:
            current.append(line)
        elif current:
            notes.append(" ".join(current))
            current = []
    if current:
        notes.append(" ".join(current))
    return notes


def build_notes_group(notes: list[str], width_mm: float = 180.0,
                      text_height_mm: float = NOTES_TEXT_HEIGHT_MM) -> DrawingGroup:
    """grup cu titlul „NOTE:” și notele numerotate, încadrate la lățimea dată [mm pe foaie]"""
    line_step = text_height_mm * NOTES_LINE_SPACING
    max_chars = max(10, int(width_mm / (text_height_mm * TEXT_WIDTH_FACTOR)))
    lines = [NOTES_TITLE]
    for number, note in enumerate(notes, start=1):
        lines.extend(textwrap.wrap(f"{number}. {note}", max_chars, subsequent_indent="   "))
    items = [Text((0.0, -index * line_step), line, text_height_mm) for index, line in enumerate(lines)]
    return DrawingGroup(NOTES_GROUP_NAME, items)


def build_title_block_group(title_block: TitleBlock) -> DrawingGroup:
    """cartușul ca tabel cu două coloane (etichetă, valoare)"""
    table = Table((0.0, 0.0), title_block.rows(), TITLE_BLOCK_COLUMN_WIDTHS_MM, TITLE_BLOCK_ROW_HEIGHT_MM,
                  TITLE_BLOCK_TEXT_HEIGHT_MM)
    return DrawingGroup(TITLE_BLOCK_GROUP_NAME, [table])


# ---------------------------------------------------------------- așezare

def _overlaps(first: Bounds, second: Bounds) -> bool:
    """suprapunere strictă (atingerea marginilor nu contează)"""
    return first[0] < second[2] and second[0] < first[2] and first[1] < second[3] and second[1] < first[3]


def _place_at(group: DrawingGroup, left: float, top: float) -> DrawingGroup:
    """mută grupul astfel încât colțul stânga-sus al încadrării să fie în (left, top)"""
    x_min, _, _, y_max = group.local_bounds()
    return group.moved_to((left - x_min, top - y_max))


def _place_title_block(title_block: TitleBlock, frame: Bounds) -> DrawingGroup:
    """cartușul în colțul dreapta-jos al chenarului"""
    group = build_title_block_group(title_block)
    width, height = group.size()
    return _place_at(group, frame[2] - width, frame[1] + height)


def _frame_group(settings: SheetSettings) -> DrawingGroup:
    width, height = settings.sheet_size()
    x0, y0, x1, y1 = settings.frame_bounds()
    sheet_edge = Polyline(((0, 0), (width, 0), (width, height), (0, height)), closed=True, style="tabel")
    frame = Polyline(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), closed=True, style="tabel")
    return DrawingGroup(FRAME_GROUP_NAME, [sheet_edge, frame])


class _RowPacker:
    """așezare pe rânduri în chenar, cu obstacole (cartușul)"""

    def __init__(self, frame: Bounds, obstacles: list[Bounds], gap_mm: float):
        self.frame, self.obstacles, self.gap = frame, obstacles, gap_mm
        self.x, self.row_top, self.row_height = frame[0], frame[3], 0.0

    def _fits(self, box: Bounds) -> bool:
        inside = box[0] >= self.frame[0] and box[2] <= self.frame[2] and box[1] >= self.frame[1]
        return inside and not any(_overlaps(box, obstacle) for obstacle in self.obstacles)

    def _next_row(self) -> None:
        self.x = self.frame[0]
        self.row_top -= self.row_height + self.gap
        self.row_height = 0.0

    def place(self, width: float, height: float) -> tuple[float, float] | None:
        """colțul stânga-sus pentru un dreptunghi width x height, sau None dacă nu încape
        (în acest caz starea rândului curent rămâne neschimbată, pentru grupurile următoare)"""
        saved_state = (self.x, self.row_top, self.row_height)
        corner = self._search(width, height)
        if corner is None:
            self.x, self.row_top, self.row_height = saved_state
        return corner

    def _search(self, width: float, height: float) -> tuple[float, float] | None:
        if width > self.frame[2] - self.frame[0]:
            return None
        while self.row_top - height >= self.frame[1]:
            box = (self.x, self.row_top - height, self.x + width, self.row_top)
            if self._fits(box):
                self.obstacles.append(box)
                self.x += width + self.gap
                self.row_height = max(self.row_height, height)
                return (box[0], box[3])
            if self.x == self.frame[0] and self.row_height == 0.0:
                self.row_height = min(height, self.row_top - self.frame[1])   # rândul e blocat: coboară
            self._next_row()
        return None


def layout_sheet(groups: list[DrawingGroup], settings: SheetSettings,
                 title_block: TitleBlock | None = None) -> SheetLayoutResult:
    """așază grupurile (plan, secțiuni, tabel, note) pe foaie, fără suprapuneri"""
    frame = settings.frame_bounds()
    placed = [_frame_group(settings)]
    obstacles: list[Bounds] = []
    if title_block is not None:
        placed.append(_place_title_block(title_block, frame))
        obstacles.append(placed[-1].sheet_bounds())
    packer = _RowPacker(frame, obstacles, settings.gap_mm)
    unplaced, warnings = [], []
    for group in groups:
        width, height = group.size()
        corner = packer.place(width, height)
        if corner is None:
            unplaced.append(group.name)
            warnings.append(f"Grupul „{group.name}” ({width:.0f} x {height:.0f} mm) nu încape pe foaia "
                            f"{settings.paper_format} {settings.orientation}; alegeți un format mai mare "
                            f"sau o scară mai mică.")
        else:
            placed.append(_place_at(group, *corner))
    return SheetLayoutResult(settings.sheet_size(), tuple(placed), tuple(unplaced), tuple(warnings))
