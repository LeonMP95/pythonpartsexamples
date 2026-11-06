"""PythonPart: stâlp dreptunghiular armat automat conform SR EN 1992-1-1 și P100-1/2013

Fluxul de lucru:

1.  eforturile de calcul se citesc dintr-un fișier CSV (vezi EffortsFile.py și
    EforturiStalpi_Exemplu.csv);
2.  modulul ColumnDesign stabilește armarea longitudinală, etrierii, agrafele,
    zonele critice și lungimea de suprapunere;
3.  scriptul de față modelează betonul și armătura în Allplan și scrie raportul de calcul.

Sistemul de coordonate: colțul stâlpului în originea PythonPart-ului, latura b pe X,
latura h pe Y, axa stâlpului pe Z.
"""

from __future__ import annotations

import os

from typing import TYPE_CHECKING

import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_Reinforcement as AllplanReinf
import NemAll_Python_Utility as AllplanUtil
import StdReinfShapeBuilder.GeneralReinfShapeBuilder as GeneralShapeBuilder
import StdReinfShapeBuilder.LinearBarPlacementBuilder as LinearBarBuilder

from CreateElementResult import CreateElementResult
from NemAll_Python_IFW_ElementAdapter import DocumentAdapter
from PythonPartUtil import PythonPartUtil
from StdReinfShapeBuilder.ConcreteCoverProperties import ConcreteCoverProperties
from StdReinfShapeBuilder.ReinforcementShapeProperties import ReinforcementShapeProperties
from StdReinfShapeBuilder.RotationAngles import RotationAngles
from TypeCollections.ModelEleList import ModelEleList

from ReinforcementExamples.SeismicColumn.ColumnDesign import (CONCRETE_CLASSES, FIRST_STIRRUP, ColumnDesignResult,
                                                              ColumnGeometry, DesignOptions, Materials,
                                                              design_column)
from ReinforcementExamples.SeismicColumn.EffortsFile import EffortsFileError, read_efforts_file

if TYPE_CHECKING:
    from __BuildingElementStubFiles.SeismicColumnBuildingElement import \
        SeismicColumnBuildingElement as BuildingElement  # type: ignore
else:
    from BuildingElement import BuildingElement

print('Load SeismicColumn.py')

EXAMPLE_EFFORTS_FILE = os.path.join(os.path.dirname(__file__), "EforturiStalpi_Exemplu.csv")

MARK_STIRRUP      = 1
MARK_HOOK_ALONG_Y = 2
MARK_HOOK_ALONG_X = 3
MARK_LONGITUDINAL = 4


def check_allplan_version(_build_ele: BuildingElement,
                          _version  : float) -> bool:
    """Check the current Allplan version

    Args:
        _build_ele: the building element.
        _version:   the current Allplan version

    Returns:
        True if version is supported by this script
    """

    # Support all versions
    return True


def create_element(build_ele: BuildingElement,
                   _doc     : DocumentAdapter) -> CreateElementResult:
    """Creation of element

    Args:
        build_ele: the building element.
        _doc:      input document

    Returns:
        result of element creation
    """
    return SeismicColumn(build_ele).create()


