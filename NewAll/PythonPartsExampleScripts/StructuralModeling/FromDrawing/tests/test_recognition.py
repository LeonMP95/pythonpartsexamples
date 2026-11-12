"""Teste pentru Recognition.recognize, pe planșe sintetice construite în cod (coordonate în mm)

Toleranța de comparare a coordonatelor și dimensiunilor: TOL_MM (rezultate geometrice exacte,
diferențe doar din rotunjiri numerice), cu excepția cazurilor cu fețe neparalele, unde toleranța
este dată explicit în test.
"""

from __future__ import annotations

import math
import time
import unittest

from StructuralModeling.FromDrawing.Model2D import Drawing2D, Hatch2D, Polyline2D, Segment2D
from StructuralModeling.FromDrawing.Recognition import recognize
from StructuralModeling.FromDrawing.RecognitionRules import LayerRule, RecognitionRules
from StructuralModeling.FromDrawing.StructuralModel import Level

TOL_MM = 1e-6

RULES = RecognitionRules(layers = (LayerRule("*STALP*", "column"), LayerRule("*PERE*", "wall"),
                                   LayerRule("*GRIND*", "beam"), LayerRule("*PLAC*", "slab")))
LEVEL = Level("Parter", 0.0, 3000.0)

COL, WALL, BEAM, SLAB = "S_STALPI", "S_PERETI", "S_GRINDA", "S_PLACI"


def rect(x_0: float, y_0: float, x_1: float, y_1: float) -> tuple:
    """dreptunghi în sens trigonometric"""
    return ((x_0, y_0), (x_1, y_0), (x_1, y_1), (x_0, y_1))


def seg(p_1, p_2, layer = WALL) -> Segment2D:
    return Segment2D(p_1, p_2, layer)


def run(segments = (), polylines = (), hatches = (), rules = RULES):
    return recognize(Drawing2D(tuple(segments), tuple(polylines), tuple(hatches)), rules, LEVEL)


class AssertMixin:
    def assertPoint(self, actual, expected, delta = TOL_MM):
        self.assertAlmostEqual(actual[0], expected[0], delta = delta)
        self.assertAlmostEqual(actual[1], expected[1], delta = delta)

    def assertWall(self, wall, start, end, thickness, delta = TOL_MM):
        self.assertPoint(wall.start, start, delta)
        self.assertPoint(wall.end, end, delta)
        self.assertAlmostEqual(wall.thickness, thickness, delta = delta)


class TestColumns(unittest.TestCase, AssertMixin):

    def test_rectangle_polyline_creates_column(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 400, 600), True, COL)])

        self.assertEqual(len(model.columns), 1)
        self.assertEqual(model.columns[0].id, "S1")
        self.assertEqual(model.columns[0].size, (400.0, 600.0))
        self.assertEqual(model.columns[0].level, LEVEL)
        self.assertEqual(model.warnings, [])

    def test_l_shaped_polyline_keeps_six_vertices(self):
        l_shape = ((0, 0), (600, 0), (600, 250), (250, 250), (250, 600), (0, 600))
        model   = run(polylines = [Polyline2D(l_shape, True, COL)])

        self.assertEqual(len(model.columns), 1)
        self.assertEqual(len(model.columns[0].outline), 6)
        self.assertEqual(model.columns[0].size, (600.0, 600.0))

    def test_duplicate_and_collinear_points_are_removed(self):
        pts   = ((0, 0), (200, 0), (400, 0), (400, 0.5), (400, 400), (0, 400), (0, 0))
        model = run(polylines = [Polyline2D(pts, True, COL)])

        self.assertEqual(len(model.columns[0].outline), 4)

    def test_four_free_segments_chain_into_column(self):
        pts   = rect(1000, 1000, 1300, 1500)
        sides = [seg(pts[i], pts[(i + 1) % 4], COL) for i in (2, 0, 3, 1)]
        sides[1] = seg(sides[1].end, (sides[1].start[0] + 3, sides[1].start[1]), COL)   # capăt la 3 mm
        model = run(segments = sides)

        self.assertEqual(len(model.columns), 1)
        self.assertAlmostEqual(model.columns[0].size[0], 300.0, delta = 3.0)
        self.assertAlmostEqual(model.columns[0].size[1], 500.0, delta = 3.0)
        self.assertEqual(model.warnings, [])

    def test_open_chain_leaves_warning(self):
        model = run(segments = [seg((0, 0), (400, 0), COL), seg((400, 0), (400, 400), COL)])

        self.assertEqual(model.columns, [])
        self.assertEqual(len(model.warnings), 2)
        self.assertIn("Stâlp", model.warnings[0])
        self.assertIn("S_STALPI", model.warnings[0])

    def test_hatch_and_polyline_on_same_place_give_one_column(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 400, 400), True, COL)],
                    hatches   = [Hatch2D(rect(400, 2, 0, 402)[::-1], (), COL)])

        self.assertEqual(len(model.columns), 1)
        self.assertEqual(model.warnings, [])

    def test_hatch_alone_creates_column(self):
        model = run(hatches = [Hatch2D(rect(0, 0, 300, 300), (), COL)])

        self.assertEqual(len(model.columns), 1)

    def test_too_large_contour_gives_warning(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 2500, 400), True, COL)])

        self.assertEqual(model.columns, [])
        self.assertEqual(len(model.warnings), 1)
        self.assertIn("2500 x 400", model.warnings[0])
        self.assertIn("(1250, 200)", model.warnings[0])

    def test_too_small_contour_gives_warning(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 100, 400), True, COL)])

        self.assertEqual(model.columns, [])
        self.assertEqual(len(model.warnings), 1)


