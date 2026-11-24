"""Teste pentru conținutul neutru al planșei (DrawingContent) și așezarea pe foaie (SheetLayout)"""

from __future__ import annotations

import os
import tempfile
import unittest
from itertools import combinations

from StructuralModeling.Excavation.DrawingContent import (
    Drawing,
    DrawingGroup,
    ElevationMark,
    Hatch,
    Line,
    LinearDim,
    Polyline,
    Table,
    Text,
    format_elevation_m,
)
from StructuralModeling.Excavation.SheetLayout import (
    DEFAULT_NOTES_PATH,
    MAX_NOTES_FILE_BYTES,
    SheetSettings,
    TitleBlock,
    build_notes_group,
    layout_sheet,
    load_notes,
    parse_notes,
)

SNAPSHOT_JSON = (
    '{"groups":[{"items":[{"col_widths":[10.0,20.0],"origin":[0.0,0.0],"row_height":5.0,"rows":[["A","1"]],'
    '"style":"tabel","text_height":2.5,"type":"Table"}],"name":"a_tabel","origin":[0.0,0.0],"scale":1.0,'
    '"type":"DrawingGroup"},{"items":[{"closed":true,"points":[[0.0,0.0],[1000.0,0.0],[1000.0,500.0]],'
    '"style":"contur_baza","type":"Polyline"},{"offset":-300.0,"p1":[0.0,0.0],"p2":[1000.0,0.0],"style":"cota",'
    '"text_override":null,"type":"LinearDim"},{"label":"CF","pos":[10.0,10.0],"style":"cota",'
    '"type":"ElevationMark","z":-2400.0}],"name":"plan","origin":[0.0,0.0],"scale":100.0,"type":"DrawingGroup"}]}'
)

TITLE_BLOCK = TitleBlock("Plan săpătură", "Proiect test", "S01", "1:100", "2026-11-24")


def _snapshot_drawing(groups_reversed: bool = False) -> Drawing:
    plan = DrawingGroup("plan", [
        Polyline([(0, 0), (1000.04, -0.04), (1000, 500)], closed=True),
        LinearDim((0, 0), (1000, 0), -300),
        ElevationMark((10, 10), -2400, "CF"),
    ], scale=100)
    table = DrawingGroup("a_tabel", [Table((0, 0), [["A", "1"]], [10, 20], 5)])
    groups = [table, plan] if groups_reversed else [plan, table]
    return Drawing(groups)


def _rectangle_group(name: str, width_mm: float, height_mm: float, scale: float) -> DrawingGroup:
    """grup dreptunghiular cu dimensiunile date în unități locale"""
    outline = Polyline([(0, 0), (width_mm, 0), (width_mm, height_mm), (0, height_mm)], closed=True)
    return DrawingGroup(name, [outline], scale=scale)


def _a1_content() -> list[DrawingGroup]:
    """1 plan 30 x 20 m la 1:100, 3 secțiuni 30 x 4 m la 1:100, tabel de volume și note"""
    plan = _rectangle_group("plan", 30000, 20000, 100)
    sections = [_rectangle_group(f"sectiune_{label}", 30000, 4000, 100) for label in ("1-1", "2-2", "3-3")]
    table = DrawingGroup("tabel_volume", [Table((0, 0), [["Element", "Volum [mc]"]] * 6, [60, 40], 8)])
    notes = build_notes_group(load_notes())
    return [plan, *sections, table, notes]


