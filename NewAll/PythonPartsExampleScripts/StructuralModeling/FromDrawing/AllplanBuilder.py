"""StructuralModel -> elemente native Allplan Arhitectură (stâlp, perete, grindă, placă, gol în placă)

Fiecare element primește Name = id-ul din model (S1, P3, G2, PL1), ca modulul de armare
să îl poată găsi ulterior.

Cote absolute prin PlaneReferences (SlabOpening.py:117 și 345-354):
    -   stâlpi și pereți: z_bottom -> z_top ale nivelului;
    -   grinzi: fața de sus la z_top, fața de jos la z_top - înălțimea grinzii;
    -   plăci și golurile lor: fața de sus la z_top, fața de jos la z_top - grosimea plăcii.

Modulul nu face calcule de inginerie: doar transpune geometria recunoscută.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import NemAll_Python_AllplanSettings as AllplanSettings
import NemAll_Python_ArchElements as AllplanArchEle
import NemAll_Python_BaseElements as AllplanBaseEle
import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_IFW_ElementAdapter as AllplanEleAdapter

from StructuralModeling.FromDrawing.Model2D import Point2
from StructuralModeling.FromDrawing.StructuralModel import Beam, Column, Slab, StructuralModel, Wall

SINGLE_TIER = 1


@dataclass(frozen=True)
class BuildOptions:
    """Ce tipuri de elemente se creează"""

    columns: bool = True
    walls  : bool = True
    beams  : bool = True
    slabs  : bool = True


@dataclass
class BuildResult:
    """Elementele native de creat, pe tipuri; plăcile păstrează legătura cu Slab (golurile se creează după placă)"""

    columns : list        = field(default_factory = list)
    walls   : list        = field(default_factory = list)
    beams   : list        = field(default_factory = list)
    slabs   : list[tuple] = field(default_factory = list)       # (Slab, SlabElement)
    warnings: list[str]   = field(default_factory = list)

    @property
    def elements(self) -> list:
        """toate elementele native (pentru previzualizare)"""
        return [*self.columns, *self.walls, *self.beams, *(slab_ele for _, slab_ele in self.slabs)]


@dataclass
class CreationReport:
    """Rezultatul creării în document"""

    counts  : dict[str, int] = field(default_factory = dict)
    warnings: list[str]      = field(default_factory = list)


#----------------- utilitare


def plane_references(document: Any, z_bottom: float, z_top: float) -> Any:
    """PlaneReferences cu cote absolute (constructor ca în GetJointData.py:112, cote ca în SlabOpening.py:345-354)

    Cota de sus se setează înainte și după cota de jos, ca ordinea să nu conteze față de valorile implicite.
    """
    plane_ref = AllplanArchEle.PlaneReferences(document, AllplanEleAdapter.BaseElementAdapter())
    plane_ref.SetAbsTopElevation(z_top)
    plane_ref.SetAbsBottomElevation(z_bottom)
    plane_ref.SetAbsTopElevation(z_top)
    return plane_ref


def polygon_2d(points: tuple[Point2, ...]) -> Any:
    """Polygon2D închis (primul punct repetat la final, ca în ClippedSweptSolid.py:45)"""
    pts = [AllplanGeo.Point2D(x, y) for x, y in points]
    return AllplanGeo.Polygon2D(pts + [AllplanGeo.Point2D(points[0][0], points[0][1])])


def line_2d(start: Point2, end: Point2) -> Any:
    """axă 2D"""
    return AllplanGeo.Line2D(AllplanGeo.Point2D(start[0], start[1]), AllplanGeo.Point2D(end[0], end[1]))


def set_name(properties: Any, element_id: str, warnings: list[str]):
    """Name = id (ColumnProperties.Name ca în ModifyColumn.py:215; pentru celelalte proprietăți
    atributul Name nu are exemplu: dacă lipsește, se raportează)"""
    try:
        properties.Name = element_id
    except AttributeError:
        warnings.append(f"{element_id}: numele nu a putut fi setat ({type(properties).__name__} nu are Name)")


def centered_axis(width: float) -> Any:
    """Axă centrată pe grosime (Wall.py:208-233 / Beam.py:206-229, varianta eCenter)"""
    axis_prop          = AllplanArchEle.AxisProperties()
    axis_prop.OnTier   = SINGLE_TIER
    axis_prop.Position = AllplanArchEle.WallAxisPosition.eCenter
    axis_prop.Distance = width / 2
    axis_prop.Extension = -1
    return axis_prop


def _distance(start: Point2, end: Point2) -> float:
    return ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5


#----------------- elemente


def column_element(column: Column, document: Any, common_props: Any, warnings: list[str]) -> Any:
    """Stâlp cu contur poligonal (ShapeType.ePolygonal + ShapePolygon, ca în ModifyColumn.py:234-235
    și SlabOpeningsFor3DSolids.py:290-291), z_bottom -> z_top"""
    polygon = polygon_2d(column.outline)

    column_prop                  = AllplanArchEle.ColumnProperties()
    column_prop.ShapeType        = AllplanArchEle.ShapeType.ePolygonal
    column_prop.ShapePolygon     = polygon
    column_prop.PlaneReferences  = plane_references(document, column.level.z_bottom, column.level.z_top)
    column_prop.CommonProperties = common_props
    set_name(column_prop, column.id, warnings)

    start = column.outline[0]

    return AllplanArchEle.ColumnElement(column_prop, AllplanGeo.Point3D(start[0], start[1], 0))


def wall_element(wall: Wall, document: Any, common_props: Any, warnings: list[str]) -> Any:
    """Perete cu un singur strat, grosime centrată pe axă (Wall.py:158-248), z_bottom -> z_top"""
    wall_prop                         = AllplanArchEle.WallProperties()
    wall_prop.Axis                    = centered_axis(wall.thickness)
    wall_prop.TierCount               = SINGLE_TIER
    wall_prop.StartNewJoinedWallGroup = True
    set_name(wall_prop, wall.id, warnings)

    tier_prop                  = wall_prop.GetWallTierProperties(SINGLE_TIER)       # indicii straturilor încep de la 1
    tier_prop.PlaneReferences  = plane_references(document, wall.level.z_bottom, wall.level.z_top)
    tier_prop.Thickness        = wall.thickness
    tier_prop.CommonProperties = common_props

    return AllplanArchEle.WallElement(wall_prop, line_2d(wall.start, wall.end))


def beam_element(beam: Beam, document: Any, common_props: Any, warnings: list[str]) -> Any:
    """Grindă dreptunghiulară cu axa centrată (Beam.py:158-235), fața de sus la z_top"""
    z_top = beam.level.z_top

    beam_prop = AllplanArchEle.BeamProperties()
    beam_prop.SetAxis(centered_axis(beam.width))
    beam_prop.PlaneReferences           = plane_references(document, z_top - beam.depth, z_top)
    beam_prop.ShapeType                 = AllplanArchEle.ShapeType.eRectangular
    beam_prop.Width                     = beam.width
    beam_prop.IsStartNewJoinedBeamGroup = True
    beam_prop.CommonProperties          = common_props
    set_name(beam_prop, beam.id, warnings)

    return AllplanArchEle.BeamElement(beam_prop, line_2d(beam.start, beam.end))


def slab_element(slab: Slab, document: Any, common_props: Any, warnings: list[str]) -> Any:
    """Placă cu un singur strat (Slab.py:169-211), fața de sus la z_top"""
    z_top = slab.level.z_top

    slab_prop                 = AllplanArchEle.SlabProperties()
    slab_prop.PlaneReferences = plane_references(document, z_top - slab.thickness, z_top)
    slab_prop.TierCount       = SINGLE_TIER
    slab_prop.VariableTier    = SINGLE_TIER
    set_name(slab_prop, slab.id, warnings)

    tier_prop                  = slab_prop.GetSlabTierProperties(0)      # ca în Slab.py:189 (range de la 0)
    tier_prop.Thickness        = slab.thickness
    tier_prop.CommonProperties = common_props

    return AllplanArchEle.SlabElement(slab_prop, polygon_2d(slab.outline))


def slab_opening_elements(slab: Slab, slab_uuid: Any, document: Any, common_props: Any) -> list:
    """Golurile plăcii (SlabOpeningsFor3DSolids.py:287-309), pe toată grosimea plăcii"""
    z_top    = slab.level.z_top
    openings = []

    for hole in slab.holes:
        opening_prop                  = AllplanArchEle.SlabOpeningProperties(AllplanArchEle.SlabOpeningType.eOpening)
        opening_prop.ShapeType        = AllplanArchEle.ShapeType.ePolygonal
        opening_prop.ShapePolygon     = polygon_2d(hole)
        opening_prop.CommonProperties = common_props
        opening_prop.PlaneReferences  = plane_references(document, z_top - slab.thickness, z_top)

        openings.append(AllplanArchEle.SlabOpeningElement(opening_prop, AllplanGeo.Point2D(), slab_uuid))

    return openings


#----------------- model complet


def build_elements(model: StructuralModel, document: Any, options: BuildOptions,
                   common_props: Any = None) -> BuildResult:
    """Elementele native pentru tipurile alese (fără golurile plăcilor, care cer placa creată)"""
    if common_props is None:
        common_props = AllplanSettings.AllplanGlobalSettings.GetCurrentCommonProperties()     # Wall.py:53

    result = BuildResult()

    if options.columns:
        for column in model.columns:
            if len(column.outline) < 3:
                result.warnings.append(f"{column.id}: contur cu mai puțin de 3 puncte, stâlp necreat")
                continue
            result.columns.append(column_element(column, document, common_props, result.warnings))

    if options.walls:
        for wall in model.walls:
            if _distance(wall.start, wall.end) <= 0 or wall.thickness <= 0:
                result.warnings.append(f"{wall.id}: axă de lungime zero sau grosime nulă, perete necreat")
                continue
            result.walls.append(wall_element(wall, document, common_props, result.warnings))

    if options.beams:
        for beam in model.beams:
            if _distance(beam.start, beam.end) <= 0 or beam.width <= 0 or beam.depth <= 0:
                result.warnings.append(f"{beam.id}: axă de lungime zero sau secțiune nulă, grindă necreată")
                continue
            result.beams.append(beam_element(beam, document, common_props, result.warnings))

    if options.slabs:
        for slab in model.slabs:
            if len(slab.outline) < 3 or slab.thickness <= 0:
                result.warnings.append(f"{slab.id}: contur invalid sau grosime nulă, placă necreată")
                continue
            slab_ele = slab_element(slab, document, common_props, result.warnings)
            result.slabs.append((slab, slab_ele))

    return result


def create_in_document(model: StructuralModel, document: Any, options: BuildOptions) -> CreationReport:
    """Creează elementele în document (CreateElements ca în GeneralModificationsInteractor.py:154)

    Plăcile se creează una câte una, ca golurile să primească UUID-ul plăcii create
    (SlabOpeningsFor3DSolids.py:309).
    """
    common_props = AllplanSettings.AllplanGlobalSettings.GetCurrentCommonProperties()
    build        = build_elements(model, document, options, common_props)
    report       = CreationReport(warnings = list(build.warnings))
    others       = [*build.columns, *build.walls, *build.beams]

    if others:
        AllplanBaseEle.CreateElements(document, AllplanGeo.Matrix3D(), others, [], None)

    report.counts = {"stâlpi": len(build.columns), "pereți": len(build.walls), "grinzi": len(build.beams),
                     "plăci": 0, "goluri": 0}

    for slab, slab_ele in build.slabs:
        created = AllplanBaseEle.CreateElements(document, AllplanGeo.Matrix3D(), [slab_ele], [], None)
        report.counts["plăci"] += 1

        if not slab.holes:
            continue

        slab_adapters = [ele for ele in created if ele == AllplanEleAdapter.Slab_TypeUUID]   # SlabOpeningsFor3DSolids.py:132

        if not slab_adapters:
            report.warnings.append(f"{slab.id}: placa creată nu a fost găsită, golurile nu au fost create")
            continue

        openings = slab_opening_elements(slab, slab_adapters[0].GetModelElementUUID(), document, common_props)
        AllplanBaseEle.CreateElements(document, AllplanGeo.Matrix3D(), openings, [], None)
        report.counts["goluri"] += len(openings)

    return report