class TestWalls(unittest.TestCase, AssertMixin):

    def test_two_parallel_lines_create_wall(self):
        model = run(segments = [seg((0, 0), (5000, 0)), seg((5000, 250), (0, 250))])

        self.assertEqual(len(model.walls), 1)
        self.assertWall(model.walls[0], (0, 125), (5000, 125), 250)
        self.assertEqual(model.walls[0].id, "P1")
        self.assertEqual(model.warnings, [])

    def test_axis_only_on_overlap(self):
        model = run(segments = [seg((0, 0), (5000, 0)), seg((1000, 300), (4000, 300))])

        self.assertWall(model.walls[0], (1000, 150), (4000, 150), 300)
        self.assertEqual(model.warnings, [])

    def test_rectangle_polyline_creates_wall_on_long_axis(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 200, 4000), True, WALL)])

        self.assertEqual(len(model.walls), 1)
        self.assertWall(model.walls[0], (100, 0), (100, 4000), 200)
        self.assertEqual(model.warnings, [])

    def test_rectangle_with_thickness_out_of_range_gives_warnings(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 1000, 4000), True, WALL)])

        self.assertEqual(model.walls, [])
        self.assertEqual(len(model.warnings), 4)          # cele 4 laturi rămân fără față opusă

    def test_square_wall_contour_gives_warning(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 300, 300), True, WALL)])

        self.assertEqual(model.walls, [])
        self.assertEqual(len(model.warnings), 1)
        self.assertIn("ambiguă", model.warnings[0])

    def test_third_line_too_far_stays_unpaired(self):
        model = run(segments = [seg((0, 0), (5000, 0)), seg((0, 250), (5000, 250)),
                                seg((0, 1500), (5000, 1500))])

        self.assertEqual(len(model.walls), 1)
        self.assertWall(model.walls[0], (0, 125), (5000, 125), 250)
        self.assertEqual(len(model.warnings), 1)
        self.assertIn("(0, 1500)", model.warnings[0])

    def test_closest_opposite_face_wins(self):
        model = run(segments = [seg((0, 0), (5000, 0)), seg((0, 250), (5000, 250)),
                                seg((0, 550), (5000, 550)), seg((0, 800), (5000, 800))])

        self.assertEqual(len(model.walls), 2)
        self.assertEqual([round(w.thickness) for w in model.walls], [250, 250])
        self.assertWall(model.walls[0], (0, 675), (5000, 675), 250)
        self.assertWall(model.walls[1], (0, 125), (5000, 125), 250)

    def test_door_opening_gives_two_separate_walls(self):
        model = run(segments = [seg((0, 0), (2000, 0)), seg((2900, 0), (5000, 0)),
                                seg((0, 250), (2000, 250)), seg((2900, 250), (5000, 250))])

        self.assertEqual(len(model.walls), 2)
        self.assertWall(model.walls[0], (0, 125), (2000, 125), 250)
        self.assertWall(model.walls[1], (2900, 125), (5000, 125), 250)
        self.assertEqual(model.warnings, [])

    def test_collinear_consecutive_walls_are_merged(self):
        model = run(segments = [seg((0, 0), (2000, 0)), seg((2000, 0), (5000, 0)),
                                seg((0, 250), (2000, 250)), seg((2002, 250), (5000, 250))],
                    polylines = [Polyline2D(rect(5000, 0, 7000, 250), True, WALL)])

        self.assertEqual(len(model.walls), 1)
        self.assertWall(model.walls[0], (0, 125), (7000, 125), 250, delta = 2.0)

    def test_different_thickness_not_merged(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 2000, 250), True, WALL),
                                 Polyline2D(rect(2000, -25, 4000, 275), True, WALL)])

        self.assertEqual(len(model.walls), 2)

    def test_unpaired_segment_gives_warning_with_coordinates(self):
        model = run(segments = [seg((0, 0), (3000, 0))])

        self.assertEqual(model.walls, [])
        self.assertEqual(len(model.warnings), 1)
        self.assertIn("Perete", model.warnings[0])
        self.assertIn("S_PERETI", model.warnings[0])
        self.assertIn("(0, 0)", model.warnings[0])
        self.assertIn("(3000, 0)", model.warnings[0])

    def test_lines_at_half_degree_are_accepted(self):
        angle = math.radians(0.5)
        far   = (3000 * math.cos(angle), 250 + 3000 * math.sin(angle))
        model = run(segments = [seg((0, 0), (3000, 0)), seg((0, 250), far)])

        self.assertEqual(len(model.walls), 1)
        expected_thickness = (250 + far[1]) / 2          # media distanțelor la capetele suprapunerii
        self.assertAlmostEqual(model.walls[0].thickness, expected_thickness, delta = 1.0)

    def test_lines_at_five_degrees_are_rejected(self):
        angle = math.radians(5.0)
        model = run(segments = [seg((0, 0), (3000, 0)),
                                seg((0, 250), (3000 * math.cos(angle), 250 + 3000 * math.sin(angle)))])

        self.assertEqual(model.walls, [])
        self.assertEqual(len(model.warnings), 2)

    def test_short_overlap_is_rejected(self):
        model = run(segments = [seg((0, 0), (1000, 0)), seg((800, 250), (2000, 250))])

        self.assertEqual(model.walls, [])
        self.assertEqual(len(model.warnings), 2)

    def test_ring_of_walls_from_two_closed_polylines(self):
        outer = rect(0, 0, 6000, 4000)
        inner = rect(250, 250, 5750, 3750)
        model = run(polylines = [Polyline2D(outer, True, WALL), Polyline2D(inner, True, WALL)])

        self.assertEqual(len(model.walls), 4)
        self.assertEqual(model.warnings, [])
        self.assertTrue(all(abs(w.thickness - 250) < TOL_MM for w in model.walls))


