# Structură din planșă - modelare 3D din planșe de arhitectură (prototip)

Modulul recunoaște stâlpii, pereții, grinzile și plăcile dintr-o planșă de arhitectură și le creează
în Allplan ca elemente native (stâlp, perete, grindă, placă), câte un etaj pe rulare.
Planșa este un DWG sau un PDF vectorial importat în Allplan, sau un fișier DXF citit direct.
Recunoașterea se face după numele layerelor, pe baza unui fișier de reguli.
Modulul este separat de modulele de armare; acestea pot prelua ulterior elementele create.

## Fișiere

| Fișier | Rol |
|---|---|
| `Model2D.py` | Planșa 2D neutră (segmente, polilinii, hașuri, în mm) - contractul dintre surse și recunoaștere |
| `StructuralModel.py` | Modelul structural (etaj, stâlp, perete, grindă, placă) - contractul cu Allplan și cu modulele de armare |
| `RecognitionRules.py`, `data/RulesDefault.json` | Regulile de recunoaștere: layer → tip de element, toleranțe, dimensiuni implicite |
| `Recognition.py` | Recunoașterea elementelor (Python pur, fără Allplan) |
| `DxfSource.py` | Citirea directă a fișierelor DXF (cu ezdxf) |
| `AllplanDrawingSource.py` | Citirea elementelor 2D selectate din modelul Allplan |
| `AllplanBuilder.py` | Crearea elementelor native Allplan |
| `StructuralFromDrawing.py` | Interactorul (scriptul pornit din Library) |
| `tests/` | Teste unitare și de integrare, rulează fără Allplan |
| `NewAll/Library/.../StructuralModeling/FromDrawing/StructuralFromDrawing.pyp` | Paleta de proprietăți |

## Instalare

1. Copiați conținutul folderului `NewAll/` (`Library` și `PythonPartsExampleScripts`) direct în
   `C:\Users\<utilizator>\Documents\Nemetschek\Allplan\<versiune>\Usr\Local`.
   **Copiați și folderul `data/`** de lângă script: conține regulile implicite.
2. Doar pentru citirea directă DXF: instalați pachetul `ezdxf` în Allplan cu unealta
   „Install Python Package” din PythonParts SDK (versiunea testată: 1.4.5, licență MIT).
   Fără ezdxf, modulul funcționează cu planșe importate în Allplan.

## Flux de lucru

1. **Importați planșa** etajului în Allplan cu importul nativ: DWG/DXF, sau PDF **vectorial**.
   PDF-urile scanate (imagini) nu pot fi folosite.
2. **Verificați numele layerelor** din planșa importată: pe ce layere sunt stâlpii, pereții structurali,
   grinzile și conturul plăcii.
3. **Adaptați fișierul de reguli**, dacă layerele nu se potrivesc cu regulile implicite (vezi mai jos).
   Salvați o copie proprie; nu modificați `RulesDefault.json`.
4. Porniți **Library → Private → Examples → PythonParts → StructuralModeling → FromDrawing**.
5. În paletă alegeți:
   - **Sursa**: „Selecție din model” (apoi selectați elementele 2D ale planșei) sau „Fișier DXF”;
   - **Fișierul de reguli** (gol = regulile implicite);
   - **Etajul**: nume, cotă jos [mm], înălțime etaj [mm];
   - **Suprascrieri** (0 = valoarea din reguli): lățime și înălțime grindă, grosime placă;
   - **Elementele create**: stâlpi, pereți, grinzi, plăci.
6. Verificați **previzualizarea**. Ea se actualizează la fiecare schimbare.
7. Apăsați **„Recunoaște și creează”**. La final apare o fereastră cu rezumatul și avertismentele;
   ele apar și în fereastra de trace.
8. Repetați pentru fiecare etaj, cu planșa și cotele lui.

## Fișierul de reguli (JSON)

```json
{
  "layers": [
    {"pattern": "A-STALPI*",    "element": "column"},
    {"pattern": "A-PERETI-BA*", "element": "wall"},
    {"pattern": "S-GRINZI*",    "element": "beam"},
    {"pattern": "S-PLACA*",     "element": "slab"}
  ],
  "beam_width": 250,
  "beam_depth": 600,
  "slab_thickness": 180
}
```

- `layers`: lista de reguli. `pattern` acceptă `*` și `?` și nu ține cont de literele mari sau mici.
  **Prima regulă care se potrivește câștigă.** `element` este `column`, `wall`, `beam` sau `slab`.
  Layerele care nu se potrivesc cu nicio regulă se ignoră (mobilier, cote, texte etc.).
- Regulile implicite prind layere care conțin `STALP`, `STÂLP`, `COLUMN`, `GRIND`, `GRINZ`, `BEAM`,
  `PLAC`, `SLAB`, `PERE`, `WALL`. Atenție: `*PLAC*` prinde și layere ca „PLACAJ”, iar `*PERE*` prinde
  toți pereții, inclusiv compartimentările nestructurale. Pentru planșe reale, scrieți reguli precise.

