---
name: deploy-guide
description: Cum se verifică, se împachetează și se instalează în Allplan proiectele din NewAll. Folosește-l pentru orice sarcină de infrastructură.
---

# Verificare și instalare

## Medii
| Mediu | Scop | Cine instalează |
|---|---|---|
| sesiune cloud | dezvoltare, teste fără Allplan | agenții |
| Allplan local al utilizatorului | verificare vizuală, folosire | doar utilizatorul |

## Verificare (local și în CI, la fiecare push)
Din `NewAll/PythonPartsExampleScripts`:
1. `python -m compileall -q .`
2. `ruff check --select E9,F .`
3. `python -m unittest discover -s . -p "test_*.py" -t .`

## Instalare în Allplan
1. Toate verificările trec.
2. Utilizatorul copiază conținutul folderului `NewAll/` (`Library` și `PythonPartsExampleScripts`) direct în
   `C:\Users\<utilizator>\Documents\Nemetschek\Allplan\<versiune>\Usr\Local`.
3. Pornește PythonPart-ul din Library → Private → Examples → PythonParts → ...
4. Verificare după instalare: lista „ce trebuie verificat în Allplan” din README-ul proiectului.
5. Anulare: șterge din `Usr\Local` fișierele copiate (sau restaurează copia anterioară).

## Pachet (opțional)
Arhivă zip cu conținutul `NewAll/`, fără `tests/`, `reference_cases/` și `__pycache__/`. Doar cu acordul utilizatorului se publică ca release.

## Secrete
Proiectul nu are nevoie de secrete. Dacă apar, doar în variabile de mediu sau în secretele CI. Niciodată în repo.