class TestWallJunctions(unittest.TestCase, AssertMixin):

    def test_ring_of_walls_axes_close_at_corners(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 6000, 4000), True, WALL),
                                 Polyline2D(rect(250, 250, 5750, 3750), True, WALL)])

        self.assertEqual(len(model.walls), 4)
        self.assertEqual(model.warnings, [])
        self.assertWall(model.walls[0], (125, 3875), (5875, 3875), 250)
        self.assertWall(model.walls[1], (125, 125), (125, 3875), 250)
        self.assertWall(model.walls[2], (5875, 125), (5875, 3875), 250)
        self.assertWall(model.walls[3], (125, 125), (5875, 125), 250)

    def test_four_overlapping_rectangles_close_at_corners(self):
        polys = [Polyline2D(r, True, WALL) for r in (rect(0, 3750, 6000, 4000), rect(0, 0, 6000, 250),
                                                     rect(0, 0, 250, 4000), rect(5750, 0, 6000, 4000))]
        model = run(polylines = polys)

        self.assertEqual(len(model.walls), 4)
        self.assertEqual(model.warnings, [])
        self.assertWall(model.walls[0], (125, 3875), (5875, 3875), 250)
        self.assertWall(model.walls[3], (125, 125), (5875, 125), 250)

    def test_l_shaped_closed_polyline_gives_l_without_warnings(self):
        l_shape = ((0, 0), (4000, 0), (4000, 250), (250, 250), (250, 3000), (0, 3000))
        model   = run(polylines = [Polyline2D(l_shape, True, WALL)])

        self.assertEqual(model.warnings, [])
        self.assertWall(model.walls[0], (125, 125), (125, 3000), 250)
        self.assertWall(model.walls[1], (125, 125), (4000, 125), 250)

    def test_t_junction_stem_reaches_through_wall_axis(self):
        model = run(segments = [seg((0, 250), (6000, 250)),                       # fața continuă
                                seg((0, 0), (2875, 0)), seg((3125, 0), (6000, 0)), # fața ruptă de nod
                                seg((2875, 0), (2875, -3000)), seg((3125, 0), (3125, -3000)),
                                seg((2875, -3000), (3125, -3000)),                 # capete închise
                                seg((0, 0), (0, 250)), seg((6000, 0), (6000, 250))])

        self.assertEqual(model.warnings, [])
        self.assertEqual(len(model.walls), 2)
        self.assertWall(model.walls[0], (0, 125), (6000, 125), 250)
        self.assertWall(model.walls[1], (3000, -3000), (3000, 125), 250)

    def test_wall_with_closed_ends_has_no_warnings(self):
        model = run(segments = [seg((0, 0), (5000, 0)), seg((0, 250), (5000, 250)),
                                seg((0, 0), (0, 250)), seg((5000, 252), (5000, -1))])

        self.assertEqual(len(model.walls), 1)
        self.assertEqual(model.warnings, [])

    def test_end_line_of_wrong_length_still_warns(self):
        model = run(segments = [seg((0, 0), (5000, 0)), seg((0, 250), (5000, 250)),
                                seg((-200, -300), (-200, 300))])

        self.assertEqual(len(model.walls), 1)
        self.assertEqual(len(model.warnings), 1)
        self.assertIn("(-200, -300)", model.warnings[0])

    def test_continuous_face_with_door_in_opposite_face_gives_two_walls(self):
        model = run(segments = [seg((0, 250), (5000, 250)),
                                seg((0, 0), (2000, 0)), seg((2900, 0), (5000, 0))])

        self.assertEqual(model.warnings, [])
        self.assertEqual(len(model.walls), 2)
        self.assertWall(model.walls[0], (0, 125), (2000, 125), 250)
        self.assertWall(model.walls[1], (2900, 125), (5000, 125), 250)

    def test_continuous_face_with_touching_opposite_pieces_gives_one_wall(self):
        model = run(segments = [seg((0, 250), (5000, 250)),
                                seg((0, 0), (2000, 0)), seg((2000, 0), (5000, 0))])

        self.assertEqual(model.warnings, [])
        self.assertEqual(len(model.walls), 1)
        self.assertWall(model.walls[0], (0, 125), (5000, 125), 250)

    def test_crossing_walls_are_not_modified(self):
        model = run(polylines = [Polyline2D(rect(0, 1000, 4000, 1250), True, WALL),
                                 Polyline2D(rect(1500, 0, 1750, 3000), True, WALL)])

        self.assertWall(model.walls[0], (1625, 0), (1625, 3000), 250)    # mijloc la y = 1500
        self.assertWall(model.walls[1], (0, 1125), (4000, 1125), 250)


