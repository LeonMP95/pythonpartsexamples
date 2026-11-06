---
name: project-conventions
description: Convențiile proiectului - structura folderelor NewAll, denumiri, stil de cod. Folosește-l la orice scriere sau revizuire de cod.
---

# Convențiile proiectului

## Structura folderelor
```
PythonPartsExampleScripts/, Library/     exemplele ALLPLAN - DOAR CITIRE (documentație API)
NewAll/                                  tot codul nou
  PythonPartsExampleScripts/<Categorie>/<Proiect>/
    <Proiect>.py          scriptul PythonPart (modelare Allplan)
    <Calcul>.py           modul de calcul, fără NemAll_Python_*
    <Fisiere>.py          citire/scriere fișiere
    README.md             documentația proiectului (română)
    tests/test_*.py       teste unittest, rulează fără Allplan
  Library/Examples/PythonParts/<Categorie>/<Proiect>/
    <Proiect>.pyp         paleta; <Script><Name> = cale relativă la PythonPartsExampleScripts
  reference_cases/        cazuri de referință pentru calcule
  docs/                   ghiduri, ADR
  CHANGELOG.md
```
- Fiecare folder de pachet are `__init__.py`. Dacă un `__init__.py` există deja în exemplele ALLPLAN pentru aceeași categorie, cel din `NewAll` trebuie să aibă același conținut (se suprascriu la instalare).
- Importurile între module: absolute de la `PythonPartsExampleScripts`, de ex. `from ReinforcementExamples.SeismicColumn.ColumnDesign import ...`.

## Denumiri
- Fișiere de modul: `PascalCase.py`, ca în exemplele ALLPLAN.
- Clase: `PascalCase`; funcții și variabile: `snake_case`.
- Parametrii din `.pyp`: `PascalCase` (accesați ca `build_ele.<Nume>.value`).
- Nume descriptive, fără abrevieri obscure. Unitățile de măsură în nume sau în docstring: `length_mm`, `n_kn`.
- Unități interne în calcul: mm, N, MPa. Fișierele de eforturi: kN, kNm.

## Stil
- Funcții sub ~40 de linii, o singură responsabilitate.
- Fără valori „magice” în cod; constantele au nume, iar valorile din normă stau grupate (de ex. `SeismicRules`).
- Erorile se tratează explicit, nu se ignoră. Erorile din fișierele de intrare au mesaje clare în română.
- Type hints și `from __future__ import annotations`.
- Linter: `ruff check --select E9,F .`

## Interfața (palete `.pyp` și modelul Allplan)
- Paginile și textele paletei în română.
- Valorile implicite trebuie să producă un rezultat valid cu fișierul exemplu.
- Rezultatele de calcul se afișează în trace și într-un raport text; elementele modelate nu se creează dacă dimensionarea eșuează.
