---
name: allplan-api
description: Cum se folosește API-ul ALLPLAN PythonParts în acest repo - unde se caută exemple, ce exemple acoperă ce funcții, structura unui PythonPart și a unei palete .pyp. Folosește-l la scrierea, planificarea sau revizuirea oricărui cod care importă NemAll_Python_* sau StdReinfShapeBuilder.
---

# API ALLPLAN PythonParts

## Sursa de adevăr
1. Exemplele oficiale din rădăcina repo-ului: `PythonPartsExampleScripts/` (scripturi) și `Library/` (palete `.pyp`). DOAR CITIRE.
2. Documentația online: https://pythonparts.allplan.com/latest
3. Nicio semnătură de funcție din memorie: caută cu Grep un exemplu care o apelează și copiază forma apelului.

## Unde găsești ce
| Ai nevoie de | Exemple |
|---|---|
| Structura modernă a unui script (`create_element`, `CreateElementResult`, `PythonPartUtil`) | `ReinforcementExamples/BarPlacement/BarPlacement.py` |
| Etrieri, cârlige, forme generale de bare | `ReinforcementExamples/BarShapes/GeneralShapeBuilder.py`, `ClosedStirrupFreeform.py` |
| Bare longitudinale în colțuri / pe laturi de etrier | `ReinforcementExamples/BarPlacement/LongitudinalBarPlacement.py` |
| Bară dreaptă din polilinie (`BendingShape`) | `ReinforcementExamples/AreaPlacementExpand.py`, `PrecastExamples/MWSPlacement.py` |
| Dispuneri liniare, pe zone, rotaționale, spirale | `ReinforcementExamples/BarPlacement/`, `RotationalPlacement.py` |
| Plase sudate | `ReinforcementExamples/MeshPlacement/`, `MeshShapes/` |
| Etichete și cote pentru armătură | `ReinforcementExamples/Labels/` |
| Secțiuni și vederi | `ReinforcementExamples/SectionsAndViews.py` |
| Stâlpi, grinzi, pereți ca obiecte Allplan | `StructuralFramingExamples/`, `ArchitectureExamples/` |
| Selecția elementelor din model | `ModelObjectExamples/SelectionExamples/`, `InteractorExamples/` |
| Citirea datelor elementelor existente | `ObjectAccessExamples/` |
| Date citite din fișier | `InteractorExamples/HaunchReinforcementFromFileInteractor.py` |
| Controale de paletă (combo, checkbox, fișier, expander) | `Library/Examples/PythonParts/PaletteExamples/AllControls.pyp` |
| Parametri de armătură în paletă (`ReinfBarDiameter`, `ReinfSteelGrade`, `ReinfConcreteCover`) | `Library/Examples/PythonParts/PaletteExamples/AllControls.pyp` |

Căută rapid: `Grep` după numele funcției în `PythonPartsExampleScripts/`, de ex. `create_stirrup(`, `BarPlacement(`.

## Structura unui PythonPart
- Script: `check_allplan_version(build_ele, version)` și `create_element(build_ele, doc) -> CreateElementResult`.
- Parametrii paletei se citesc cu `build_ele.<Nume>.value`.
- Elementele se grupează cu `PythonPartUtil`: `add_pythonpart_view_2d3d(...)`, `add_reinforcement_elements(...)`, `create_pythonpart(build_ele)`.
- `create_element` rulează la fiecare schimbare din paletă: calculul trebuie să fie rapid și fără ferestre modale.

## Paleta `.pyp`
- `<Script><Name>`: calea scriptului relativă la `PythonPartsExampleScripts`, cu `\`.
- Schema: `https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd` (ca în exemple).
- Selector de fișier: `ValueType` `String` + `ValueDialog` `OpenFileDialog` + `FileFilter` (vezi `AllControls.pyp`).

## Convenții de geometrie în armătură
- Unități: mm.
- `RotationAngles(x, y, z)` / `RotationUtil` rotesc forma din sistemul local în cel global; verifică într-un exemplu sensul și planul formei.
- `ConcreteCoverProperties` dă acoperirile față de conturul dat formei.
- Mărcile (numerele de poziție) sunt primul argument al dispunerilor.

## Limitare
Allplan nu rulează în sesiunile cloud. Orice cod nou de modelare se testează cu module simulate și se marchează „de verificat vizual în Allplan”.