class TestBeams(unittest.TestCase, AssertMixin):

    def test_axis_segment_creates_beam_with_default_section(self):
        model = run(segments = [seg((6000, 0), (0, 0), BEAM)])

        self.assertEqual(len(model.beams), 1)
        beam = model.beams[0]
        self.assertEqual(beam.id, "G1")
        self.assertPoint(beam.start, (0, 0))
        self.assertPoint(beam.end, (6000, 0))
        self.assertEqual((beam.width, beam.depth), (RULES.beam_width, RULES.beam_depth))

    def test_open_polyline_gives_one_beam_per_segment(self):
        model = run(polylines = [Polyline2D(((0, 0), (5000, 0), (5000, 4000)), False, BEAM)])

        self.assertEqual(len(model.beams), 2)

    def test_rectangle_creates_beam_on_long_axis(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 6000, 350), True, BEAM)])

        self.assertEqual(len(model.beams), 1)
        beam = model.beams[0]
        self.assertPoint(beam.start, (0, 175))
        self.assertPoint(beam.end, (6000, 175))
        self.assertAlmostEqual(beam.width, 350, delta = TOL_MM)
        self.assertEqual(beam.depth, RULES.beam_depth)

    def test_non_rectangular_contour_gives_warning(self):
        model = run(polylines = [Polyline2D(((0, 0), (600, 0), (600, 300), (300, 600), (0, 600)), True, BEAM)])

        self.assertEqual(model.beams, [])
        self.assertEqual(len(model.warnings), 1)


