---
name: revit-api
description: Cum se scrie stratul Revit 2026 al proiectului - extensie pyRevit cu CPython, structura folderelor NewAll/Revit, refolosirea nucleului Python, Rebar API, planșe de cofraj, testare. Folosește-l la planificarea, scrierea sau revizuirea oricărui cod Revit.
---

# Revit 2026 (pyRevit, CPython)

Decizia și alternativele: `NewAll/docs/adr/0001-revit-python-pyrevit.md`.

## Structura
```
NewAll/Revit/
  Armare.extension/                 extensie pyRevit (se adaugă în pyRevit ca extensie locală/de rețea)
    Armare.tab/
      Stalpi.panel/
        ArmareStalp.pushbutton/
          script.py                 #! python3 - doar UI + apel adaptor
      Cofraje.panel/
        PlanseCofraj.pushbutton/
          script.py
    lib/                            cod comun al extensiei (pe sys.path în pyRevit)
      revit_adapters/               conversii date simple <-> Revit API, creare Rebar, vederi, cote
  tests/                            teste pentru logica din lib/ care nu importă Autodesk.*
  README.md
```
- Nucleul comun (de ex. `ReinforcementExamples/SeismicColumn/ColumnDesign.py`,
  `StructuralModeling/FromDrawing/StructuralModel.py`) rămâne în `NewAll/PythonPartsExampleScripts/`;
  extensia adaugă acel folder pe `sys.path`. Modulele nucleului nu importă nimic din Allplan sau Revit.

## Reguli
- Prima linie a scripturilor: `#! python3` (motorul CPython). IronPython nu rulează nucleul.
- Unități: Revit lucrează intern în picioare; convertește cu `UnitUtils.ConvertToInternalUnits(..., UnitTypeId.Millimeters)`.
- Armare: `Rebar.CreateFromCurves` cu overload-ul care primește `BarTerminationsData` (cel cu cârlige separate e depreciat în 2026);
  tipuri de bare (`RebarBarType`), forme (`RebarShape`), `RebarContainer` pentru seturi mari.
- Cofraje: `ViewPlan`/`ViewSection`, `Dimension`, `IndependentTag`, `ViewSheet`; fixează versiunea pyRevit
  (7.1.0 a schimbat comportamentul unor utilitare de vederi).
- Fiecare modificare într-o `Transaction` cu nume; rollback la excepție; mesaj în română.
- Fără semnături API din memorie: documentația oficială Revit API 2026 (help.autodesk.com, Revit-API-MainReference).

## Testare
- Cloud: doar logica din `lib/` care nu importă `Autodesk.*`, plus nucleul (`unittest`).
- PC: verificare în Revit 2026 cu un proiect de test; lista „de verificat în Revit” în README.
