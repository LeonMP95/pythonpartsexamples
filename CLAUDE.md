# Reguli de lucru în acest repository

## Unde se scrie codul nou

- **Tot codul nou (scripturi, fișiere `.pyp`, date, teste, documentație) se salvează în folderul `NewAll/`.**
- În `NewAll/` se păstrează structura de directoare PythonParts, ca importurile și căile din `.pyp` să funcționeze după copierea în `Usr\Local` al Allplan:
  - scripturile Python în `NewAll/PythonPartsExampleScripts/<Categorie>/<Proiect>/`
  - fișierele `.pyp` (și imaginile de previzualizare) în `NewAll/Library/Examples/PythonParts/<Categorie>/<Proiect>/`
  - în `.pyp`, `<Script><Name>` este calea relativă la `PythonPartsExampleScripts`, de exemplu `ReinforcementExamples\SeismicColumn\SeismicColumn.py`
- Fiecare proiect nou are un `README.md` (în română) și, unde se poate, teste unitare care rulează fără Allplan.

## Sursa de documentare (doar citire)

- `PythonPartsExampleScripts/` și `Library/` din rădăcină sunt exemplele oficiale ALLPLAN PythonParts.
  Ele sunt **sursa de documentare** pentru API (`NemAll_Python_*`, `StdReinfShapeBuilder`, `PythonPartUtil`,
  sintaxa paletelor `.pyp` etc.). **Nu se modifică și nu se adaugă fișiere acolo.**
- Înainte de a folosi o funcție API, caută un exemplu care o folosește în aceste foldere și urmează-l.
- Documentația online: https://pythonparts.allplan.com/latest

## Proiecte existente în NewAll

- `ReinforcementExamples/SeismicColumn` - stâlp armat automat conform SR EN 1992-1-1 și P100-1/2013,
  cu eforturi citite din CSV. Teste:

      cd NewAll/PythonPartsExampleScripts
      python -m unittest discover -s ReinforcementExamples/SeismicColumn/tests -t .