class TestSlabs(unittest.TestCase, AssertMixin):

    def test_polyline_with_inner_contour_creates_slab_with_hole(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 8000, 6000), True, SLAB),
                                 Polyline2D(rect(1000, 1000, 2000, 2500), True, SLAB)])

        self.assertEqual(len(model.slabs), 1)
        slab = model.slabs[0]
        self.assertEqual(slab.id, "PL1")
        self.assertEqual(slab.thickness, RULES.slab_thickness)
        self.assertEqual(len(slab.holes), 1)
        self.assertEqual(slab.holes[0], rect(1000, 1000, 2000, 2500))
        self.assertEqual(model.warnings, [])

    def test_hatch_brings_its_holes(self):
        model = run(hatches = [Hatch2D(rect(0, 0, 8000, 6000), (rect(1000, 1000, 2000, 2500),), SLAB)])

        self.assertEqual(len(model.slabs), 1)
        self.assertEqual(len(model.slabs[0].holes), 1)

    def test_hatch_and_polyline_same_outline_one_slab(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 8000, 6000), True, SLAB)],
                    hatches   = [Hatch2D(rect(0, 0, 8000, 6000), (rect(1000, 1000, 2000, 2500),), SLAB)])

        self.assertEqual(len(model.slabs), 1)
        self.assertEqual(len(model.slabs[0].holes), 1)

    def test_adjacent_slabs_are_separate_without_warning(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 4000, 6000), True, SLAB),
                                 Polyline2D(rect(4000, 0, 8000, 6000), True, SLAB)])

        self.assertEqual(len(model.slabs), 2)
        self.assertEqual(model.warnings, [])

    def test_open_polyline_on_slab_layer_gives_warning(self):
        model = run(polylines = [Polyline2D(((0, 0), (4000, 0), (4000, 3000)), False, SLAB)])

        self.assertEqual(model.slabs, [])
        self.assertEqual(len(model.warnings), 1)


