"""Interactor PythonPart: structura unui etaj (stâlpi, pereți, grinzi, plăci) recunoscută dintr-o planșă

Fluxul de lucru:

1.  sursa planșei (paleta):
    -   „Selecție din model”: planșa DWG/PDF importată nativ în Allplan; utilizatorul selectează
        elementele 2D (AllplanDrawingSource);
    -   „Fișier DXF”: fișierul se citește cu DxfSource.read_dxf;
2.  regulile de recunoaștere se citesc din fișierul JSON ales (gol = data/RulesDefault.json),
    cu suprascrierile din paletă (lățime / înălțime grindă, grosime placă, dacă sunt > 0);
3.  Recognition.recognize produce StructuralModel pentru etajul din paletă;
4.  elementele recunoscute se previzualizează; butonul „Recunoaște și creează” le creează ca
    elemente native Allplan Arhitectură (AllplanBuilder), cu Name = id-ul din model.

S-a ales un interactor (nu un PythonPart cu create_element), ca în
ToolsAndStartExamples/SelectDrawingGeometryForPythonPart.py: selecția elementelor din model cere
un interactor, iar golurile plăcilor cer UUID-ul plăcii deja create (CreateElements întoarce
elementele create, SlabOpeningsFor3DSolids.py:309).
"""

from __future__ import annotations

import dataclasses
import os
import traceback

from dataclasses import dataclass
from typing import Any

import NemAll_Python_BaseElements as AllplanBaseEle
import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_IFW_Input as AllplanIFW
import NemAll_Python_Utility as AllplanUtil

from BaseInteractor import BaseInteractor
from BuildingElementPaletteService import BuildingElementPaletteService

from StructuralModeling.FromDrawing.AllplanBuilder import BuildOptions, CreationReport, build_elements, create_in_document
from StructuralModeling.FromDrawing.AllplanDrawingSource import drawing_from_elements
from StructuralModeling.FromDrawing.DxfSource import DxfSourceError, read_dxf
from StructuralModeling.FromDrawing.Model2D import Drawing2D
from StructuralModeling.FromDrawing.Recognition import recognize
from StructuralModeling.FromDrawing.RecognitionRules import RecognitionRules, RulesError, load_rules
from StructuralModeling.FromDrawing.StructuralModel import Level, StructuralModel, StructuralModelError

CREATE_EVENT_ID       = 1001
SOURCE_MODEL          = 1
SOURCE_DXF            = 2
DEFAULT_RULES_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "RulesDefault.json")
MAX_WARNINGS_IN_BOX   = 15
PREVIEW_LEVEL_NAME    = "-"          # numele etajului nu influențează recunoașterea pentru previzualizare
UNEXPECTED_ERROR_TEXT = ("Eroare neașteptată: elementele pot fi create doar parțial sau deloc. "
                         "Detaliile sunt în trace.")


class InputError(ValueError):
    """Date de intrare lipsă sau invalide în paletă"""


INPUT_ERRORS = (InputError, RulesError, DxfSourceError, StructuralModelError)


def check_allplan_version(_build_ele: Any, _version: Any) -> bool:
    """Toate versiunile sunt acceptate"""
    return True


def create_interactor(coord_input             : Any,
                      _pyp_path               : str,
                      _global_str_table_service: Any,
                      build_ele_list          : list,
                      build_ele_composite     : Any,
                      control_props_list      : list,
                      _modify_uuid_list       : list) -> StructuralFromDrawingInteractor:
    """Creează interactorul (semnătura din SelectDrawingGeometryForPythonPart.py:44-67)"""
    return StructuralFromDrawingInteractor(coord_input, build_ele_list, build_ele_composite, control_props_list)


#----------------- logica fără interfață (testabilă fără Allplan)


@dataclass(frozen=True)
class PaletteInput:
    """Valorile din paletă"""

    source        : int
    dxf_file      : str
    rules_file    : str
    level_name    : str
    level_bottom  : float
    storey_height : float
    beam_width    : float
    beam_depth    : float
    slab_thickness: float
    options       : BuildOptions


