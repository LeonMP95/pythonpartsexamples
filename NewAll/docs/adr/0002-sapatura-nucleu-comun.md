# 0002. Planul de săpătură: contract separat pentru fundații și nucleu geometric comun Allplan/Revit

Data: 2026-11-24   Status: acceptată

## Context
Utilizatorul cere o planșă cu planul de săpătură în Allplan și în Revit 2026: plan cu contururi (bază și cap de
taluz), cote, secțiuni, tabel de volume și note de execuție. Fundațiile vin din model, terenul natural este o cotă
constantă (sau pe zone), iar pantele și spațiul de lucru se introduc pe proiect (studiul geotehnic).

## Decizie
- Nucleu Python pur, doar biblioteca standard, în `NewAll/PythonPartsExampleScripts/StructuralModeling/Excavation/`:
  `FoundationModel` (contract NOU; `StructuralModel.py` nu se modifică), `ExcavationSettings`, `PolygonOps`,
  `ExcavationGeometry`, `ExcavationVolumes`, `ExcavationSections`, `DrawingContent` + `SheetLayout` (conținutul
  planșei ca date neutre), `ExecutionNotes.txt` (note editabile).
- Geometria: conturul la cota z este reuniunea gropilor decalate cu taluzul corespunzător; din aceeași funcție
  rezultă capul de taluz, treptele și săpătura generală. Volume: formulă exactă pentru groapă convexă izolată,
  integrare numerică (Simpson adaptiv) pentru gropi reunite.
- Straturi separate: Allplan (PythonPart + paletă) și Revit (pyRevit), care doar citesc fundațiile și desenează
  conținutul neutru.
- Valori implicite (configurabile în paletă): colțuri ascuțite la capul de taluz; umplutura = săpătura - volumul
  fundațiilor sub teren; coeficientul de afânare se aplică pământului evacuat; terenul pe zone = cotă constantă pe
  zonă (fără interpolare); în Revit, secțiunile sunt vederi de desen (ViewDrafting) în prima versiune.
- Valorile de inginerie vin din paletă; `sapatura.md` (NEVALIDAT) dă doar precompletări și avertismente.

## Alternative respinse
- Extinderea `StructuralModel` cu fundații acum: ar atinge modulele existente; se poate adăuga ulterior opțional.
- shapely / numpy pentru geometrie: nu se instalează ușor în Allplan și pyRevit.
- Secțiuni Revit reale prin model (ViewSection): săpătura nu e element de model; amânat.

## Consecințe
- Același calcul și aceeași planșă în ambele programe; testare completă a nucleului fără Allplan/Revit.
- Reuniunea de poligoane scrisă de noi: cazuri degenerate tratate prin toleranță și teste dedicate.
- Offsetul cu colțuri ascuțite e exact pentru poligoane convexe sau dreptunghiulare compuse; altfel colțuri rotunjite.
