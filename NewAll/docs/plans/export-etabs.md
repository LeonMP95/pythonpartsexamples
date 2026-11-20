# Plan: export Allplan → model de calcul ETABS (.e2k)

Status: propus, în așteptarea validării convențiilor și a unui fișier .e2k șablon.
Modul: `NewAll/PythonPartsExampleScripts/StructuralModeling/AnalysisExport/` (separat de FromDrawing și de armare).
Convenții de modelare: `.claude/skills/engineering-calcs/references/model-calcul-p100.md` (NEVALIDAT).

## Straturi
| Strat | Fișiere | Agent | Python pur |
|---|---|---|---|
| (a) Citire model Allplan → model de clădire pe etaje | `AllplanModelReader.py`, `BuildingModel.py`, `LevelInference.py` | allplan-dev | parțial (reader: nu) |
| (b) Model analitic neutru | `AnalyticalModel.py` (Node, Frame, Area, Material, secțiuni, Story, Diaphragm, Support, încărcări, spectru, combinații, sursa de masă), `ModelingConventions.py` + `ModelingConventions.json` (chei MC-*) | backend-dev | da |
| (c) Constructor analitic: axe, unirea nodurilor, offseturi/zone rigide, împărțirea suprafețelor, diafragme, reazeme | `AnalyticalBuilder.py`, `NodeMerger.py`, `AreaSplitter.py` | calc-engineer | da |
| (d) Încărcări, spectru P100 (ca funcție tabelară), combinații, sursa de masă | `LoadsAndSpectrum.py` | calc-engineer | da |
| (e) Scriitori | `writers/AnalysisWriter.py` (interfață), `writers/E2kWriter.py`, `writers/E2kSyntax.py` (singurul loc cu sintaxa .e2k); ulterior `writers/SafWriter.py` pentru AxisVM | backend-dev | da |
| (f) Interactor și paletă | `AnalysisExport.py`, `.pyp` | allplan-dev | nu |

Toate valorile de inginerie vin din `ModelingConventions.json`, niciuna hard-codată. Rapoartele afișează statusul NEVALIDAT până la validare.

## Exemple API pentru citirea modelului (de urmat)
- selecție după tip: `ModifyObjects/ModifyPlaneReferences.py:85-88,113,167-169`; toate elementele: `SlabOpeningsFor3DSolids.py:131`
- pereți: `ModifyPlaneReferences.py:209-237`, `ModifyWall.py:129-155`; grinzi: `ModifyBeam.py:139-157`;
  stâlpi: `ModifyColumn.py:153,168`; plăci: `ModifySlab.py:129,144`; cote: `PlaneConnection.py:130-131`;
  atribute: `LabelElement.py:124`. Fără exemplu: clasa betonului, citirea golurilor din plăci (de verificat în Allplan).

## Ordine
1. (b) + convenții · 2. (c) · 3. (d) · 4. (a) — în paralel, cu un JSON de test (fără valori de normă).
5. (e) ciornă, finalizată după primirea .e2k șablon. 6. (f).
Apoi tester, norm-verifier, code-reviewer, security-reviewer, docs-writer.

## Testare fără ETABS
- test „golden” pe text normalizat, după un .e2k mic exportat de utilizator din versiunea lui de ETABS;
- parser minimal .e2k doar în teste (numără noduri, bare, suprafețe, etaje, combinații);
- invarianți: masa totală față de calcul manual, aria plăcilor = suma ariilor shell, fără noduri dublate,
  o diafragmă pe etaj, reazeme doar la bază, numărul de moduri.
- pe PC: import fără erori, comparație vizuală 3D, masa ETABS vs. raport (±1 %), participare modală ≥ 90 %.

## Riscuri
Sintaxa .e2k dependentă de versiune; Name gol/duplicat în Allplan; axe necentrate, pereți multistrat/curbi;
lipsa exemplelor pentru material și goluri; împărțirea suprafețelor la intersecții (alternativ auto-mesh ETABS);
rezultate potențial NECONSERVATIVE din convenții (diafragmă rigidă cu goluri mari, 0,5·EI, ψ2, q introdus manual).