class TestLayersAndOrdering(unittest.TestCase, AssertMixin):

    def test_unknown_layer_is_ignored(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 400, 400), True, COL),
                                 Polyline2D(rect(0, 0, 400, 400), True, "MOBILIER")],
                    segments  = [seg((0, 0), (3000, 0), "COTE")])

        self.assertEqual(model.element_count, 1)
        self.assertEqual(model.warnings, [])

    def test_drawing_without_matching_layers_gives_warning(self):
        model = run(segments = [seg((0, 0), (3000, 0), "COTE"), seg((0, 0), (0, 3000), "AXE")])

        self.assertEqual(model.element_count, 0)
        self.assertEqual(len(model.warnings), 1)
        self.assertIn("'AXE', 'COTE'", model.warnings[0])

    def test_empty_drawing_gives_warning(self):
        model = run()

        self.assertEqual(model.element_count, 0)
        self.assertEqual(len(model.warnings), 1)

    def test_layer_matching_is_case_insensitive(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 400, 400), True, "s_stalpi_ba")])

        self.assertEqual(len(model.columns), 1)

    def test_ids_follow_y_descending_then_x_ascending(self):
        polys = [Polyline2D(rect(x, y, x + 400, y + 400), True, COL)
                 for x, y in ((5000, 0), (0, 0), (5000, 6000), (0, 6000))]
        model = run(polylines = polys)

        self.assertEqual([c.id for c in model.columns], ["S1", "S2", "S3", "S4"])
        centers = [c.centroid for c in model.columns]
        expected = [(200, 6200), (5200, 6200), (200, 200), (5200, 200)]
        for actual, exp in zip(centers, expected):
            self.assertPoint(actual, exp)

    def test_order_is_independent_of_input_order(self):
        segs = [seg((0, 0), (5000, 0)), seg((0, 250), (5000, 250)),
                seg((0, 3000), (5000, 3000)), seg((0, 3300), (5000, 3300)),
                seg((0, 6000), (0, 9000), BEAM), seg((0, 6000), (4000, 6000), BEAM)]
        model_a = run(segments = segs)
        model_b = run(segments = segs[::-1])

        self.assertEqual(model_a, model_b)
        self.assertEqual([w.id for w in model_a.walls], ["P1", "P2"])
        self.assertAlmostEqual(model_a.walls[0].thickness, 300, delta = TOL_MM)
        self.assertPoint(model_a.beams[0].start, (0, 6000))
        self.assertPoint(model_a.beams[0].end, (0, 9000))

    def test_all_types_in_one_drawing(self):
        model = run(polylines = [Polyline2D(rect(0, 0, 400, 400), True, COL),
                                 Polyline2D(rect(400, 0, 5000, 250), True, WALL),
                                 Polyline2D(rect(0, 0, 5000, 5000), True, SLAB)],
                    segments  = [seg((200, 200), (200, 5000), BEAM)])

        self.assertEqual(model.summary(), "1 stâlpi, 1 pereți, 1 grinzi, 1 plăci, 0 avertismente")


def wall_grid_segments(nodes: int, pitch: float = 4000.0, half: float = 125.0) -> list[Segment2D]:
    """grilă de pereți desenați prin fețe întrerupte la fiecare nod: 4 * nodes * (nodes - 1) segmente"""
    segments = []

    for i in range(nodes):
        for j in range(nodes - 1):
            low, high, fixed = j * pitch + half, (j + 1) * pitch - half, i * pitch

            for off in (-half, half):
                segments.append(seg((low, fixed + off), (high, fixed + off)))
                segments.append(seg((fixed + off, low), (fixed + off, high)))

    return segments


def rotated_rect(center_start, length, width, angle_deg) -> tuple:
    """dreptunghi cu axa de la center_start, de lungime length, rotit cu angle_deg"""
    ang = math.radians(angle_deg)
    u_x, u_y = math.cos(ang), math.sin(ang)
    n_x, n_y = -u_y * width / 2, u_x * width / 2
    x_0, y_0 = center_start
    x_1, y_1 = x_0 + u_x * length, y_0 + u_y * length
    return ((x_0 - n_x, y_0 - n_y), (x_1 - n_x, y_1 - n_y), (x_1 + n_x, y_1 + n_y), (x_0 + n_x, y_0 + n_y))


