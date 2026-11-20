# Convenții pentru modelul de calcul (export ETABS) - P100-1/2013, CR 0-2012, SR EN 1992-1-1

Normă: P100-1/2013, CR 0-2012, SR EN 1990/1992-1-1 + NA · Status: NEVALIDAT · Validat la: -
Scop: valorile și convențiile pe care modulul de export le scrie în modelul ETABS. Nimic din acest fișier
nu se folosește în proiecte reale până când inginerul nu verifică fiecare rând cu textul în vigoare,
completează articolul exact și trece statusul pe VALIDAT.

Coloana „Sursă propunere”:
- **skill**: valoare din skill-ul `structural-engineer-ro` (verificat de autorul lui în noiembrie 2026), tot de confirmat;
- **memorie**: propusă din cunoștințe generale - DE VERIFICAT obligatoriu;
- **convenție**: alegere de modelare (nu e cerință de normă), de aprobat de inginer.

## 1. Spectrul de proiectare (P100-1/2013 cap. 3)

| ID | Mărime | Propunere | Articol | Sursă propunere |
|---|---|---|---|---|
| MC-SPEC-AG | ag | din harta de zonare pentru IMR = 225 ani, pe amplasament (input în paletă) | 3.1, fig. 3.1 | skill |
| MC-SPEC-TC | TC | din harta perioadelor de control (input în paletă) | 3.1, fig. 3.2 | skill |
| MC-SPEC-TB | TB | 0,2·TC | 3.1, tab. 3.1 | skill |
| MC-SPEC-TD | TD | din tabel în funcție de TC (propunere: TC = 0,7 s → 3,0 s; 1,0 s → 3,0 s; 1,6 s → 2,0 s) | tab. 3.1 | memorie |
| MC-SPEC-BETA | β(T), β0 = 2,5 | 0<T≤TB: 1+(β0−1)T/TB; TB<T≤TC: β0; TC<T≤TD: β0·TC/T; T>TD: β0·TC·TD/T² | 3.1, rel. (3.3)-(3.5) | skill |
| MC-SPEC-SD | spectrul de proiectare | Sd(T) = ag·β(T)/q pentru T > TB; pentru 0 < T ≤ TB formula de racordare din normă | 3.2, rel. (3.18)-(3.19) | skill (T > TB); memorie (T ≤ TB) |
| MC-SPEC-GAMMA | γI,e | clasa I: 1,4 · II: 1,2 · III: 1,0 · IV: 0,8 (input: clasa) | 4.4.5, tab. 4.2 | skill |
| MC-SPEC-Q | q | din cap. 5 în funcție de sistem și clasa de ductilitate, redus pentru neregularitate (input în paletă; NU calculat automat) | 5.2.2.2 | skill (regula); valoarea - inginer |
| MC-SPEC-VERT | componenta verticală | avg = 0,7·ag, spectru vertical cu TBv = 0,1·TCv...; considerată doar pentru elementele cerute de normă (console, deschideri mari, elemente precomprimate) - implicit DEZACTIVATĂ | 3.1.1, 4.5.3.? | memorie |

## 2. Analiza modală (P100-1/2013 cap. 4)

| ID | Mărime | Propunere | Articol | Sursă propunere |
|---|---|---|---|---|
| MC-MOD-MASA | participarea masei | suma maselor modale efective ≥ 90 % din masa totală pe fiecare direcție și toate modurile cu masă efectivă > 5 % | 4.5.3.3.1 | memorie |
| MC-MOD-NR | numărul de moduri cerut în ETABS | 3 × numărul de etaje (minim 12), cu verificarea MC-MOD-MASA după rulare | - | convenție |
| MC-MOD-COMB | combinarea modală | CQC; combinarea direcțiilor: SRSS sau 100 % + 30 % (alegere în paletă) | 4.5.3.3.2, 4.5.3.6 | memorie |
| MC-MOD-TORS | torsiunea accidentală | excentricitate e1a = ±0,05·Li pe fiecare direcție, la fiecare nivel (ETABS: „diaphragm eccentricity” 0,05) | 4.5.2.? | memorie |

## 3. Sursa de masă și combinații (CR 0-2012, P100-1/2013)

