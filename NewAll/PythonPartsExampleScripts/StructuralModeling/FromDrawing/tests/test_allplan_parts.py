"""Teste pentru partea Allplan (AllplanDrawingSource, AllplanBuilder, StructuralFromDrawing) cu module Allplan simulate

Modulele NemAll_Python_* sunt înlocuite cu MagicMock înainte de import; clasele de geometrie și de
arhitectură folosite de cod sunt înlocuite, pe durata fiecărui test, cu clase simple care
înregistrează valorile primite. Corectitudinea în Allplan se verifică vizual (vezi README).
"""

from __future__ import annotations

import importlib
import math
import os
import sys
import tempfile
import types
import unittest

from types import SimpleNamespace
from unittest import mock
from unittest.mock import MagicMock

ALLPLAN_MODULES = ["NemAll_Python_AllplanSettings", "NemAll_Python_ArchElements", "NemAll_Python_BaseElements",
                   "NemAll_Python_Geometry", "NemAll_Python_IFW_ElementAdapter", "NemAll_Python_IFW_Input",
                   "NemAll_Python_Utility", "BuildingElementPaletteService"]

for _name in ALLPLAN_MODULES:
    sys.modules.setdefault(_name, MagicMock())


class _BaseInteractor:                       # clasă reală: din MagicMock nu se poate deriva
    """BaseInteractor simulat"""


if not isinstance(getattr(sys.modules.get("BaseInteractor"), "BaseInteractor", None), type):
    sys.modules["BaseInteractor"] = types.SimpleNamespace(BaseInteractor = _BaseInteractor)

try:                                         # Recognition este scris în paralel; testele îl simulează oricum
    importlib.import_module("StructuralModeling.FromDrawing.Recognition")
except Exception:                            # pylint: disable=broad-except
    sys.modules["StructuralModeling.FromDrawing.Recognition"] = types.SimpleNamespace(recognize = MagicMock())

AllplanGeo       = sys.modules["NemAll_Python_Geometry"]
AllplanArchEle   = sys.modules["NemAll_Python_ArchElements"]
AllplanBaseEle   = sys.modules["NemAll_Python_BaseElements"]
AllplanEleAdapter = sys.modules["NemAll_Python_IFW_ElementAdapter"]
AllplanUtil      = sys.modules["NemAll_Python_Utility"]

from StructuralModeling.FromDrawing import AllplanBuilder, AllplanDrawingSource, StructuralFromDrawing  # noqa: E402
from StructuralModeling.FromDrawing.DxfSource import DxfSourceError                                      # noqa: E402
from StructuralModeling.FromDrawing.Model2D import Drawing2D, Hatch2D, Polyline2D, Segment2D            # noqa: E402
from StructuralModeling.FromDrawing.RecognitionRules import RulesError                                  # noqa: E402
from StructuralModeling.FromDrawing.StructuralModel import (Beam, Column, Level, Slab, StructuralModel,  # noqa: E402
                                                            Wall)

TOL_MM = 1e-6
LEVEL  = Level("Etaj 1", 3000.0, 6000.0)


#----------------- geometrie simulată


class Point2D:
    def __init__(self, x = 0.0, y = 0.0):
        self.X, self.Y = float(x), float(y)


class Point3D(Point2D):
    def __init__(self, x = 0.0, y = 0.0, z = 0.0):
        super().__init__(x, y)
        self.Z = float(z)


class Line2D:
    def __init__(self, start, end):
        self.StartPoint, self.EndPoint = start, end


class Polyline2D2:
    def __init__(self, points):
        self.Points = list(points)


class Polygon2D:
    def __init__(self, points = None):
        self.Points = list(points or [])


class Arc2D:
    """arc de cerc, unghiuri în radiani, sens trigonometric"""

    def __init__(self, center, radius, start_angle, end_angle):
        self.center, self.radius, self.start_angle, self.end_angle = center, radius, start_angle, end_angle

    def point(self, angle):
        return Point2D(self.center.X + self.radius * math.cos(angle), self.center.Y + self.radius * math.sin(angle))

    @property
    def StartPoint(self):                    # noqa: N802 - numele din API
        return self.point(self.start_angle)

    @property
    def EndPoint(self):                      # noqa: N802
        return self.point(self.end_angle)


class Path2D:
    def __init__(self):
        self.items = []

    def __iadd__(self, other):
        self.items.append(other)
        return self