def read_palette(build_ele: Any) -> PaletteInput:
    """Citește parametrii paletei (build_ele.<Nume>.value)"""
    return PaletteInput(source         = int(build_ele.Source.value),
                        dxf_file       = str(build_ele.DxfFile.value or "").strip(),
                        rules_file     = str(build_ele.RulesFile.value or "").strip(),
                        level_name     = str(build_ele.LevelName.value or "").strip(),
                        level_bottom   = float(build_ele.LevelBottom.value),
                        storey_height  = float(build_ele.StoreyHeight.value),
                        beam_width     = float(build_ele.BeamWidth.value),
                        beam_depth     = float(build_ele.BeamDepth.value),
                        slab_thickness = float(build_ele.SlabThickness.value),
                        options        = BuildOptions(columns = bool(build_ele.CreateColumns.value),
                                                      walls   = bool(build_ele.CreateWalls.value),
                                                      beams   = bool(build_ele.CreateBeams.value),
                                                      slabs   = bool(build_ele.CreateSlabs.value)))


def rules_file_path(palette: PaletteInput) -> str:
    """Fișierul de reguli ales sau cel implicit de lângă script

    Raises:
        RulesError: fișierul implicit lipsește (folderul data/ nu a fost copiat)
    """
    if palette.rules_file:
        return palette.rules_file

    if not os.path.isfile(DEFAULT_RULES_FILE):
        raise RulesError(f"Fișierul de reguli implicit lipsește: {DEFAULT_RULES_FILE}. La instalare copiați și "
                         f"folderul data/ lângă StructuralFromDrawing.py sau alegeți un fișier de reguli în paletă.")

    return DEFAULT_RULES_FILE


def apply_overrides(rules: RecognitionRules, palette: PaletteInput) -> RecognitionRules:
    """Suprascrierile > 0 din paletă (lățime / înălțime grindă, grosime placă)"""
    overrides = {key: value for key, value in (("beam_width", palette.beam_width),
                                               ("beam_depth", palette.beam_depth),
                                               ("slab_thickness", palette.slab_thickness)) if value > 0}

    return dataclasses.replace(rules, **overrides) if overrides else rules


def effective_rules(palette: PaletteInput) -> RecognitionRules:
    """Regulile din fișier (gol = implicit), cu suprascrierile > 0 din paletă

    Raises:
        RulesError: fișier de reguli lipsă sau invalid
    """
    return apply_overrides(load_rules(rules_file_path(palette)), palette)


def level_from_palette(palette: PaletteInput) -> Level:
    """Nivelul etajului din paletă

    Raises:
        InputError, StructuralModelError: nume lipsă sau înălțime nepozitivă
    """
    if not palette.level_name:
        raise InputError("Numele etajului lipsește")

    return Level(palette.level_name, palette.level_bottom, palette.level_bottom + palette.storey_height)


def read_dxf_drawing(path: str) -> Drawing2D:
    """Planșa din fișierul DXF

    Raises:
        InputError, DxfSourceError: cale lipsă, fișier lipsă sau invalid
    """
    if not path:
        raise InputError("Alegeți fișierul DXF")

    return read_dxf(path)


def format_report(level_name: str, drawing: Drawing2D, model: StructuralModel, creation: CreationReport) -> str:
    """Raportul final: rezumatul modelului, elementele create și toate avertismentele"""
    created  = ", ".join(f"{count} {name}" for name, count in creation.counts.items())
    warnings = [*drawing.warnings, *model.warnings, *creation.warnings]
    lines    = [f"{level_name}: {model.summary()}", f"Create în Allplan: {created}"]

    if warnings:
        lines.append("Avertismente:")
        lines.extend(f"  - {warning}" for warning in warnings)

    return "\n".join(lines)


def short_report(report: str) -> str:
    """Raportul limitat pentru fereastra de mesaj (textul complet este în trace)"""
    lines = report.splitlines()
    limit = 3 + MAX_WARNINGS_IN_BOX

    if len(lines) <= limit:
        return report

    return "\n".join(lines[:limit] + [f"  ... încă {len(lines) - limit} avertismente (vezi trace)"])


def file_key(path: str) -> tuple | None:
    """(cale absolută, mtime, mărime) sau None dacă fișierul nu poate fi citit"""
    try:
        stat = os.stat(path)
    except OSError:
        return None

    return os.path.abspath(path), stat.st_mtime_ns, stat.st_size