class TestTable(unittest.TestCase):

    def setUp(self):
        self.table = Table((100, 200), [["Nr.", "Element", "Volum"], ["1", "F1", ""]], [10, 50, 30], 8)

    def test_to_primitives_counts_lines_and_texts(self):
        primitives = self.table.to_primitives()
        lines = [item for item in primitives if isinstance(item, Line)]
        texts = [item for item in primitives if isinstance(item, Text)]
        self.assertEqual(len(lines), (2 + 1) + (3 + 1))   # orizontale + verticale
        self.assertEqual(len(texts), 5)                      # celula goală nu produce text

    def test_to_primitives_line_positions(self):
        lines = [item for item in self.table.to_primitives() if isinstance(item, Line)]
        self.assertEqual(lines[0], Line((100, 200), (190, 200), "tabel"))
        self.assertEqual(lines[2], Line((100, 184), (190, 184), "tabel"))
        self.assertEqual([line.start[0] for line in lines[3:]], [100, 110, 160, 190])
        self.assertEqual(lines[3].end, (100, 184))

    def test_to_primitives_text_positions(self):
        texts = [item for item in self.table.to_primitives() if isinstance(item, Text)]
        self.assertEqual(texts[0].text, "Nr.")
        self.assertAlmostEqual(texts[0].pos[0], 101.5)
        self.assertAlmostEqual(texts[0].pos[1], 192 + (8 - 2.5) / 2)
        self.assertEqual(texts[4].text, "F1")
        self.assertAlmostEqual(texts[4].pos[0], 111.5)
        self.assertAlmostEqual(texts[4].pos[1], 184 + (8 - 2.5) / 2)

    def test_table_too_many_cells_raises(self):
        with self.assertRaisesRegex(ValueError, "Rândul 1"):
            Table((0, 0), [["a", "b", "c"]], [10, 10], 5)

    def test_table_zero_width_raises(self):
        with self.assertRaises(ValueError):
            Table((0, 0), [["a"]], [0], 5)


class TestPrimitives(unittest.TestCase):

    def test_unknown_style_raises(self):
        with self.assertRaisesRegex(ValueError, "Stil necunoscut"):
            Line((0, 0), (1, 1), "rosu")

    def test_primitives_are_immutable(self):
        line = Line((0, 0), (1, 1))
        with self.assertRaises(Exception):
            line.style = "axa"

    def test_points_converted_to_tuples(self):
        polyline = Polyline([[0, 0], [1, 2]])
        self.assertEqual(polyline.points, ((0.0, 0.0), (1.0, 2.0)))

    def test_hatch_needs_three_points(self):
        with self.assertRaises(ValueError):
            Hatch([(0, 0), (1, 0)])

    def test_hatch_with_hole(self):
        hatch = Hatch([(0, 0), (10, 0), (10, 10)], [[(1, 1), (2, 1), (2, 2)]])
        self.assertEqual(len(hatch.holes), 1)

    def test_zero_length_dimension_raises(self):
        with self.assertRaises(ValueError):
            LinearDim((1, 1), (1, 1), 5)

    def test_dimension_text_in_cm_or_override(self):
        self.assertEqual(LinearDim((0, 0), (2350, 0)).display_text(), "235")
        self.assertEqual(LinearDim((0, 0), (2350, 0), text_override="var.").display_text(), "var.")

    def test_dimension_line_offset_perpendicular(self):
        start, end = LinearDim((0, 0), (1000, 0), 300).dim_line_points()
        self.assertEqual((start, end), ((0.0, 300.0), (1000.0, 300.0)))

    def test_elevation_text_format(self):
        self.assertEqual(format_elevation_m(0), "±0,00")
        self.assertEqual(format_elevation_m(150), "+0,15")
        self.assertEqual(ElevationMark((0, 0), -2400, "CF").display_text(), "CF -2,40")

    def test_invalid_text_align_raises(self):
        with self.assertRaises(ValueError):
            Text((0, 0), "x", 2.5, align="sus")

    def test_group_rejects_unknown_item(self):
        with self.assertRaises(ValueError):
            DrawingGroup("plan", ["nu e primitivă"])

    def test_group_bounds_divided_by_scale(self):
        group = _rectangle_group("plan", 30000, 20000, 100).moved_to((50, 60))
        self.assertEqual(group.sheet_bounds(), (50.0, 60.0, 350.0, 260.0))


