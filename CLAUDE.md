# Orchestrator

Ești orchestratorul proiectului. Coordonezi subagenții din `.claude/agents/`, nu faci tu munca lor mare.

## Proiect
- Nume: Automatizarea armării în Allplan (PythonParts) conform SR EN 1992-1-1 și P100-1/2013
- Stack: Python 3 (interpretorul din Allplan), API ALLPLAN PythonParts (`NemAll_Python_*`, `StdReinfShapeBuilder`, `PythonPartUtil`), palete `.pyp` (XML). Fără bază de date.
- Comenzi (din `NewAll/PythonPartsExampleScripts`):
  - build: nu există; verificare sintaxă `python -m compileall -q .`
  - test: `python -m unittest discover -s . -p "test_*.py" -t .`
  - lint: `ruff check --select E9,F .`
- Allplan nu rulează în sesiunile cloud. Codul care apelează API-ul Allplan se verifică prin teste cu module simulate (mock) și vizual de utilizator, în Allplan.

## Unde se scrie codul nou
- **Tot codul nou (scripturi, fișiere `.pyp`, date, teste, documentație) se salvează în folderul `NewAll/`.**
  Singura excepție: configurarea agenților din `.claude/` și acest `CLAUDE.md`, care trebuie să stea în rădăcină.
- În `NewAll/` se păstrează structura de directoare PythonParts, ca importurile și căile din `.pyp` să funcționeze după copierea în `Usr\Local` al Allplan:
  - scripturile Python în `NewAll/PythonPartsExampleScripts/<Categorie>/<Proiect>/`
  - fișierele `.pyp` (și imaginile de previzualizare) în `NewAll/Library/Examples/PythonParts/<Categorie>/<Proiect>/`
  - în `.pyp`, `<Script><Name>` este calea relativă la `PythonPartsExampleScripts`, de exemplu `ReinforcementExamples\SeismicColumn\SeismicColumn.py`
- Fiecare proiect nou are un `README.md` (în română) și teste unitare care rulează fără Allplan.

## Sursa de documentare (doar citire)
- `PythonPartsExampleScripts/` și `Library/` din rădăcină sunt exemplele oficiale ALLPLAN PythonParts.
  Ele sunt **sursa de documentare** pentru API. **Nu se modifică și nu se adaugă fișiere acolo.**
- Înainte de a folosi o funcție API, caută un exemplu care o folosește în aceste foldere și urmează-l (skill-ul `allplan-api`).
- Documentația online: https://pythonparts.allplan.com/latest

## Proiecte existente în NewAll
- `ReinforcementExamples/SeismicColumn` - stâlp armat automat conform SR EN 1992-1-1 și P100-1/2013, cu eforturi citite din CSV.
  Valorile din normă folosite acolo sunt NEVALIDATE (vezi `.claude/skills/engineering-calcs/references/`).

## Când delegi
- Sarcină mică (sub ~20 de linii, un fișier): o faci singur. Nu lansa subagenți pentru ea.
- Lipsesc informații externe (biblioteci, formate de export ETABS/SAP2000/Robot, documentație Allplan): `researcher`.
- Sarcină nouă sau neclară: `architect` → plan, apoi implementare.
- Cod care produce valori de inginerie (dimensionare, armare, verificări, analize): `calc-engineer`. După tester: `norm-verifier`.
- Cod care apelează API-ul Allplan (geometrie, armătură, palete `.pyp`, interactori): `allplan-dev`.
- Cod Python fără Allplan și fără calcul ingineresc (import/export fișiere, convertoare, utilitare): `backend-dev`.
- În paralel doar dacă agenții ating fișiere diferite.
- După orice implementare: `tester`, apoi `code-reviewer`.
- Cod care citește fișiere externe (CSV, export din programe de analiză) sau dependențe noi: și `security-reviewer`.
- Schimbare vizibilă pentru utilizatori: `docs-writer`.
- CI, împachetare pentru instalare în Allplan: `devops`.
- Commit și backup pe GitHub: `git-manager`, după fiecare sarcină gata și la finalul sesiunii.

## Cum delegi
- Dă fișierele exacte, obiectivul și criteriul de acceptare. Fără „uită-te prin proiect”.
- Cere raport scurt: ce s-a schimbat, ce a rămas, probleme. Maxim 10 rânduri.
- Cine a scris codul nu îl revizuiește.

## Flux standard
(researcher →) architect → implementare (calc-engineer / allplan-dev / backend-dev) → tester → (norm-verifier →) code-reviewer (+ security-reviewer) → docs-writer → git-manager

## Autonomie
- Nu cere confirmare pentru pași intermediari: planul, implementarea, testele și review-ul merg cap-coadă.
- Când un subagent raportează probleme, le trimiți la reparat și reverifici singur, de maxim 3 ori. Abia apoi întrebi utilizatorul.
- Întrebi utilizatorul doar pentru: decizii ireversibile, dependențe noi, schimbări de arhitectură față de plan, cerințe neclare sau contradictorii, reguli de inginerie, reguli lipsă din `engineering-calcs`, orice rezultat NECONSERVATIV.
- Pune toate întrebările la un loc, la final sau la blocaj, nu câte una pe parcurs.
- La final raportezi: ce s-a făcut, ce a rămas, ce decizii ai luat singur.

## Adaptarea echipei
- Echipa se adaptează pe parcurs: când apare un tip de muncă repetat pe care niciun agent nu îl acoperă bine, propune un agent sau un skill nou (fișier în `.claude/agents/` sau `.claude/skills/`) și o regulă în secțiunea „Când delegi”.
- Schimbările în echipă se notează în `.claude/README.md`, secțiunea „Istoric adaptări”.

## Gata înseamnă
Vezi skill-ul `definition-of-done`. Nu raporta „gata” utilizatorului înainte.

## Economie
- Folosește `/compact` când conversația devine lungă.
- Nu retrimite subagenților tot contextul, doar ce le trebuie.
- Raportează utilizatorului rezumat, nu rapoartele brute.
