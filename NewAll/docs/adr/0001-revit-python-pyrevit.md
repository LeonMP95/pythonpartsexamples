# 0001. Modulele Revit 2026 în Python, prin pyRevit (CPython), cu nucleul comun Python pur

Data: 2026-11-22   Status: acceptată (pilot)

## Context
Utilizatorul vrea, în paralel cu modulele Allplan, module Revit 2026 pentru armare și planșe de cofraj, scrise în
Python. Nucleul existent (dimensionare EC2/P100, recunoaștere din planșe, model structural) este Python ≥ 3.9 pur,
fără dependențe de Allplan.

## Decizie
- Stratul Revit se scrie ca extensie **pyRevit**, cu scripturi pe motorul **CPython** (`#! python3`).
  pyRevit 7.1.0 declară testare cu CPython 3.12 pe Revit 2023–2027.
- Nucleul rămâne Python pur, fără `Autodesk.*`; adaptorul Revit primește date simple (tupluri, mm) și le transformă
  în `XYZ`, `Line`, `Rebar`, vederi, cote.
- Versiunea pyRevit se fixează (fără update automat); se retestează după fiecare update Revit 2026.x.
- Pilot cu armarea stâlpului; criterii de trecere: tranzacții, `Rebar.CreateFromCurves` (overload-ul nou cu
  `BarTerminationsData`, cel vechi e depreciat în 2026), `RebarContainer`, memorie la reîncărcări, fără blocaje.

## Alternative respinse
- **IronPython (2.7 / 3.4)**: nu rulează nucleul (Python ≥ 3.9: dataclasses, f-strings, type hints).
- **Dynamo PythonNet3**: grafuri greu de versionat și distribuit.
- **RevitPythonShell**: unealtă de scripting, nu de distribuire.
- **Add-in C# + nucleu Python ca proces separat (CLI/JSON)**: cel mai robust și fără GPL, dar mai mult cod C#.
  Rămâne **planul B** dacă pilotul pyRevit eșuează (ex. blocajul raportat în issue #3998 pe Revit 2026).

## Consecințe
- Un singur limbaj și un nucleu comun pentru Allplan și Revit.
- pyRevit este GPL-3.0: uz intern fără probleme uzuale; distribuirea către terți cere verificare juridică.
- Adaptorul Revit se verifică doar manual, în Revit, pe calculatorul utilizatorului (ca la Allplan).

Surse: https://github.com/pyrevitlabs/pyRevit/releases, https://github.com/pyrevitlabs/pyRevit/issues/3998,
https://github.com/IronLanguages/ironpython3,
https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/069ab1d6-e41d-de8e-cc56-8f4d6e776926.htm