| ID | Mărime | Propunere | Articol | Sursă propunere |
|---|---|---|---|---|
| MC-MASA-SURSA | sursa de masă | Σ Gk,j + Σ ψ2,i·Qk,i (greutate proprie + permanente suplimentare + fracțiunea ψ2 din utile) | CR 0 6.?, P100-1 3.? | skill (forma) |
| MC-MASA-PSI2 | ψ2,i | locuințe/birouri: 0,3 (CR 0 tab. 4.1)? Unele interpretări P100 folosesc 0,4 pentru utile în gruparea seismică - DE CLARIFICAT; input pe tip de încărcare | CR 0 tab. 4.1, P100-1 3.? | memorie |
| MC-COMB-SLU | grupare fundamentală | Σ 1,35·Gk + 1,5·Qk,1 + Σ 1,5·ψ0,i·Qk,i | CR 0 6.? | skill |
| MC-COMB-SEISM | grupare seismică | Σ Gk + γI,e·AEk + Σ ψ2,i·Qk,i (γI,e inclus în spectru, nu dublat) | CR 0 6.?, P100-1 | skill |
| MC-COMB-SLS | SLS | caracteristică / frecventă / cvasipermanentă - doar dacă se cere | CR 0 | skill |

## 4. Rigidități și modelarea elementelor de beton armat

| ID | Mărime | Propunere | Articol | Sursă propunere |
|---|---|---|---|---|
| MC-RIG-FISURAT | rigiditatea secțiunilor fisurate (calcul ULS) | 0,5·EcIc pentru încovoiere și forfecare la stâlpi, grinzi și pereți (modificatori ETABS) | P100-1 4.4.? / anexa E | memorie |
| MC-RIG-SLS | rigiditatea pentru verificarea driftului | conform anexei E (rigidități reduse specifice SLS / ULS) | P100-1 anexa E | memorie |
| MC-RIG-PLACA | plăci | element „membrane” cu diafragmă rigidă pentru analiza seismică; „shell-thin” dacă placa e verificată din model | - | convenție |
| MC-MAT-EC | modulul de elasticitate | Ecm după clasa betonului (SR EN 1992-1-1 tab. 3.1) | EC2 3.1.3 | skill |
| MC-MAT-GREUT | greutatea specifică a betonului armat | 25 kN/m³ | SR EN 1991-1-1 anexa A | memorie |

## 5. Îmbinarea elementelor (convenții de modelare analitică)

| ID | Mărime | Propunere | Sursă propunere |
|---|---|---|---|
| MC-ANA-AXE | axele analitice | stâlpi și pereți pe axa centrului de greutate; grinzi pe axa lor, la cota feței superioare a plăcii (ETABS: cardinal point „top center” + inserție) | convenție |
| MC-ANA-RIGID | zone rigide la noduri | „end length offsets” automate în ETABS, factor de rigiditate 0,5 (alternativ 0 sau 1 - de ales) | convenție |
| MC-ANA-PERETE | pereți | elemente „shell”, legați de plăci și grinzi la fiecare nivel; golurile de uși/ferestre modelate dacă sunt în modelul Allplan; auto-mesh ETABS ≤ 1 m | convenție |
| MC-ANA-DIAF | diafragme | diafragmă rigidă pe fiecare nivel (o diafragmă pe placă continuă); semi-rigidă dacă placa are goluri mari - avertisment | convenție |
| MC-ANA-REAZEM | reazeme la bază | încastrare la cota superioară a fundației (alternativ: resoarte din studiul geotehnic, nu în prima versiune) | convenție |
| MC-ANA-TOLER | toleranța de unire a nodurilor | 10 mm; excentricitățile mai mari sunt modelate ca offseturi, nu unite | convenție |
| MC-ANA-ETAJ | etaje | nivelurile din modelul Allplan (cota superioară a plăcii) devin „stories” ETABS | convenție |

## 6. Încărcări exportate

| ID | Mărime | Propunere | Sursă propunere |
|---|---|---|---|
| MC-INC-G | greutate proprie | calculată automat de ETABS din materiale (self weight multiplier 1) | convenție |
| MC-INC-GSUPL | permanente suplimentare pe plăci | input în paletă [kN/m²] pe tip de placă/etaj (pardoseli, compartimentări) | convenție |
| MC-INC-Q | utile pe plăci | input în paletă [kN/m²], categoria după SR EN 1991-1-1 tab. 6.2 + NA | skill (sursa) |
| MC-INC-AE | acțiunea seismică | cazuri spectrale pe X și Y cu spectrul MC-SPEC-*, torsiune MC-MOD-TORS | convenție |

## Neincluse în prima versiune (de decis ulterior)
- zăpadă (CR 1-1-3) și vânt (CR 1-1-4);
- interacțiunea teren-structură;
- verificările post-analiză (drift, P-Δ, regularitate) - se fac în ETABS sau într-un modul separat.

Calculul este un suport tehnic și nu înlocuiește proiectul semnat de un inginer atestat și verificarea de
specialitate cerută de Legea 169/2026 (Codul amenajării teritoriului, urbanismului și construcțiilor).