class InputCache:
    """Memorează planșa DXF, regulile și modelul recunoscut, ca previzualizarea să nu recitească
    fișierele și să nu repete recunoașterea la fiecare schimbare din paletă"""

    def __init__(self):
        self.dxf_key  : tuple | None = None
        self.dxf      : Drawing2D | None = None
        self.rules_key: tuple | None = None
        self.rules    : RecognitionRules | None = None
        self.model_key: tuple | None = None
        self.model_drawing: Drawing2D | None = None
        self.model    : StructuralModel | None = None

    def dxf_drawing(self, path: str) -> Drawing2D:
        """Planșa DXF, recitită doar dacă s-au schimbat calea, data modificării sau mărimea

        Raises:
            InputError, DxfSourceError
        """
        key = file_key(path) if path else None

        if key is None or key != self.dxf_key or self.dxf is None:
            self.dxf_key, self.dxf = None, None
            drawing = read_dxf_drawing(path)
            self.dxf_key, self.dxf = key, drawing

        return self.dxf

    def recognition_rules(self, palette: PaletteInput) -> RecognitionRules:
        """Regulile (recitite doar dacă s-a schimbat fișierul), cu suprascrierile din paletă

        Raises:
            RulesError
        """
        path = rules_file_path(palette)
        key  = file_key(path)
        key  = key[:2] if key else None

        if key is None or key != self.rules_key or self.rules is None:
            self.rules_key, self.rules = None, None
            rules = load_rules(path)
            self.rules_key, self.rules = key, rules

        return apply_overrides(self.rules, palette)

    def preview_model(self, drawing: Drawing2D, palette: PaletteInput) -> StructuralModel:
        """Modelul pentru previzualizare; recunoașterea se repetă doar dacă s-au schimbat planșa,
        regulile (cu suprascrieri) sau cotele etajului (nu și numele etajului)"""
        rules = self.recognition_rules(palette)
        key   = (rules, palette.level_bottom, palette.storey_height)

        if self.model is None or drawing is not self.model_drawing or key != self.model_key:
            level      = Level(palette.level_name or PREVIEW_LEVEL_NAME, palette.level_bottom,
                               palette.level_bottom + palette.storey_height)
            self.model = None
            model      = recognize(drawing, rules, level)
            self.model_key, self.model_drawing, self.model = key, drawing, model

        return self.model


#----------------- interactorul