class DivisionPoints:
    """Puncte la distanța dată pe arc (simulează AllplanGeo.DivisionPoints, fără capete)"""

    calls: list = []

    def __init__(self, path, length, eps):
        DivisionPoints.calls.append((path, length, eps))
        self.path, self.length = path, length

    def GetPoints(self):                     # noqa: N802
        arc   = self.path.items[0]
        sweep = arc.end_angle - arc.start_angle
        count = math.ceil(abs(sweep) * arc.radius / self.length)
        return [arc.point(arc.start_angle + sweep * i / count) for i in range(1, count)]


GEO_FAKES = {"Point2D": Point2D, "Point3D": Point3D, "Line2D": Line2D, "Polyline2D": Polyline2D2,
             "Polygon2D": Polygon2D, "Arc2D": Arc2D, "Path2D": Path2D, "DivisionPoints": DivisionPoints,
             "Matrix3D": MagicMock}


#----------------- arhitectură simulată


class Props:
    """proprietăți cu atribute libere"""

    def __init__(self, *args):
        self.args  = args
        self.tiers = {}

    def SetAxis(self, axis):                 # noqa: N802
        self.Axis = axis

    def GetWallTierProperties(self, index):  # noqa: N802
        return self.tiers.setdefault(index, Props())

    GetSlabTierProperties = GetWallTierProperties


class PropsWithoutName:
    """proprietăți fără Name (pentru avertisment)"""

    __slots__ = ("PlaneReferences", "TierCount", "VariableTier", "tiers")

    def __init__(self):
        self.tiers = {}

    def GetSlabTierProperties(self, index):  # noqa: N802
        return self.tiers.setdefault(index, Props())


class PlaneReferences:
    def __init__(self, document, adapter):
        self.document, self.bottom, self.top = document, None, None

    def SetAbsBottomElevation(self, value):  # noqa: N802
        self.bottom = value

    def SetAbsTopElevation(self, value):     # noqa: N802
        self.top = value


class Element:
    def __init__(self, props, geometry, *rest):
        self.props, self.geometry, self.rest = props, geometry, rest


class ColumnElement(Element):
    pass


class WallElement(Element):
    pass


class BeamElement(Element):
    pass


class SlabElement(Element):
    pass


class SlabOpeningElement(Element):
    pass


ARCH_FAKES = {"PlaneReferences": PlaneReferences, "ColumnProperties": Props, "WallProperties": Props,
              "BeamProperties": Props, "SlabProperties": Props, "SlabOpeningProperties": Props,
              "AxisProperties": Props, "ColumnElement": ColumnElement, "WallElement": WallElement,
              "BeamElement": BeamElement, "SlabElement": SlabElement, "SlabOpeningElement": SlabOpeningElement,
              "ShapeType": SimpleNamespace(ePolygonal = "ePolygonal", eRectangular = "eRectangular"),
              "WallAxisPosition": SimpleNamespace(eCenter = "eCenter"),
              "SlabOpeningType": SimpleNamespace(eOpening = "eOpening")}


class AllplanFakesMixin(unittest.TestCase):
    """Înlocuiește, pe durata testului, clasele Allplan cu clasele simulate"""

    def setUp(self):
        DivisionPoints.calls = []
        patchers = [mock.patch.multiple(AllplanGeo, **GEO_FAKES),
                    mock.patch.multiple(AllplanArchEle, **ARCH_FAKES),
                    mock.patch.multiple(AllplanEleAdapter, Slab_TypeUUID = "SLAB",
                                        BaseElementAdapter = MagicMock())]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)


#----------------- AllplanDrawingSource


class FakeAdapter:
    """element selectat din model"""

    def __init__(self, geometry, layer_id = 1, children = ()):
        self.geometry, self.layer_id, self.children = geometry, layer_id, list(children)

    def GetModelGeometry(self):              # noqa: N802
        return self.geometry

    def GetCommonProperties(self):           # noqa: N802
        return SimpleNamespace(Layer = self.layer_id)

    def GetElementAdapterType(self):         # noqa: N802
        return SimpleNamespace(GetTypeName = lambda: "Macro")


def pts(*coords):
    return [Point2D(x, y) for x, y in coords]


