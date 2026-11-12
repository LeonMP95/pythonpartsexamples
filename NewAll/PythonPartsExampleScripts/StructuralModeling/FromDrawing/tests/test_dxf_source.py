"""Teste pentru DxfSource (citirea planșelor DXF). Fișierele DXF se generează cu ezdxf într-un director temporar."""

from __future__ import annotations

import importlib.util
import math
import os
import tempfile
import time
import unittest

from unittest import mock

from StructuralModeling.FromDrawing.DxfSource import DxfSourceError, read_dxf

HAS_EZDXF = importlib.util.find_spec("ezdxf") is not None
TOLERANCE = 1e-6

if HAS_EZDXF:
    import ezdxf


def _point_close(case: unittest.TestCase, actual, expected, places: int = 6) -> None:
    case.assertAlmostEqual(actual[0], expected[0], places = places)
    case.assertAlmostEqual(actual[1], expected[1], places = places)


@unittest.skipUnless(HAS_EZDXF, "ezdxf nu este instalat")
class DxfSourceTestBase(unittest.TestCase):
    """Director temporar și utilitar pentru salvarea documentelor"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def new_doc(self, insunits: int = 4):
        doc = ezdxf.new("R2010", units = insunits)
        doc.header["$INSUNITS"] = insunits
        return doc

    def save(self, doc, name: str = "plansa.dxf") -> str:
        path = os.path.join(self._tmp.name, name)
        doc.saveas(path)
        return path


class TestBasicEntities(DxfSourceTestBase):

    def test_line_and_closed_polyline_on_different_layers_are_read(self):
        doc = self.new_doc()
        msp = doc.modelspace()
        msp.add_line((0, 0, 5), (1000, 0, 7), dxfattribs = {"layer": "GRINZI"})
        msp.add_lwpolyline([(0, 0), (400, 0), (400, 600), (0, 600), (0, 0)], close = True,
                           dxfattribs = {"layer": "STALPI"})

        drawing = read_dxf(self.save(doc))

        self.assertEqual(len(drawing.segments), 1)
        self.assertEqual(drawing.segments[0].layer, "GRINZI")
        self.assertEqual(drawing.segments[0].start, (0.0, 0.0))
        self.assertEqual(drawing.segments[0].end, (1000.0, 0.0))
        self.assertEqual(len(drawing.polylines), 1)
        polyline = drawing.polylines[0]
        self.assertEqual(polyline.layer, "STALPI")
        self.assertTrue(polyline.closed)
        self.assertEqual(polyline.points, ((0.0, 0.0), (400.0, 0.0), (400.0, 600.0), (0.0, 600.0)))
        self.assertEqual(drawing.layers, {"GRINZI", "STALPI"})
        self.assertEqual(drawing.warnings, ())

    def test_consecutive_duplicate_points_are_removed(self):
        doc = self.new_doc()
        doc.modelspace().add_lwpolyline([(0, 0), (0, 0), (100, 0), (100, 0), (100, 50)])

        drawing = read_dxf(self.save(doc))

        self.assertEqual(drawing.polylines[0].points, ((0.0, 0.0), (100.0, 0.0), (100.0, 50.0)))
        self.assertFalse(drawing.polylines[0].closed)

    def test_open_polyline_with_coincident_ends_becomes_closed(self):
        doc = self.new_doc()
        msp = doc.modelspace()
        msp.add_lwpolyline([(0, 0), (400, 0), (400, 400), (0, 400), (0.005, 0)])
        msp.add_lwpolyline([(0, 0), (400, 0), (400, 400), (0, 400), (0, 1)])

        drawing = read_dxf(self.save(doc))

        closed, still_open = drawing.polylines
        self.assertTrue(closed.closed)
        self.assertEqual(closed.points, ((0.0, 0.0), (400.0, 0.0), (400.0, 400.0), (0.0, 400.0)))
        self.assertFalse(still_open.closed)
        self.assertEqual(len(still_open.points), 5)

    def test_insunits_cm_scales_by_ten(self):
        doc = self.new_doc(insunits = 5)
        doc.modelspace().add_line((1, 2), (30, 40))

        drawing = read_dxf(self.save(doc))

        self.assertEqual(drawing.segments[0].start, (10.0, 20.0))
        self.assertEqual(drawing.segments[0].end, (300.0, 400.0))
        self.assertEqual(drawing.warnings, ())

    def test_explicit_unit_factor_overrides_header(self):
        doc = self.new_doc(insunits = 5)
        doc.modelspace().add_line((0, 0), (2, 0))

        drawing = read_dxf(self.save(doc), unit_to_mm = 1000.0)

        self.assertEqual(drawing.segments[0].end, (2000.0, 0.0))

    def test_missing_units_assumes_mm_with_warning(self):
        doc = self.new_doc(insunits = 0)
        doc.modelspace().add_line((0, 0), (250, 0))

        drawing = read_dxf(self.save(doc))

        self.assertEqual(drawing.segments[0].end, (250.0, 0.0))
        self.assertEqual(len(drawing.warnings), 1)
        self.assertIn("$INSUNITS", drawing.warnings[0])

    def test_text_and_dimension_are_ignored_with_summary_warning(self):
        doc = self.new_doc()
        msp = doc.modelspace()
        msp.add_text("S1")
        msp.add_text("S2")
        msp.add_mtext("nota")
        msp.add_line((0, 0), (10, 0))

        drawing = read_dxf(self.save(doc))

        self.assertEqual(len(drawing.segments), 1)
        self.assertEqual(len(drawing.warnings), 1)
        self.assertIn("MTEXT: 1", drawing.warnings[0])
        self.assertIn("TEXT: 2", drawing.warnings[0])


class TestCurves(DxfSourceTestBase):

    def test_circle_becomes_closed_polyline_with_correct_radius(self):
        doc = self.new_doc()
        doc.modelspace().add_circle((1000, 2000), radius = 300, dxfattribs = {"layer": "STALPI"})

        drawing = read_dxf(self.save(doc), arc_segment_length_mm = 50.0)

        polyline = drawing.polylines[0]
        self.assertTrue(polyline.closed)
        self.assertEqual(polyline.layer, "STALPI")
        self.assertGreaterEqual(len(polyline.points), math.ceil(2 * math.pi * 300 / 50))
        self.assertNotEqual(polyline.points[0], polyline.points[-1])
        for x, y in polyline.points:
            self.assertAlmostEqual(math.hypot(x - 1000, y - 2000), 300.0, places = 6)

    def test_circle_with_negative_extrusion_is_mirrored_to_wcs(self):
        doc = self.new_doc()
        doc.modelspace().add_circle((1000, 0), radius = 100, dxfattribs = {"extrusion": (0, 0, -1)})

        drawing = read_dxf(self.save(doc))

        xs = [p[0] for p in drawing.polylines[0].points]
        self.assertAlmostEqual((max(xs) + min(xs)) / 2, -1000.0, places = 6)

    def test_arc_becomes_open_polyline_from_start_to_end(self):
        doc = self.new_doc()
        doc.modelspace().add_arc((0, 0), radius = 500, start_angle = 0, end_angle = 90)

        drawing = read_dxf(self.save(doc))

        polyline = drawing.polylines[0]
        self.assertFalse(polyline.closed)
        _point_close(self, polyline.points[0], (500.0, 0.0))
        _point_close(self, polyline.points[-1], (0.0, 500.0))

    def test_polyline_with_bulge_is_discretized_as_half_circle(self):
        doc = self.new_doc()
        # bulge = 1 -> semicerc în sens trigonometric între (0,0) și (1000,0): trece prin (500,-500)
        doc.modelspace().add_lwpolyline([(0, 0, 1.0), (1000, 0, 0.0)], format = "xyb")

        drawing = read_dxf(self.save(doc))

        points = drawing.polylines[0].points
        self.assertGreater(len(points), 3)
        _point_close(self, points[0], (0.0, 0.0))
        _point_close(self, points[-1], (1000.0, 0.0))
        for x, y in points:
            self.assertAlmostEqual(math.hypot(x - 500, y), 500.0, places = 6)
            self.assertLessEqual(y, TOLERANCE)
        self.assertAlmostEqual(min(y for _, y in points), -500.0, places = 6)

    def test_ellipse_and_spline_are_discretized(self):
        doc = self.new_doc()
        msp = doc.modelspace()
        msp.add_ellipse((0, 0), major_axis = (400, 0), ratio = 0.5)
        msp.add_spline([(0, 0), (100, 100), (200, 0), (300, 100)])

        drawing = read_dxf(self.save(doc))

        ellipse, spline = drawing.polylines
        self.assertTrue(ellipse.closed)
        for x, y in ellipse.points:
            self.assertAlmostEqual((x / 400) ** 2 + (y / 200) ** 2, 1.0, places = 6)
        self.assertFalse(spline.closed)
        _point_close(self, spline.points[0], (0.0, 0.0))
        _point_close(self, spline.points[-1], (300.0, 100.0))


class TestHatchesAndBlocks(DxfSourceTestBase):

    def test_hatch_with_hole_has_outer_and_hole(self):
        doc = self.new_doc()
        hatch = doc.modelspace().add_hatch(dxfattribs = {"layer": "PLACA"})
        hatch.paths.add_polyline_path([(0, 0), (1000, 0), (1000, 1000), (0, 1000)], flags = 1)
        hatch.paths.add_polyline_path([(400, 400), (600, 400), (600, 600), (400, 600)], flags = 16)

        drawing = read_dxf(self.save(doc))

        self.assertEqual(len(drawing.hatches), 1)
        result = drawing.hatches[0]
        self.assertEqual(result.layer, "PLACA")
        self.assertEqual(len(result.outer), 4)
        self.assertIn((1000.0, 1000.0), result.outer)
        self.assertEqual(len(result.holes), 1)
        self.assertIn((600.0, 600.0), result.holes[0])

    def test_hatch_without_external_flag_uses_largest_area_as_outer(self):
        doc = self.new_doc()
        hatch = doc.modelspace().add_hatch()
        hatch.paths.add_polyline_path([(400, 400), (600, 400), (600, 600), (400, 600)], flags = 0)
        hatch.paths.add_polyline_path([(0, 0), (1000, 0), (1000, 1000), (0, 1000)], flags = 0)

        drawing = read_dxf(self.save(doc))

        self.assertIn((1000.0, 1000.0), drawing.hatches[0].outer)
        self.assertIn((400.0, 400.0), drawing.hatches[0].holes[0])

    def test_hatch_with_three_disjoint_external_paths_gives_three_hatches(self):
        doc = self.new_doc()
        hatch = doc.modelspace().add_hatch(dxfattribs = {"layer": "STALPI"})
        for x in (0, 2000, 4000):
            hatch.paths.add_polyline_path([(x, 0), (x + 400, 0), (x + 400, 400), (x, 400)], flags = 1)

        drawing = read_dxf(self.save(doc))

        self.assertEqual(len(drawing.hatches), 3)
        self.assertEqual({h.layer for h in drawing.hatches}, {"STALPI"})
        self.assertTrue(all(h.holes == () for h in drawing.hatches))
        self.assertEqual(sorted(min(p[0] for p in h.outer) for h in drawing.hatches), [0.0, 2000.0, 4000.0])

    def test_hatch_without_flags_island_in_hole_becomes_new_hatch(self):
        doc = self.new_doc()
        hatch = doc.modelspace().add_hatch()
        hatch.paths.add_polyline_path([(400, 400), (500, 400), (500, 500), (400, 500)], flags = 0)
        hatch.paths.add_polyline_path([(0, 0), (1000, 0), (1000, 1000), (0, 1000)], flags = 0)
        hatch.paths.add_polyline_path([(200, 200), (800, 200), (800, 800), (200, 800)], flags = 0)

        drawing = read_dxf(self.save(doc))

        self.assertEqual(len(drawing.hatches), 2)
        big, island = sorted(drawing.hatches, key = lambda h: min(p[0] for p in h.outer))
        self.assertIn((1000.0, 1000.0), big.outer)
        self.assertEqual(len(big.holes), 1)
        self.assertIn((800.0, 800.0), big.holes[0])
        self.assertIn((500.0, 500.0), island.outer)
        self.assertEqual(island.holes, ())

    def test_hatch_holes_go_to_smallest_containing_external_path(self):
        doc = self.new_doc()
        hatch = doc.modelspace().add_hatch()
        hatch.paths.add_polyline_path([(0, 0), (400, 0), (400, 400), (0, 400)], flags = 1)
        hatch.paths.add_polyline_path([(2000, 0), (2400, 0), (2400, 400), (2000, 400)], flags = 1)
        hatch.paths.add_polyline_path([(2100, 100), (2200, 100), (2200, 200), (2100, 200)], flags = 0)

        drawing = read_dxf(self.save(doc))

        holes_by_x = {min(p[0] for p in h.outer): len(h.holes) for h in drawing.hatches}
        self.assertEqual(holes_by_x, {0.0: 0, 2000.0: 1})

    def test_hatch_edge_path_with_arc_is_read(self):
        doc = self.new_doc()
        hatch = doc.modelspace().add_hatch()
        edges = hatch.paths.add_edge_path(flags = 1)
        edges.add_line((0, 0), (1000, 0))
        edges.add_arc((500, 0), radius = 500, start_angle = 0, end_angle = 180, ccw = True)

        drawing = read_dxf(self.save(doc))

        outer = drawing.hatches[0].outer
        self.assertGreater(len(outer), 4)
        self.assertAlmostEqual(max(y for _, y in outer), 500.0, places = 6)
        self.assertNotEqual(outer[0], outer[-1])

    def test_block_inserted_twice_inherits_insert_layer_and_transform(self):
        doc = self.new_doc()
        block = doc.blocks.new("STALP")
        block.add_line((0, 0), (1000, 0), dxfattribs = {"layer": "0"})
        block.add_line((0, 0), (0, 200), dxfattribs = {"layer": "FIX"})
        msp = doc.modelspace()
        msp.add_blockref("STALP", (5000, 0), dxfattribs = {"layer": "STALPI", "rotation": 90})
        msp.add_blockref("STALP", (0, 3000), dxfattribs = {"layer": "GRINZI"})

        drawing = read_dxf(self.save(doc))

        by_layer = {}
        for segment in drawing.segments:
            by_layer.setdefault(segment.layer, []).append(segment)
        self.assertEqual(sorted(by_layer), ["FIX", "GRINZI", "STALPI"])
        self.assertEqual(len(by_layer["FIX"]), 2)
        rotated = by_layer["STALPI"][0]
        _point_close(self, rotated.start, (5000.0, 0.0))
        _point_close(self, rotated.end, (5000.0, 1000.0))
        translated = by_layer["GRINZI"][0]
        _point_close(self, translated.start, (0.0, 3000.0))
        _point_close(self, translated.end, (1000.0, 3000.0))

    def test_nested_block_on_layer_zero_inherits_outer_insert_layer(self):
        doc = self.new_doc()
        doc.blocks.new("INTERIOR").add_line((0, 0), (100, 0))
        doc.blocks.new("EXTERIOR").add_blockref("INTERIOR", (10, 0))
        doc.modelspace().add_blockref("EXTERIOR", (0, 0), dxfattribs = {"layer": "PERETI"})

        drawing = read_dxf(self.save(doc))

        self.assertEqual(drawing.segments[0].layer, "PERETI")
        _point_close(self, drawing.segments[0].start, (10.0, 0.0))


class TestInvalidInput(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def write(self, name: str, text: str) -> str:
        path = os.path.join(self._tmp.name, name)
        with open(path, "w", encoding = "utf-8") as file:
            file.write(text)
        return path

    def test_missing_file_raises(self):
        with self.assertRaisesRegex(DxfSourceError, "nu există"):
            read_dxf(os.path.join(self._tmp.name, "lipsa.dxf"))

    def test_wrong_extension_raises(self):
        with self.assertRaisesRegex(DxfSourceError, "extensia"):
            read_dxf(self.write("plansa.dwg", "0\nEOF\n"))

    def test_file_too_large_raises(self):
        with self.assertRaisesRegex(DxfSourceError, "prea mare"):
            read_dxf(self.write("plansa.dxf", "0\nEOF\n" * 100), max_file_size_mb = 1e-6)

    def test_invalid_parameters_raise(self):
        path = self.write("plansa.dxf", "0\nEOF\n")
        for kwargs in ({"unit_to_mm": 0.0}, {"arc_segment_length_mm": -1.0}, {"max_file_size_mb": 0.0},
                       {"max_entities": 0}, {"max_total_points": -5}):
            with self.subTest(kwargs = kwargs), self.assertRaises(DxfSourceError):
                read_dxf(path, **kwargs)

    def test_missing_ezdxf_raises_with_install_hint(self):
        path = self.write("plansa.dxf", "0\nEOF\n")
        with mock.patch.dict("sys.modules", {"ezdxf": None}):
            with self.assertRaisesRegex(DxfSourceError, "Install Python Package"):
                read_dxf(path)

    @unittest.skipUnless(HAS_EZDXF, "ezdxf nu este instalat")
    def test_corrupt_file_raises(self):
        path = self.write("plansa.dxf", "acesta nu este\nun fișier DXF\n\x00\x01")
        with self.assertRaisesRegex(DxfSourceError, "nu poate fi citit"):
            read_dxf(path)


if __name__ == "__main__":
    unittest.main()