class SeismicColumn:
    """Creează stâlpul de beton și armătura rezultată din dimensionare"""

    def __init__(self, build_ele: BuildingElement):
        """Constructor

        Args:
            build_ele: building element with the parameter properties
        """
        self.build_ele = build_ele

        self.geom = ColumnGeometry(b               = build_ele.Width.value,
                                   h               = build_ele.Depth.value,
                                   clear_height    = build_ele.Height.value,
                                   cover           = build_ele.ConcreteCover.value,
                                   buckling_factor = build_ele.BucklingFactor.value)

        self.mat = Materials(fck = CONCRETE_CLASSES.get(build_ele.ConcreteClass.value, 30.0),
                             fyk = build_ele.SteelFyk.value)

        self.options = DesignOptions(ductility         = build_ele.DuctilityClass.value,
                                     is_base_column    = build_ele.IsBaseColumn.value,
                                     max_aggregate     = build_ele.MaxAggregate.value,
                                     beam_column_ratio = build_ele.BeamColumnRatio.value)

        self.steel_grade    = build_ele.SteelGrade.value
        self.concrete_grade = build_ele.ConcreteGrade.value

    # ------------------------------------------------------------------------------------------

    def create(self) -> CreateElementResult:
        """Execută dimensionarea și creează elementele

        Returns:
            result of element creation
        """
        model_ele_list = ModelEleList()
        model_ele_list.append_geometry_3d(AllplanGeo.Polyhedron3D.CreateCuboid(self.geom.b,
                                                                               self.geom.h,
                                                                               self.geom.clear_height))

        result = self.run_design()

        reinf_ele_list = ModelEleList()

        if result is not None and result.ok and self.build_ele.CreateReinforcement.value:
            reinf_ele_list += self.create_stirrups_and_hooks(result)
            reinf_ele_list += self.create_longitudinal_bars(result)

        pyp_util = PythonPartUtil()
        pyp_util.add_pythonpart_view_2d3d(model_ele_list)
        pyp_util.add_reinforcement_elements(reinf_ele_list)

        return CreateElementResult(pyp_util.create_pythonpart(self.build_ele))

    def run_design(self) -> ColumnDesignResult | None:
        """Citește eforturile, dimensionează stâlpul și scrie raportul

        Returns:
            rezultatul dimensionării sau None dacă fișierul nu poate fi citit
        """
        file_name = self.build_ele.EffortsFile.value.strip() or EXAMPLE_EFFORTS_FILE

        try:
            cases = read_efforts_file(file_name, self.build_ele.ColumnId.value)
        except (OSError, EffortsFileError) as err:
            print(f"SeismicColumn: fișierul de eforturi nu poate fi citit: {err}")
            return None

        result = design_column(self.geom, self.mat, cases, self.options)
        report = result.report_text()

        print(report)

        if self.build_ele.WriteReport.value:
            self.write_report(file_name, report)

        return result

    def write_report(self, efforts_file: str, report: str):
        """Scrie raportul lângă fișierul de eforturi

        Args:
            efforts_file: calea fișierului de eforturi
            report:       textul raportului
        """
        base        = os.path.splitext(efforts_file)[0]
        column_id   = self.build_ele.ColumnId.value.strip()
        report_file = f"{base}_{column_id}_raport.txt" if column_id else f"{base}_raport.txt"

        try:
            with open(report_file, "w", encoding = "utf-8") as file:
                file.write(report)
        except OSError as err:
            print(f"SeismicColumn: raportul nu poate fi scris în {report_file}: {err}")

    # ------------------------------------------------------------------------------------------

    def placement_zones(self, result: ColumnDesignResult) -> list[tuple[float, float, float, float, float]]:
        """Zonele de dispunere a etrierilor pe înălțime

        Returns:
            listă (z_start, z_end, acoperire_start, acoperire_end, distanță)
        """
        trv    = result.transverse
        height = self.geom.clear_height
        lcr    = trv.critical_length

        if 2.0 * lcr >= height - trv.spacing_current:
            return [(0.0, height, FIRST_STIRRUP, FIRST_STIRRUP, trv.spacing_critical)]

        return [(0.0,          lcr,          FIRST_STIRRUP,       0.0,                 trv.spacing_critical),
                (lcr,          height - lcr, trv.spacing_current, trv.spacing_current, trv.spacing_current),
                (height - lcr, height,       0.0,                 FIRST_STIRRUP,       trv.spacing_critical)]

    def create_stirrups_and_hooks(self, result: ColumnDesignResult) -> list[AllplanReinf.BarPlacement]:
        """Etrierul perimetral și agrafele (câte una pentru fiecare bară longitudinală intermediară),
        cu cârlige la 135° și lungimea dreaptă 10·dbw (P100-1)

        Args:
            result: rezultatul dimensionării

        Returns:
            dispunerile etrierilor și agrafelor
        """
        geom, layout, trv = self.geom, result.layout, result.transverse

        bending_roller = AllplanReinf.BendingRollerService.GetBendingRollerFactor(trv.diameter,
                                                                                  self.steel_grade,
                                                                                  self.concrete_grade,
                                                                                  True)

        shape_props = ReinforcementShapeProperties.rebar(trv.diameter, bending_roller,
                                                         self.steel_grade, self.concrete_grade,
                                                         AllplanReinf.BendingShapeType.Stirrup)

        covers      = ConcreteCoverProperties.all(geom.cover)
        hook_length = 10.0 * trv.diameter

        shapes: list[tuple[int, AllplanReinf.BendingShape]] = []

        stirrup = GeneralShapeBuilder.create_stirrup(geom.b, geom.h, RotationAngles(0, 0, 0),
                                                     shape_props, covers,
                                                     AllplanReinf.StirrupType.names["Normal"], hook_length)
        shapes.append((MARK_STIRRUP, stirrup))

        # agrafe paralele cu Y, prin barele intermediare de pe laturile b
        for x_pos in layout.x_coordinates(geom, trv.diameter)[1:-1]:
            hook = GeneralShapeBuilder.create_s_hook(geom.h, RotationAngles(0, 0, 90),
                                                     shape_props, covers, hook_length)
            hook.Move(AllplanGeo.Vector3D(x_pos, 0, 0))
            shapes.append((MARK_HOOK_ALONG_Y, hook))

        # agrafe paralele cu X, prin barele intermediare de pe laturile h
        for y_pos in layout.y_coordinates(geom, trv.diameter)[1:-1]:
            hook = GeneralShapeBuilder.create_s_hook(geom.b, RotationAngles(0, 0, 0),
                                                     shape_props, covers, hook_length)
            hook.Move(AllplanGeo.Vector3D(0, y_pos, 0))
            shapes.append((MARK_HOOK_ALONG_X, hook))

        placements: list[AllplanReinf.BarPlacement] = []

        for z_start, z_end, cover_start, cover_end, spacing in self.placement_zones(result):
            for mark, shape in shapes:
                if not shape.IsValid():
                    continue

                placements.append(LinearBarBuilder.create_linear_bar_placement_from_to_by_dist(
                    mark, shape,
                    AllplanGeo.Point3D(0, 0, z_start),
                    AllplanGeo.Point3D(0, 0, z_end),
                    cover_start, cover_end, spacing))

        return placements

    def create_longitudinal_bars(self, result: ColumnDesignResult) -> list[AllplanReinf.BarPlacement]:
        """Barele longitudinale drepte; opțional prelungite peste capătul superior cu lungimea de suprapunere

        Args:
            result: rezultatul dimensionării

        Returns:
            dispunerile barelor longitudinale
        """
        geom, layout, trv = self.geom, result.layout, result.transverse

        z_top = geom.clear_height + (result.lap_length if self.build_ele.StarterBars.value else -geom.cover)

        placements: list[AllplanReinf.BarPlacement] = []

        for x_pos, y_pos in layout.positions(geom, trv.diameter):
            polyline = AllplanGeo.Polyline3D()
            polyline += AllplanGeo.Point3D(x_pos, y_pos, 0)
            polyline += AllplanGeo.Point3D(x_pos, y_pos, z_top)

            shape = AllplanReinf.BendingShape(polyline, AllplanUtil.VecDoubleList(), layout.diameter,
                                              self.steel_grade, self.concrete_grade,
                                              AllplanReinf.BendingShapeType.LongitudinalBar)

            placements.append(AllplanReinf.BarPlacement(MARK_LONGITUDINAL, 1, AllplanGeo.Vector3D(),
                                                        AllplanGeo.Point3D(), AllplanGeo.Point3D(), shape))

        return placements