class StructuralFromDrawingInteractor(BaseInteractor):
    """Selecție (sau DXF) -> recunoaștere -> previzualizare -> creare la apăsarea butonului

    Orice excepție neprevăzută este prinsă aici (limita cu Allplan): textul complet merge în trace,
    iar interactorul rămâne utilizabil.
    """

    def __init__(self, coord_input: Any, build_ele_list: list, build_ele_composite: Any, control_props_list: list):
        self.coord_input            = coord_input
        self.build_ele              = build_ele_list[0]
        self.post_element_selection = None
        self.drawing: Drawing2D | None = None
        self.preview_elements: list = []
        self.cache                  = InputCache()

        self.palette_service = BuildingElementPaletteService(build_ele_list, build_ele_composite,
                                                             self.build_ele.script_name, control_props_list,
                                                             self.build_ele.pyp_file_name)
        self.palette_service.show_palette(self.build_ele.pyp_file_name)

        self.start_input()

        if read_palette(self.build_ele).source == SOURCE_DXF:
            self.load_dxf_for_preview()

    @property
    def document(self) -> Any:
        """documentul de lucru"""
        return self.coord_input.GetInputViewDocument()

    def start_input(self, remove_running_selection: bool = False):
        """Selecția elementelor 2D (SelectDrawingGeometryForPythonPart.py:105-113) sau, pentru DXF, doar paleta

        Args:
            remove_running_selection: oprește întâi selecția în curs (MultiSelection.py:237-238)
        """
        if remove_running_selection and self.post_element_selection is not None:
            AllplanIFW.InputFunctionStarter.RemoveFunction()

        self.post_element_selection = None

        if read_palette(self.build_ele).source == SOURCE_DXF:
            self.coord_input.InitFirstElementInput(
                AllplanIFW.InputStringConvert("Alegeți fișierul DXF și apăsați „Recunoaște și creează”"))
            return

        sel_query   = AllplanIFW.SelectionQuery()
        sel_setting = AllplanIFW.ElementSelectFilterSetting(sel_query, True)

        self.post_element_selection = AllplanIFW.PostElementSelection()

        AllplanIFW.InputFunctionStarter.StartElementSelect("Selectați elementele 2D ale planșei (linii, polilinii, hașuri)",
                                                           sel_setting, self.post_element_selection, True)

    def process_mouse_msg(self, _mouse_msg: int, _pnt: Any, _msg_info: Any) -> bool:
        """Preia elementele selectate (MultiSelection.py:176-181) și actualizează previzualizarea"""
        if self.post_element_selection is None:
            self.draw_preview()
            return True

        elements = self.post_element_selection.GetSelectedElements(self.document)

        if elements:
            try:
                self.drawing = drawing_from_elements(elements, self.coord_input.GetInputViewDocumentID())
            except Exception:                   # pylint: disable=broad-except - limita cu Allplan
                print(traceback.format_exc())
                print("Selecția nu a putut fi convertită; selectați din nou.")
                self.drawing = None
            else:
                print(f"Planșă selectată: {len(self.drawing.segments)} segmente, {len(self.drawing.polylines)} "
                      f"polilinii, {len(self.drawing.hatches)} hașuri, layere: {', '.join(sorted(self.drawing.layers))}")

            self.update_preview()

        self.start_input()          # o nouă selecție înlocuiește planșa curentă

        return True

    def load_dxf_for_preview(self):
        """Citește DXF-ul pentru previzualizare (din cache dacă fișierul nu s-a schimbat); erorile merg în trace"""
        self.drawing = None

        try:
            self.drawing = self.cache.dxf_drawing(read_palette(self.build_ele).dxf_file)
        except INPUT_ERRORS as err:
            print(f"DXF: {err}")
        except Exception:                       # pylint: disable=broad-except - limita cu Allplan
            print(traceback.format_exc())

        self.update_preview()

    def update_preview(self):
        """Pregătește previzualizarea din modelul memorat (fără ferestre de mesaj)"""
        self.preview_elements = []

        if self.drawing is not None:
            try:
                palette               = read_palette(self.build_ele)
                model                 = self.cache.preview_model(self.drawing, palette)
                self.preview_elements = build_elements(model, self.document, palette.options).elements
            except INPUT_ERRORS as err:
                print(f"Previzualizare imposibilă: {err}")
            except Exception:                   # pylint: disable=broad-except - limita cu Allplan
                print(traceback.format_exc())
                self.preview_elements = []
            else:
                print(f"Previzualizare: {model.summary()}")

        self.draw_preview()

    def draw_preview(self):
        """Desenează previzualizarea (LinesFromFileInteractor.py:257)"""
        if self.preview_elements:
            AllplanBaseEle.DrawElementPreview(self.document, AllplanGeo.Matrix3D(), self.preview_elements, True, None)

    def create_elements(self) -> str:
        """Recunoaște și creează elementele; întoarce raportul

        Raises:
            INPUT_ERRORS: date de intrare invalide (nimic nu se creează)
        """
        palette = read_palette(self.build_ele)
        drawing = self.cache.dxf_drawing(palette.dxf_file) if palette.source == SOURCE_DXF else self.drawing

        if drawing is None:
            raise InputError("Selectați întâi elementele 2D ale planșei")

        model    = recognize(drawing, self.cache.recognition_rules(palette), level_from_palette(palette))
        creation = create_in_document(model, self.document, palette.options)

        return format_report(palette.level_name, drawing, model, creation)

    def on_control_event(self, event_id: int):
        """Butonul „Recunoaște și creează”: creare + raport în trace și o singură fereastră de mesaj"""
        if event_id != CREATE_EVENT_ID:
            return

        try:
            report = self.create_elements()
        except INPUT_ERRORS as err:
            report = f"Elementele nu au fost create: {err}"
        except Exception:                       # pylint: disable=broad-except - limita cu Allplan
            print(traceback.format_exc())
            report = UNEXPECTED_ERROR_TEXT

        print(report)
        AllplanUtil.ShowMessageBox(short_report(report), AllplanUtil.MB_OK)

        self.drawing          = None
        self.preview_elements = []
        self.start_input(remove_running_selection = True)

    def modify_element_property(self, page: int, name: str, value: Any):
        """Schimbare în paletă: actualizează previzualizarea (recunoașterea se repetă doar dacă e nevoie)"""
        update_palette = self.palette_service.modify_element_property(page, name, value)

        if name == "Source":
            self.drawing          = None
            self.preview_elements = []
            self.start_input(remove_running_selection = True)

        if name in ("Source", "DxfFile") and read_palette(self.build_ele).source == SOURCE_DXF:
            self.load_dxf_for_preview()
        else:
            self.update_preview()

        if update_palette:
            self.palette_service.update_palette(-1, False)

    def on_preview_draw(self):
        """Redesenează previzualizarea"""
        self.draw_preview()

    def on_mouse_leave(self):
        """Redesenează previzualizarea"""
        self.draw_preview()

    def on_value_input_control_enter(self) -> bool:
        """Fără câmp de valoare în linia de dialog"""
        return True

    def on_cancel_function(self) -> bool:
        """ESC: închide paleta și selecția (MultiSelection.py:209-218)"""
        self.palette_service.close_palette()

        if self.post_element_selection is not None:
            AllplanIFW.InputFunctionStarter.RemoveFunction()
            self.post_element_selection = None

        self.preview_elements = []

        return True
