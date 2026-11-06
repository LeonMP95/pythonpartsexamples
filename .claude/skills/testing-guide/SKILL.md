---
name: testing-guide
description: Cum se scriu și se rulează testele în proiect, inclusiv pentru cod care apelează API-ul Allplan. Folosește-l când scrii, rulezi sau repari teste.
---

# Ghid de testare

## Comenzi (din `NewAll/PythonPartsExampleScripts`)
- Toată suita: `python -m unittest discover -s . -p "test_*.py" -t .`
- Un singur proiect: `python -m unittest discover -s <Categorie>/<Proiect>/tests -t .`
- Un singur fișier: `python -m unittest <Categorie>.<Proiect>.tests.test_<nume>`
- După rulare, șterge `__pycache__/` (sunt ignorate de git, dar nu se copiază în Allplan).

## Ce testăm
- Cazul normal
- Cazuri limită: zero, valori negative, liste goale, valori maxime
- Input invalid: trebuie să dea eroare clară, nu rezultat greșit
- Pentru calcule: cazuri de referință cu rezultat cunoscut, calculat independent, cu toleranță explicită (`NewAll/reference_cases/`)

## Cod care apelează Allplan
Allplan nu rulează în cloud. Logica scriptului se testează înlocuind modulele Allplan cu `unittest.mock.MagicMock`
înainte de import:
```python
import sys
from unittest.mock import MagicMock

ALLPLAN_MODULES = [
    "NemAll_Python_BaseElements", "NemAll_Python_BasisElements", "NemAll_Python_Geometry",
    "NemAll_Python_Reinforcement", "NemAll_Python_Utility", "NemAll_Python_IFW_ElementAdapter",
    "NemAll_Python_IFW_Input", "NemAll_Python_AllplanSettings",
    "StdReinfShapeBuilder", "StdReinfShapeBuilder.GeneralReinfShapeBuilder",
    "StdReinfShapeBuilder.LinearBarPlacementBuilder", "StdReinfShapeBuilder.ConcreteCoverProperties",
    "StdReinfShapeBuilder.ReinforcementShapeProperties", "StdReinfShapeBuilder.RotationAngles",
    "CreateElementResult", "PythonPartUtil", "BuildingElement",
    "TypeCollections", "TypeCollections.ModelEleList",
]
for name in ALLPLAN_MODULES:          # adaugă orice alt modul Allplan importat de script,
    sys.modules.setdefault(name, MagicMock())   # inclusiv fiecare submodul separat
```
Se verifică: numărul de dispuneri, pozițiile calculate, zonele, tratarea erorilor. Corectitudinea geometrică finală se verifică vizual în Allplan de utilizator.

## Structura unui test
```
test_<ce>_<condiție>_<rezultat așteptat>
  Pregătire → Acțiune → Verificare
```

## Reguli
- Testele sunt independente între ele și nu depind de ordine.
- Fără acces la rețea. Fișierele de date de test stau lângă teste sau în `NewAll/reference_cases/`.
- Un test care eșuează intermitent este un bug, nu se ignoră.