class TestWallJunctionsExtra(unittest.TestCase, AssertMixin):

    def test_cross_junctions_unify_axes_in_both_directions(self):
        model = run(segments = wall_grid_segments(3))

        self.assertEqual(model.warnings, [])
        self.assertEqual(len(model.walls), 6)                 # 3 axe orizontale + 3 verticale, întregi

        for wall in model.walls:
            self.assertAlmostEqual(math.dist(wall.start, wall.end), 8000.0, delta = TOL_MM)

    def test_near_parallel_wall_at_3_degrees_is_not_extended(self):
        slanted = rotated_rect((1000, 100), 3000, 250, 3.0)
        model   = run(polylines = [Polyline2D(rect(0, -125, 5000, 125), True, WALL),
                                   Polyline2D(slanted, True, WALL)])

        self.assertEqual(len(model.walls), 2)
        host  = [w for w in model.walls if abs(w.start[1]) < TOL_MM and abs(w.end[1]) < TOL_MM][0]
        other = [w for w in model.walls if w is not host][0]
        self.assertWall(host, (0, 0), (5000, 0), 250)
        expected_end = (1000 + 3000 * math.cos(math.radians(3)), 100 + 3000 * math.sin(math.radians(3)))
        self.assertWall(other, (1000, 100), expected_end, 250, delta = 1e-6)

    def test_door_symbol_on_wall_layer_is_ignored(self):
        radius, hinge = 900.0, (2000.0, 125.0)
        arc = [(hinge[0] + radius * math.cos(math.radians(a)), hinge[1] + radius * math.sin(math.radians(a)))
               for a in range(0, 91, 6)]
        door = [seg(hinge, (2900, 125))] + [seg(p_1, p_2) for p_1, p_2 in zip(arc, arc[1:])]
        model = run(segments = [seg((0, 0), (2000, 0)), seg((0, 250), (2000, 250)),
                                seg((2900, 0), (5000, 0)), seg((2900, 250), (5000, 250)),
                                seg((2000, 0), (2000, 250)), seg((2900, 0), (2900, 250)), *door])

        self.assertEqual(len(model.walls), 2)
        self.assertEqual(model.warnings, [], "\n".join(model.warnings))

    def test_many_unpaired_lines_give_one_aggregated_warning(self):
        model = run(segments = [seg((i * 3000, i * 3000), (i * 3000 + 1000, i * 3000)) for i in range(12)])

        self.assertEqual(model.walls, [])
        self.assertEqual(len(model.warnings), 1)
        self.assertIn("12 linii fără față opusă", model.warnings[0])
        self.assertEqual(model.warnings[0].count(")-("), 5)

    def test_ten_unpaired_lines_are_listed_separately(self):
        model = run(segments = [seg((i * 3000, i * 3000), (i * 3000 + 1000, i * 3000)) for i in range(10)])

        self.assertEqual(len(model.warnings), 10)


class TestColumnsTouching(unittest.TestCase):

    def test_two_columns_sharing_a_side_drawn_as_segments_give_warnings_only(self):
        """Comportament documentat: latura comună creează ramificații, iar înlănțuirea nu ghicește
        cum se împart segmentele → niciun stâlp, avertismente pentru toate segmentele."""
        pts = [((0, 0), (400, 0)), ((400, 0), (400, 400)), ((400, 400), (0, 400)), ((0, 400), (0, 0)),
               ((400, 0), (800, 0)), ((800, 0), (800, 400)), ((800, 400), (400, 400))]
        model = run(segments = [seg(p_1, p_2, COL) for p_1, p_2 in pts])

        self.assertEqual(model.columns, [])
        self.assertEqual(len(model.warnings), 7)
        self.assertTrue(all(warn.startswith("Stâlp:") for warn in model.warnings))


class TestSlowPerformance(unittest.TestCase):

    MAX_SECONDS = 5.0

    def test_slow_wall_grid_5040_segments_under_5_seconds(self):
        segments = wall_grid_segments(36)
        self.assertEqual(len(segments), 5040)

        start   = time.perf_counter()
        model   = run(segments = segments)
        elapsed = time.perf_counter() - start

        self.assertEqual(model.warnings, [])
        self.assertEqual(len(model.walls), 72)
        total = sum(math.dist(wall.start, wall.end) for wall in model.walls)
        self.assertAlmostEqual(total, 2 * 36 * 35 * 4000.0, delta = 1.0)
        self.assertLess(elapsed, self.MAX_SECONDS)


if __name__ == "__main__":
    unittest.main()