class TestAllplanDrawingSource(AllplanFakesMixin):

    LAYERS = {1: "S_PERETI", 2: "S_STALPI", 3: "S_PLACI"}

    def setUp(self):
        super().setUp()
        for patcher in (mock.patch.object(AllplanBaseEle.LayerService, "GetShortNameByID",
                                          side_effect = lambda layer_id, _doc: self.LAYERS.get(layer_id, "")),
                        mock.patch.object(AllplanEleAdapter.BaseElementAdapterChildElementsService,
                                          "GetChildModelElementsFromTree",
                                          side_effect = lambda element: element.children)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def convert(self, *elements, seg_len = 100.0):
        return AllplanDrawingSource.drawing_from_elements(list(elements), "DOC", seg_len)

    def test_line_converted_to_segment_with_layer_name(self):
        drawing = self.convert(FakeAdapter(Line2D(Point2D(0, 0), Point2D(5000, 0)), layer_id = 1))

        self.assertEqual(drawing.segments, (Segment2D((0.0, 0.0), (5000.0, 0.0), "S_PERETI"),))
        self.assertEqual(drawing.warnings, ())

    def test_closed_polyline_drops_repeated_last_point(self):
        geo     = Polyline2D2(pts((0, 0), (400, 0), (400, 600), (0, 600), (0, 0)))
        drawing = self.convert(FakeAdapter(geo, layer_id = 2))

        self.assertEqual(drawing.polylines,
                         (Polyline2D(((0.0, 0.0), (400.0, 0.0), (400.0, 600.0), (0.0, 600.0)), True, "S_STALPI"),))

    def test_open_polyline_stays_open(self):
        drawing = self.convert(FakeAdapter(Polyline2D2(pts((0, 0), (1000, 0), (1000, 1000)))))

        self.assertFalse(drawing.polylines[0].closed)
        self.assertEqual(len(drawing.polylines[0].points), 3)

    def test_arc_discretized_with_endpoints_on_radius(self):
        arc     = Arc2D(Point2D(1000, 1000), 500.0, 0.0, math.pi / 2)
        drawing = self.convert(FakeAdapter(arc), seg_len = 100.0)
        poly    = drawing.polylines[0]

        self.assertEqual(DivisionPoints.calls[0][1], 100.0)
        self.assertFalse(poly.closed)
        self.assertEqual(len(poly.points), math.ceil(math.pi / 2 * 500 / 100) + 1)
        self.assertAlmostEqual(poly.points[0][0], 1500.0, delta = TOL_MM)
        self.assertAlmostEqual(poly.points[-1][1], 1500.0, delta = TOL_MM)

        for x, y in poly.points:
            self.assertAlmostEqual(math.hypot(x - 1000, y - 1000), 500.0, delta = TOL_MM)

    def test_full_circle_becomes_closed_polyline(self):
        drawing = self.convert(FakeAdapter(Arc2D(Point2D(0, 0), 300.0, 0.0, 2 * math.pi)))

        self.assertTrue(drawing.polylines[0].closed)
        self.assertGreater(len(drawing.polylines[0].points), 10)

    def test_polygon_with_two_components_becomes_hatch_with_hole(self):
        outer   = [(0, 0), (6000, 0), (6000, 4000), (0, 4000), (0, 0)]
        hole    = [(1000, 1000), (2000, 1000), (2000, 2000), (1000, 1000)]
        drawing = self.convert(FakeAdapter(Polygon2D(pts(*hole, *outer)), layer_id = 3))
        hatch   = drawing.hatches[0]

        self.assertIsInstance(hatch, Hatch2D)
        self.assertEqual(hatch.layer, "S_PLACI")
        self.assertEqual(len(hatch.outer), 4)
        self.assertEqual(hatch.outer[1], (6000.0, 0.0))
        self.assertEqual(len(hatch.holes), 1)
        self.assertEqual(len(hatch.holes[0]), 3)

    def test_group_without_geometry_is_unpacked_into_children(self):
        child_1 = FakeAdapter(Line2D(Point2D(0, 0), Point2D(1, 0)), layer_id = 1)
        child_2 = FakeAdapter(Line2D(Point2D(0, 1), Point2D(1, 1)), layer_id = 2)
        drawing = self.convert(FakeAdapter(object(), children = [child_1, child_2]))

        self.assertEqual({seg.layer for seg in drawing.segments}, {"S_PERETI", "S_STALPI"})

    def test_macro_geometry_list_is_converted(self):
        geos    = [Line2D(Point2D(0, 0), Point2D(1, 0)), Line2D(Point2D(0, 1), Point2D(1, 1))]
        drawing = self.convert(FakeAdapter(geos))

        self.assertEqual(len(drawing.segments), 2)

    def test_unsupported_geometry_reported_in_warnings(self):
        drawing = self.convert(FakeAdapter(object()))

        self.assertEqual(drawing.segments, ())
        self.assertIn("Macro", drawing.warnings[0])

    def test_layer_without_name_reported(self):
        drawing = self.convert(FakeAdapter(Line2D(Point2D(0, 0), Point2D(1, 0)), layer_id = 99))

        self.assertEqual(drawing.segments[0].layer, "")
        self.assertTrue(any("layere" in warning for warning in drawing.warnings))

    def test_non_positive_arc_segment_length_raises(self):
        with self.assertRaises(ValueError):
            self.convert(FakeAdapter(Line2D(Point2D(0, 0), Point2D(1, 0))), seg_len = 0.0)


#----------------- AllplanBuilder


def sample_model() -> StructuralModel:
    return StructuralModel(columns = [Column("S1", ((0, 0), (400, 0), (400, 600), (0, 600)), LEVEL)],
                           walls   = [Wall("P1", (0, 0), (5000, 0), 250.0, LEVEL)],
                           beams   = [Beam("G1", (0, 0), (0, 6000), 300.0, 500.0, LEVEL)],
                           slabs   = [Slab("PL1", ((0, 0), (6000, 0), (6000, 5000), (0, 5000)),
                                           (((1000, 1000), (2000, 1000), (2000, 2000)),), 150.0, LEVEL)])


class SlabAdapter:
    def __eq__(self, other):
        return other == "SLAB"

    def GetModelElementUUID(self):           # noqa: N802
        return "UUID-PL1"


class TestAllplanBuilder(AllplanFakesMixin):

    def build(self, options = AllplanBuilder.BuildOptions()):
        return AllplanBuilder.build_elements(sample_model(), "DOC", options, common_props = "COMMON")

    def test_one_native_element_per_model_element(self):
        result = self.build()

        self.assertEqual([type(ele) for ele in result.elements], [ColumnElement, WallElement, BeamElement, SlabElement])
        self.assertEqual(result.warnings, [])

    def test_names_are_model_ids(self):
        result = self.build()

        self.assertEqual([ele.props.Name for ele in result.elements], ["S1", "P1", "G1", "PL1"])

    def test_column_polygonal_outline_from_bottom_to_top(self):
        column = self.build().columns[0]

        self.assertEqual(column.props.ShapeType, "ePolygonal")
        self.assertEqual([(p.X, p.Y) for p in column.props.ShapePolygon.Points],
                         [(0, 0), (400, 0), (400, 600), (0, 600), (0, 0)])
        self.assertEqual((column.props.PlaneReferences.bottom, column.props.PlaneReferences.top), (3000.0, 6000.0))
        self.assertEqual(column.props.CommonProperties, "COMMON")

    def test_wall_centered_axis_thickness_and_levels(self):
        wall = self.build().walls[0]
        tier = wall.props.tiers[1]

        self.assertEqual(wall.props.Axis.Position, "eCenter")
        self.assertEqual(wall.props.Axis.Distance, 125.0)
        self.assertEqual(tier.Thickness, 250.0)
        self.assertEqual((tier.PlaneReferences.bottom, tier.PlaneReferences.top), (3000.0, 6000.0))
        self.assertEqual((wall.geometry.EndPoint.X, wall.geometry.EndPoint.Y), (5000.0, 0.0))

    def test_beam_top_at_level_top(self):
        beam = self.build().beams[0]

        self.assertEqual((beam.props.PlaneReferences.bottom, beam.props.PlaneReferences.top), (5500.0, 6000.0))
        self.assertEqual(beam.props.Width, 300.0)
        self.assertEqual(beam.props.Axis.Distance, 150.0)

    def test_slab_top_at_level_top(self):
        _, slab = self.build().slabs[0]

        self.assertEqual((slab.props.PlaneReferences.bottom, slab.props.PlaneReferences.top), (5850.0, 6000.0))
        self.assertEqual(slab.props.tiers[0].Thickness, 150.0)
        self.assertEqual(len(slab.geometry.Points), 5)

    def test_options_filter_element_types(self):
        result = self.build(AllplanBuilder.BuildOptions(columns = False, walls = True, beams = False, slabs = False))

        self.assertEqual([type(ele) for ele in result.elements], [WallElement])

    def test_degenerate_wall_skipped_with_warning(self):
        model  = StructuralModel(walls = [Wall("P9", (0, 0), (0, 0), 250.0, LEVEL)])
        result = AllplanBuilder.build_elements(model, "DOC", AllplanBuilder.BuildOptions(), "COMMON")

        self.assertEqual(result.elements, [])
        self.assertIn("P9", result.warnings[0])

    def test_missing_name_attribute_gives_warning(self):
        with mock.patch.object(AllplanArchEle, "SlabProperties", PropsWithoutName):
            result = self.build()

        self.assertTrue(any("PL1" in warning for warning in result.warnings))

    def test_create_in_document_creates_slab_then_openings(self):
        create = MagicMock(side_effect = lambda doc, mat, elements, uuids, asso:
                           [SlabAdapter()] if isinstance(elements[0], SlabElement) else [])

        with mock.patch.object(AllplanBaseEle, "CreateElements", create):
            report = AllplanBuilder.create_in_document(sample_model(), "DOC", AllplanBuilder.BuildOptions())

        self.assertEqual(create.call_count, 3)
        first, slab_call, opening_call = (call.args[2] for call in create.call_args_list)
        self.assertEqual([type(ele) for ele in first], [ColumnElement, WallElement, BeamElement])
        self.assertIsInstance(slab_call[0], SlabElement)
        self.assertIsInstance(opening_call[0], SlabOpeningElement)
        self.assertEqual(opening_call[0].rest, ("UUID-PL1",))
        self.assertEqual((opening_call[0].props.PlaneReferences.bottom, opening_call[0].props.PlaneReferences.top),
                         (5850.0, 6000.0))
        self.assertEqual(report.counts, {"stâlpi": 1, "pereți": 1, "grinzi": 1, "plăci": 1, "goluri": 1})

    def test_openings_skipped_with_warning_when_slab_not_found(self):
        with mock.patch.object(AllplanBaseEle, "CreateElements", MagicMock(return_value = [])):
            report = AllplanBuilder.create_in_document(sample_model(), "DOC", AllplanBuilder.BuildOptions())

        self.assertEqual(report.counts["goluri"], 0)
        self.assertTrue(any("PL1" in warning for warning in report.warnings))


#----------------- StructuralFromDrawing (logica paletei și interactorul)


def build_ele(**overrides):
    values = {"Source": 1, "DxfFile": "", "RulesFile": "", "LevelName": "Etaj 1", "LevelBottom": 3000.0,
              "StoreyHeight": 3000.0, "BeamWidth": 0.0, "BeamDepth": 0.0, "SlabThickness": 0.0,
              "CreateColumns": True, "CreateWalls": True, "CreateBeams": True, "CreateSlabs": True}
    values.update(overrides)
    ele = SimpleNamespace(**{key: SimpleNamespace(value = value) for key, value in values.items()})
    ele.script_name   = "StructuralFromDrawing.py"
    ele.pyp_file_name = "StructuralFromDrawing.pyp"
    return ele


class TestPaletteLogic(unittest.TestCase):

    def test_default_rules_file_exists_and_loads(self):
        palette = StructuralFromDrawing.read_palette(build_ele())
        rules   = StructuralFromDrawing.effective_rules(palette)

        self.assertTrue(os.path.isfile(StructuralFromDrawing.DEFAULT_RULES_FILE))
        self.assertEqual(rules.beam_depth, 500.0)

    def test_positive_overrides_replace_rule_values(self):
        palette = StructuralFromDrawing.read_palette(build_ele(BeamWidth = 250.0, BeamDepth = 600.0, SlabThickness = 0.0))
        rules   = StructuralFromDrawing.effective_rules(palette)

        self.assertEqual((rules.beam_width, rules.beam_depth, rules.slab_thickness), (250.0, 600.0, 150.0))

    def test_invalid_rules_file_raises_rules_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "reguli.json")
            with open(path, "w", encoding = "utf-8") as file:
                file.write("{ nu este json")

            with self.assertRaises(RulesError):
                StructuralFromDrawing.effective_rules(StructuralFromDrawing.read_palette(build_ele(RulesFile = path)))

    def test_level_from_palette(self):
        level = StructuralFromDrawing.level_from_palette(StructuralFromDrawing.read_palette(build_ele()))

        self.assertEqual((level.name, level.z_bottom, level.z_top), ("Etaj 1", 3000.0, 6000.0))

    def test_empty_level_name_raises(self):
        with self.assertRaises(StructuralFromDrawing.InputError):
            StructuralFromDrawing.level_from_palette(StructuralFromDrawing.read_palette(build_ele(LevelName = " ")))

    def test_dxf_path_empty_or_missing_raises(self):
        with self.assertRaises(StructuralFromDrawing.InputError):
            StructuralFromDrawing.read_dxf_drawing("")

        with self.assertRaises(DxfSourceError):
            StructuralFromDrawing.read_dxf_drawing(os.path.join(tempfile.gettempdir(), "nu_exista_12345.dxf"))

    def test_short_report_limits_warning_lines(self):
        report = "\n".join(["a", "b", "Avertismente:"] + [f"  - w{i}" for i in range(40)])
        short  = StructuralFromDrawing.short_report(report)

        self.assertEqual(len(short.splitlines()), 3 + StructuralFromDrawing.MAX_WARNINGS_IN_BOX + 1)