| Cheie | Implicit | Unitate | Rol |
|---|---|---|---|
| `column_min_size` / `column_max_size` | 150 / 2000 | mm | laturile admise ale unui stâlp |
| `wall_min_thickness` / `wall_max_thickness` | 100 / 800 | mm | grosimile admise ale unui perete |
| `wall_min_length` | 300 | mm | lungimea minimă a unui perete |
| `parallel_tolerance_deg` | 1,0 | grade | abaterea admisă între fețele unui perete |
| `point_tolerance` | 5 | mm | distanța sub care două puncte sunt identice |
| `beam_width` / `beam_depth` | 300 / 500 | mm | secțiunea grinzilor (planșele de arhitectură nu o conțin) |
| `slab_thickness` | 150 | mm | grosimea plăcilor |

## Ce se recunoaște

| Desen pe layer | Element creat |
|---|---|
| contur închis (polilinie, hașură, cerc) pe layerul stâlpilor, cu laturi în limite | stâlp cu secțiunea conturului (inclusiv L, circular) |
| segmente libere care formează un contur închis, pe layerul stâlpilor | stâlp |
| două linii paralele pe layerul pereților, la distanța unei grosimi admise | perete pe axa dintre ele |
| dreptunghi îngust pe layerul pereților | perete |
| linie (axă) pe layerul grinzilor | grindă cu secțiunea din reguli |
| dreptunghi pe layerul grinzilor | grindă cu lățimea dreptunghiului |
| contur închis pe layerul plăcilor; contururile din interior | placă; goluri în placă |

- La pereți se tratează: capetele închise, colțurile (L), ramificațiile (T), intersecțiile (X),
  golurile de uși și ferestre și simbolul de ușă (canat și arc) desenat pe layerul pereților.
- Id-urile se pun în proprietatea **Name**: stâlpi `S1, S2…`, pereți `P1…`, grinzi `G1…`, plăci `PL1…`,
  numerotate de sus în jos și de la stânga la dreapta.
- **Cote**: stâlpii și pereții merg de la cota de jos la cota de sus a etajului. Grinzile și plăcile
  au fața de sus la cota de sus a etajului.
- **Nu se ghicește**: ce e ambiguu (contur în afara limitelor, linie fără față opusă, segmente care
  nu se închid) nu devine element, ci avertisment, cu poziția. Multe avertismente de același tip se
  adună într-unul singur.

## Citirea directă DXF

- Entități: LINE, LWPOLYLINE, POLYLINE, CIRCLE, ARC, ELLIPSE, SPLINE (discretizate), HATCH (fiecare
  contur exterior separat, cu golurile lui), INSERT/MINSERT (blocuri explodate; entitățile de pe
  layerul 0 primesc layerul inserției). Textele și cotele se ignoră.
- Unitățile se iau din `$INSUNITS`. Dacă lipsesc, se presupune mm și apare un avertisment.
- Limite de siguranță: fișier de maximum 50 MB, 1 000 000 de entități (inclusiv din blocuri),
  5 000 000 de puncte. Blocurile care se inserează pe ele însele se sar, cu avertisment.
- DWG nu se citește direct: se importă în Allplan sau se salvează ca DXF.

## Legătura cu armarea

Elementele create sunt obiecte native Allplan cu id-ul în Name. Un modul de armare le poate selecta
după tip și id și le poate citi geometria. Contractul comun în Python este `StructuralModel.py`.
Modulele de armare depind de el, niciodată invers.

## Limitări și ce trebuie verificat în Allplan

Codul care lucrează cu Allplan este testat **doar cu module Allplan simulate**. La prima rulare,
verificați:

1. ce geometrie dau hașurile, umpluturile, simbolurile și macro-urile importate (și dacă au
   coordonate globale);
2. arcele și cercurile importate (discretizarea, capetele);
3. stâlpii poligonali: poziția corectă, fără deplasare dublă;
4. proprietatea Name la pereți, grinzi și plăci (exemplul oficial o arată doar la stâlpi);
5. cotele în vederi 3D, inclusiv pentru etaje cu cote negative;
6. golurile din plăci (se găsește placa creată și golul trece prin toată grosimea);
7. previzualizarea, comutarea Selecție/DXF și fereastra de mesaj (doar la buton).

Alte limitări:

- noduri de pereți în Y sau oblice cu mai mult de doi pereți nu sunt tratate;
- grinzile au secțiunea din reguli sau din paletă, nu din planșă;
- recunoașterea depinde de calitatea planșei: layere corecte, linii fără goluri mici.

## Teste

```
cd NewAll/PythonPartsExampleScripts
python -m unittest discover -s . -p "test_*.py" -t .
```