class TestDrawingJson(unittest.TestCase):

    def test_to_json_matches_snapshot(self):
        self.assertEqual(_snapshot_drawing().to_json(), SNAPSHOT_JSON)

    def test_to_json_independent_of_group_order(self):
        self.assertEqual(_snapshot_drawing(groups_reversed=True).to_json(), SNAPSHOT_JSON)


class TestSheetLayout(unittest.TestCase):

    def test_a1_layout_without_overlaps(self):
        result = layout_sheet(_a1_content(), SheetSettings("A1"), TITLE_BLOCK)
        self.assertEqual(result.warnings, ())
        self.assertEqual(result.unplaced, ())
        content = [group for group in result.groups if group.name != "chenar"]
        self.assertEqual(len(content), 7)                 # 6 grupuri + cartuș
        for first, second in combinations(content, 2):
            self.assertFalse(_overlap(first.sheet_bounds(), second.sheet_bounds()),
                             f"{first.name} se suprapune cu {second.name}")
        frame = SheetSettings("A1").frame_bounds()
        for group in content:
            self.assertTrue(_inside(group.sheet_bounds(), frame), f"{group.name} iese din chenar")

    def test_a4_too_small_gives_warning(self):
        result = layout_sheet(_a1_content(), SheetSettings("A4"), TITLE_BLOCK)
        self.assertIn("plan", result.unplaced)
        self.assertTrue(any("nu încape" in warning for warning in result.warnings))

    def test_portrait_swaps_sheet_size(self):
        self.assertEqual(SheetSettings("A3", "vertical").sheet_size(), (297.0, 420.0))

    def test_unknown_format_raises(self):
        with self.assertRaises(ValueError):
            SheetSettings("B2")

    def test_title_block_in_bottom_right_corner(self):
        result = layout_sheet([], SheetSettings("A3"), TITLE_BLOCK)
        title = next(group for group in result.groups if group.name == "cartus")
        x_min, y_min, x_max, _ = title.sheet_bounds()
        frame = SheetSettings("A3").frame_bounds()
        self.assertAlmostEqual(x_max, frame[2])
        self.assertAlmostEqual(y_min, frame[1])


class TestNotes(unittest.TestCase):

    def test_default_notes_loaded(self):
        notes = load_notes(DEFAULT_NOTES_PATH)
        self.assertGreaterEqual(len(notes), 8)
        self.assertTrue(any("proces-verbal" in note for note in notes))
        self.assertFalse(any(note.startswith("#") for note in notes))

    def test_parse_notes_paragraphs_and_comments(self):
        self.assertEqual(parse_notes("# comentariu\nprima\nnotă\n\n\na doua\n"), ["prima notă", "a doua"])

    def test_missing_file_raises_clear_error(self):
        with self.assertRaisesRegex(FileNotFoundError, "nu există"):
            load_notes(os.path.join(tempfile.gettempdir(), "nu_exista_note_123.txt"))

    def test_too_large_file_raises(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "note.txt")
            with open(path, "w", encoding="utf-8") as notes_file:
                notes_file.write("a" * (MAX_NOTES_FILE_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "prea mare"):
                load_notes(path)

    def test_non_utf8_file_raises(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "note.txt")
            with open(path, "wb") as notes_file:
                notes_file.write(b"\xff\xfe\xfa nota")
            with self.assertRaisesRegex(ValueError, "UTF-8"):
                load_notes(path)

    def test_notes_group_numbered(self):
        group = build_notes_group(["prima", "a doua"])
        self.assertEqual([item.text for item in group.items], ["NOTE:", "1. prima", "2. a doua"])


def _overlap(first, second) -> bool:
    return first[0] < second[2] and second[0] < first[2] and first[1] < second[3] and second[1] < first[3]


def _inside(box, frame) -> bool:
    return box[0] >= frame[0] and box[1] >= frame[1] and box[2] <= frame[2] and box[3] <= frame[3]


if __name__ == "__main__":
    unittest.main()