class TestInteractor(AllplanFakesMixin):

    def setUp(self):
        super().setUp()
        self.message_box = MagicMock()
        self.create      = MagicMock(return_value = [])
        for patcher in (mock.patch.object(AllplanUtil, "ShowMessageBox", self.message_box),
                        mock.patch.object(AllplanBaseEle, "CreateElements", self.create),
                        mock.patch.object(AllplanBaseEle, "DrawElementPreview", MagicMock())):
            patcher.start()
            self.addCleanup(patcher.stop)

    def interactor(self, **values):
        return StructuralFromDrawing.StructuralFromDrawingInteractor(MagicMock(), [build_ele(**values)], None, [])

    def test_missing_dxf_shows_error_and_creates_nothing(self):
        interactor = self.interactor(Source = 2, DxfFile = os.path.join(tempfile.gettempdir(), "lipsa_9876.dxf"))
        interactor.on_control_event(StructuralFromDrawing.CREATE_EVENT_ID)

        self.create.assert_not_called()
        self.assertIn("nu au fost create", self.message_box.call_args.args[0])

    def test_no_selection_shows_error(self):
        interactor = self.interactor()
        interactor.on_control_event(StructuralFromDrawing.CREATE_EVENT_ID)

        self.create.assert_not_called()
        self.assertIn("Selectați", self.message_box.call_args.args[0])

    def test_button_recognizes_creates_and_reports_once(self):
        interactor         = self.interactor()
        interactor.drawing = Drawing2D(warnings = ("avertisment planșă",))
        model              = sample_model()
        model.warnings.append("avertisment recunoaștere")

        with mock.patch.object(StructuralFromDrawing, "recognize", MagicMock(return_value = model)) as recognize:
            interactor.on_control_event(StructuralFromDrawing.CREATE_EVENT_ID)

        _, rules, level = recognize.call_args.args
        self.assertEqual(level.z_top, 6000.0)
        self.assertEqual(rules.slab_thickness, 150.0)
        self.assertEqual(self.create.call_count, 2)                 # stâlp/perete/grindă, apoi placa
        self.message_box.assert_called_once()
        text = self.message_box.call_args.args[0]
        self.assertIn("1 stâlpi", text)
        self.assertIn("avertisment planșă", text)
        self.assertIn("avertisment recunoaștere", text)
        self.assertIsNone(interactor.drawing)

    def test_palette_change_updates_preview_without_message_box(self):
        interactor         = self.interactor()
        interactor.drawing = Drawing2D()

        with mock.patch.object(StructuralFromDrawing, "recognize", MagicMock(return_value = sample_model())):
            interactor.modify_element_property(0, "BeamWidth", 250.0)

        self.assertEqual(len(interactor.preview_elements), 4)
        self.message_box.assert_not_called()
        self.create.assert_not_called()

    def test_other_event_ids_are_ignored(self):
        self.interactor().on_control_event(999)

        self.message_box.assert_not_called()


if __name__ == "__main__":
    unittest.main()
