"""Teste de integrare: DXF (ezdxf) -> read_dxf -> recognize -> AllplanBuilder (module Allplan simulate)

Planșa de test este în cm ($INSUNITS = 5), cu layere în stil românesc; rezultatele se verifică în mm.
Testul de performanță are "SLOW" în nume (test_slow_...).
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import time
import unittest

from unittest import mock
from unittest.mock import MagicMock

try:
    import ezdxf
except ImportError:                                           # pragma: no cover
    ezdxf = None

# importul modulului existent instalează modulele NemAll_* simulate înainte de importul AllplanBuilder
from StructuralModeling.FromDrawing.tests import test_allplan_parts as tap     # noqa: E402

from StructuralModeling.FromDrawing import AllplanBuilder, DxfSource, Recognition, RecognitionRules  # noqa: E402
from StructuralModeling.FromDrawing.StructuralModel import Level                                    # noqa: E402

DEFAULT_RULES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "RulesDefault.json")

CM_UNITS = 5
LAYERS   = {"wall": "A-PERETI-BA", "column": "A-STALPI", "beam": "S-GRINZI", "slab": "S-PLACA"}
IGNORED  = ("A-MOBILIER", "A-COTE")
LEVEL    = Level("Etaj 1", 0.0, 3000.0)
BASEMENT = Level("Subsol", -3000.0, 0.0)


def build_floor_plan(path: str, layers: dict | None = None, door_block: bool = True) -> None:
    """Planșă de etaj 12 m x 8 m (cm)"""
    lay = layers or LAYERS
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = CM_UNITS

    for name in (*lay.values(), *IGNORED):
        doc.layers.add(name)

    msp  = doc.modelspace()
    wall = {"layer": lay["wall"]}

    # inel de pereți exteriori de 25 cm: două contururi închise
    msp.add_lwpolyline([(0, 0), (1200, 0), (1200, 800), (0, 800)], close = True, dxfattribs = wall)
    msp.add_lwpolyline([(25, 25), (1175, 25), (1175, 775), (25, 775)], close = True, dxfattribs = wall)

    # perete interior orizontal (y = 400) cu ușă de 90 cm între x = 200 și 290, plus ramura verticală (T)
    for y_face in (387.5, 412.5):
        msp.add_line((25, y_face), (200, y_face), dxfattribs = wall)
        msp.add_line((290, y_face), (1175, y_face), dxfattribs = wall)

    msp.add_line((200, 387.5), (200, 412.5), dxfattribs = wall)
    msp.add_line((290, 387.5), (290, 412.5), dxfattribs = wall)

    for x_face in (587.5, 612.5):
        msp.add_line((x_face, 25), (x_face, 387.5), dxfattribs = wall)

    if door_block:                                            # simbol de ușă (canat + arc) pe layerul pereților
        block = doc.blocks.new("USA90")
        block.add_line((0, 0), (90, 0))
        block.add_arc((0, 0), 90, 0, 90)
        msp.add_blockref("USA90", (200, 400), dxfattribs = wall)

    # stâlpi 40x40 în colțuri: o singură hașură cu 4 insule + stâlp circular Ø50
    hatch = msp.add_hatch(dxfattribs = {"layer": lay["column"]})

    for x_0, y_0 in ((0, 0), (1160, 0), (1160, 760), (0, 760)):
        hatch.paths.add_polyline_path([(x_0, y_0), (x_0 + 40, y_0), (x_0 + 40, y_0 + 40), (x_0, y_0 + 40)],
                                      is_closed = True)

    msp.add_circle((600, 600), 25, dxfattribs = {"layer": lay["column"]})

    # axe de grindă
    for y_axis in (200, 600):
        msp.add_line((20, y_axis), (1180, y_axis), dxfattribs = {"layer": lay["beam"]})

    # placă cu gol de scară
    msp.add_lwpolyline([(25, 25), (1175, 25), (1175, 775), (25, 775)], close = True, dxfattribs = {"layer": lay["slab"]})
    msp.add_lwpolyline([(800, 200), (1000, 200), (1000, 500), (800, 500)], close = True,
                       dxfattribs = {"layer": lay["slab"]})

    # layere de ignorat
    msp.add_text("Camera", dxfattribs = {"layer": "A-COTE", "insert": (100, 100), "height": 10})
    msp.add_linear_dim(base = (0, -50), p1 = (0, 0), p2 = (1200, 0), dxfattribs = {"layer": "A-COTE"}).render()
    msp.add_lwpolyline([(300, 100), (400, 100), (400, 150), (300, 150)], close = True,
                       dxfattribs = {"layer": "A-MOBILIER"})

    doc.saveas(path)


def recognize_file(path: str, rules_path: str = DEFAULT_RULES, level: Level = LEVEL):
    drawing = DxfSource.read_dxf(path)
    rules   = RecognitionRules.load_rules(rules_path)
    return drawing, Recognition.recognize(drawing, rules, level)


def size_of(outline):
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    return max(xs) - min(xs), max(ys) - min(ys)


@unittest.skipIf(ezdxf is None, "ezdxf nu este instalat")
class TestFloorPlan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = os.path.join(cls.tmp.name, "etaj.dxf")
        build_floor_plan(cls.path)
        cls.drawing, cls.model = recognize_file(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_units_converted_from_cm_to_mm(self):
        xs = [seg.start[0] for seg in self.drawing.segments] + [seg.end[0] for seg in self.drawing.segments]
        self.assertAlmostEqual(max(xs), 11800.0, delta = 1)

    def test_five_columns_with_expected_sizes(self):
        columns = self.model.columns
        self.assertEqual(len(columns), 5)

        square = [col for col in columns if len(col.outline) == 4]
        self.assertEqual(len(square), 4)

        for col in square:
            width, height = col.size
            self.assertAlmostEqual(width, 400.0, delta = 1)
            self.assertAlmostEqual(height, 400.0, delta = 1)

    def test_square_column_centroids_at_corners(self):
        centers = sorted((round(col.centroid[0]), round(col.centroid[1])) for col in self.model.columns
                         if len(col.outline) == 4)
        self.assertEqual(centers, [(200, 200), (200, 7800), (11800, 200), (11800, 7800)])

    def test_circular_column(self):
        circles = [col for col in self.model.columns if len(col.outline) > 4]
        self.assertEqual(len(circles), 1)

        width, height = circles[0].size
        self.assertAlmostEqual(width, 500.0, delta = 5)
        self.assertAlmostEqual(height, 500.0, delta = 5)
        self.assertAlmostEqual(circles[0].centroid[0], 6000.0, delta = 1)
        self.assertAlmostEqual(circles[0].centroid[1], 6000.0, delta = 1)

    def test_walls_thickness_and_count(self):
        walls = self.model.walls
        # 4 laturi exterioare + 2 segmente de perete interior (ușa întrerupe) + ramura verticală (T)
        self.assertEqual(len(walls), 7)

        for wall in walls:
            self.assertAlmostEqual(wall.thickness, 250.0, delta = 1)

    def test_exterior_ring_axes_closed_at_corners(self):
        walls   = self.model.walls
        corners = [(125, 125), (11875, 125), (11875, 7875), (125, 7875)]

        for corner in corners:
            ends = [pnt for wall in walls for pnt in (wall.start, wall.end)
                    if math.hypot(pnt[0] - corner[0], pnt[1] - corner[1]) <= 1.0]
            self.assertGreaterEqual(len(ends), 2, f"axele nu se închid în colțul {corner}")

    def test_door_is_a_break_in_interior_wall(self):
        interior = [wall for wall in self.model.walls
                    if abs(wall.start[1] - 4000) < 1 and abs(wall.end[1] - 4000) < 1]
        self.assertEqual(len(interior), 2)

        left, right = sorted(interior, key = lambda wall: min(wall.start[0], wall.end[0]))
        self.assertAlmostEqual(max(left.start[0], left.end[0]), 2000.0, delta = 1)
        self.assertAlmostEqual(min(right.start[0], right.end[0]), 2900.0, delta = 1)

    def test_t_branch_ends_on_interior_wall_axis(self):
        stem = [wall for wall in self.model.walls if abs(wall.start[0] - 6000) < 1 and abs(wall.end[0] - 6000) < 1]
        self.assertEqual(len(stem), 1)
        self.assertAlmostEqual(max(stem[0].start[1], stem[0].end[1]), 4000.0, delta = 1)
        self.assertAlmostEqual(min(stem[0].start[1], stem[0].end[1]), 125.0, delta = 1)

    def test_beams_from_rules(self):
        beams = self.model.beams
        self.assertEqual(len(beams), 2)

        for beam in beams:
            self.assertEqual(beam.width, 300.0)
            self.assertEqual(beam.depth, 500.0)

        self.assertEqual(sorted(round(beam.start[1]) for beam in beams), [2000, 6000])

    def test_slab_with_one_hole(self):
        self.assertEqual(len(self.model.slabs), 1)
        slab = self.model.slabs[0]

        self.assertEqual(len(slab.holes), 1)
        self.assertEqual(slab.thickness, 150.0)
        self.assertEqual(size_of(slab.outline), (11500.0, 7500.0))
        self.assertEqual(size_of(slab.holes[0]), (2000.0, 3000.0))

    def test_ids_unique_and_sequential(self):
        model = self.model
        self.assertEqual([col.id for col in model.columns], [f"S{n}" for n in range(1, 6)])
        self.assertEqual([wall.id for wall in model.walls], [f"P{n}" for n in range(1, 8)])
        self.assertEqual([beam.id for beam in model.beams], ["G1", "G2"])
        self.assertEqual([slab.id for slab in model.slabs], ["PL1"])

    def test_all_elements_have_level(self):
        for element in (*self.model.columns, *self.model.walls, *self.model.beams, *self.model.slabs):
            self.assertEqual(element.level, LEVEL)

    def test_furniture_and_dimensions_ignored(self):
        self.assertEqual(self.model.element_count, 5 + 7 + 2 + 1)
        self.assertEqual(self.drawing.layers & set(IGNORED), set(IGNORED) & self.drawing.layers)

        for col in self.model.columns:                      # mobilierul (300..400 x 100..150 cm) nu devine stâlp
            self.assertFalse(3000 <= col.centroid[0] <= 4000 and 1000 <= col.centroid[1] <= 1500)

    def test_unsupported_entities_reported_by_source_not_model(self):
        self.assertTrue(any("DIMENSION" in warn for warn in self.drawing.warnings))
        self.assertFalse(any("DIMENSION" in warn or "TEXT" in warn for warn in self.model.warnings))

    def test_no_false_warnings_with_door_block(self):
        self.assertEqual(self.model.warnings, [], "\n".join(self.model.warnings))


@unittest.skipIf(ezdxf is None, "ezdxf nu este instalat")
class TestRingTAndDoorWithoutBlock(unittest.TestCase):

    def test_no_warnings_for_ring_t_and_door_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fara_bloc.dxf")
            build_floor_plan(path, door_block = False)
            _, model = recognize_file(path)

        self.assertEqual(len(model.walls), 7)
        self.assertEqual(model.warnings, [], "\n".join(model.warnings))


@unittest.skipIf(ezdxf is None, "ezdxf nu este instalat")
class TestAllplanBuild(tap.AllplanFakesMixin):

    def model_for(self, level: Level):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "etaj.dxf")
            build_floor_plan(path)
            return recognize_file(path, level = level)[1]

    def check(self, level: Level):
        model  = self.model_for(level)
        result = AllplanBuilder.build_elements(model, "DOC", AllplanBuilder.BuildOptions(), "COMMON")

        self.assertEqual((len(result.columns), len(result.walls), len(result.beams), len(result.slabs)), (5, 7, 2, 1))
        self.assertEqual(result.warnings, [])

        for ele in result.columns:
            self.assertEqual((ele.props.PlaneReferences.bottom, ele.props.PlaneReferences.top),
                             (level.z_bottom, level.z_top))

        for ele in result.walls:
            tier = ele.props.GetWallTierProperties(1)
            self.assertEqual((tier.PlaneReferences.bottom, tier.PlaneReferences.top), (level.z_bottom, level.z_top))
            self.assertEqual(tier.Thickness, 250.0)

        for ele in result.beams:
            self.assertEqual((ele.props.PlaneReferences.bottom, ele.props.PlaneReferences.top),
                             (level.z_top - 500.0, level.z_top))

        slab, slab_ele = result.slabs[0]
        self.assertEqual((slab_ele.props.PlaneReferences.bottom, slab_ele.props.PlaneReferences.top),
                         (level.z_top - 150.0, level.z_top))
        self.assertEqual(len(slab.holes), 1)

        names = sorted(ele.props.Name for ele in result.elements)
        self.assertEqual(names, sorted(["S1", "S2", "S3", "S4", "S5", *[f"P{n}" for n in range(1, 8)],
                                        "G1", "G2", "PL1"]))

    def test_basement_levels(self):
        self.check(BASEMENT)

    def test_ground_floor_levels(self):
        self.check(LEVEL)

    def test_create_in_document_counts(self):
        model  = self.model_for(LEVEL)
        slab_a = MagicMock()
        slab_a.__eq__ = lambda self_, other: True
        slab_a.GetModelElementUUID.return_value = "UUID"

        def create(_doc, _matrix, elements, *_args):
            return [slab_a] if elements and isinstance(elements[0], tap.SlabElement) else []

        with mock.patch.object(tap.AllplanBaseEle, "CreateElements", MagicMock(side_effect = create)):
            report = AllplanBuilder.create_in_document(model, "DOC", AllplanBuilder.BuildOptions())

        self.assertEqual(report.counts, {"stâlpi": 5, "pereți": 7, "grinzi": 2, "plăci": 1, "goluri": 1})
        self.assertEqual(report.warnings, [])


@unittest.skipIf(ezdxf is None, "ezdxf nu este instalat")
class TestRobustness(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def path(self, name: str) -> str:
        return os.path.join(self.tmp.name, name)

    def test_empty_drawing(self):
        path = self.path("gol.dxf")
        doc  = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = CM_UNITS
        doc.saveas(path)

        _, model = recognize_file(path)

        self.assertEqual(model.element_count, 0)
        self.assertEqual(len(model.warnings), 1)
        self.assertIn("planșă goală", model.warnings[0])

    def test_unknown_layers_only(self):
        path = self.path("necunoscut.dxf")
        doc  = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = CM_UNITS
        doc.layers.add("XYZ")
        doc.modelspace().add_line((0, 0), (500, 0), dxfattribs = {"layer": "XYZ"})
        doc.saveas(path)

        _, model = recognize_file(path)

        self.assertEqual(model.element_count, 0)
        self.assertEqual(len(model.warnings), 1)
        self.assertIn("'XYZ'", model.warnings[0])

    def test_custom_rules_file_with_renamed_layers(self):
        layers = {"wall": "MUR_BA", "column": "COL", "beam": "BM", "slab": "FLOOR"}
        rules  = {"layers": [{"pattern": "MUR_BA", "element": "wall"}, {"pattern": "COL", "element": "column"},
                             {"pattern": "BM", "element": "beam"}, {"pattern": "FLOOR", "element": "slab"}],
                  "beam_width": 250, "beam_depth": 600, "slab_thickness": 200}
        path       = self.path("custom.dxf")
        rules_path = self.path("reguli.json")
        build_floor_plan(path, layers)

        with open(rules_path, "w", encoding = "utf-8") as file:
            json.dump(rules, file)

        _, model = recognize_file(path, rules_path)

        self.assertEqual((len(model.columns), len(model.walls), len(model.beams), len(model.slabs)), (5, 7, 2, 1))
        self.assertEqual({(beam.width, beam.depth) for beam in model.beams}, {(250.0, 600.0)})
        self.assertEqual(model.slabs[0].thickness, 200.0)

    def test_default_rules_do_not_match_renamed_layers(self):
        path = self.path("custom.dxf")
        build_floor_plan(path, {"wall": "MUR_BA", "column": "COL", "beam": "BM", "slab": "FLOOR"})

        _, model = recognize_file(path)

        self.assertEqual(model.element_count, 0)
        self.assertEqual(len(model.warnings), 1)

    def test_invalid_rules_file(self):
        rules_path = self.path("rau.json")

        with open(rules_path, "w", encoding = "utf-8") as file:
            file.write("{nu este json")

        with self.assertRaises(RecognitionRules.RulesError):
            RecognitionRules.load_rules(rules_path)

    def test_missing_dxf_and_garbage_dxf(self):
        with self.assertRaises(DxfSource.DxfSourceError):
            DxfSource.read_dxf(self.path("lipsa.dxf"))

        garbage = self.path("garbage.dxf")

        with open(garbage, "w", encoding = "utf-8") as file:
            file.write("acesta nu este un DXF")

        with self.assertRaises(DxfSource.DxfSourceError):
            DxfSource.read_dxf(garbage)


def build_wall_grid(path: str, nodes: int = 16, pitch_cm: float = 400.0, thickness_cm: float = 25.0) -> None:
    """Grilă de pereți: nodes x nodes noduri, 2 * nodes * (nodes - 1) pereți (fețe LINE între noduri)"""
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = CM_UNITS
    doc.layers.add("A-PERETI-BA")
    msp  = doc.modelspace()
    attr = {"layer": "A-PERETI-BA"}
    half = thickness_cm / 2

    for i in range(nodes):
        for j in range(nodes - 1):
            lo, hi = j * pitch_cm + half, (j + 1) * pitch_cm - half
            fixed  = i * pitch_cm

            for off in (-half, half):
                msp.add_line((lo, fixed + off), (hi, fixed + off), dxfattribs = attr)      # perete orizontal
                msp.add_line((fixed + off, lo), (fixed + off, hi), dxfattribs = attr)      # perete vertical

    doc.saveas(path)


@unittest.skipIf(ezdxf is None, "ezdxf nu este instalat")
class TestSlowPerformance(unittest.TestCase):

    MAX_SECONDS = 10.0

    def test_slow_wall_grid_15x15_under_10_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "grila.dxf")
            build_wall_grid(path)

            start    = time.perf_counter()
            _, model = recognize_file(path)
            elapsed  = time.perf_counter() - start

        print(f"\n[PERF] grila 15x15: {len(model.walls)} pereti, read_dxf + recognize = {elapsed:.2f} s")

        # axele coliniare se pot uni prin noduri: numărul exact depinde de recunoaștere, lungimea totală nu
        total = sum(math.hypot(wall.end[0] - wall.start[0], wall.end[1] - wall.start[1]) for wall in model.walls)
        self.assertAlmostEqual(total, 2 * 16 * 15 * 4000.0, delta = 1.0)
        self.assertGreaterEqual(len(model.walls), 32)
        self.assertEqual(model.warnings, [])
        self.assertLess(elapsed, self.MAX_SECONDS)


if __name__ == "__main__":
    unittest.main()
