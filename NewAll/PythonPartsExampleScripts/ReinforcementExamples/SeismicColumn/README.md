# Stâlp armat automat - SR EN 1992-1-1 + P100-1/2013 (prototip)

PythonPart care citește eforturile de calcul dintr-un fișier CSV, dimensionează un
stâlp dreptunghiular din beton armat și modelează armătura în Allplan:

- bare longitudinale distribuite uniform pe contur, opțional prelungite cu lungimea de suprapunere;
- etrier perimetral și agrafe la fiecare bară intermediară, cu cârlige de 10·dbw;
- zone critice la ambele capete, cu etrieri îndesiți;
- raport de calcul `<fisier>_<stalp>_raport.txt`, scris lângă fișierul de eforturi și afișat în fereastra de trace.

## Fișiere

| Fișier | Rol |
|---|---|
| `ColumnDesign.py` | Regulile EC2 și P100-1. Python pur, nu depinde de Allplan |
| `EffortsFile.py` | Citirea fișierului CSV de eforturi |
| `SeismicColumn.py` | Scriptul PythonPart: geometrie și armătură în Allplan |
| `EforturiStalpi_Exemplu.csv` | Fișier de eforturi exemplu (stâlpii S1, S2) |
| `tests/test_column_design.py` | Teste unitare pentru calcul și citirea fișierului |
| `NewAll/Library/.../ReinforcementExamples/SeismicColumn/SeismicColumn.pyp` | Paleta de proprietăți |

În Allplan: **Library → Private → Examples → PythonParts → ReinforcementExamples → SeismicColumn**.

## Formatul fișierului de eforturi

```
Stalp;Combinatie;Tip;N;Mx_sus;My_sus;Mx_jos;My_jos;Vx;Vy
S1;GF1;FUND;2450;35;20;-60;-25;30;45
S1;GS1+X;SEISM;1650;90;210;-120;-290;160;70
```

- Unitățile sunt kN și kNm. N > 0 înseamnă compresiune.
- Separatorul poate fi `;` (atunci se acceptă și virgula zecimală) sau `,`. Liniile care încep cu `#` sunt comentarii.
- `Tip` este `FUND` (grupare fundamentală) sau `SEISM` (grupare seismică).
- `Mx` rotește în jurul axei X, deci solicită latura **h**. `My` solicită latura **b**.
- Coloana `Stalp` este opțională. Dacă există, în paletă se alege stâlpul dorit.

Fișierul se poate exporta direct din programul de analiză (ETABS, SAP2000, Robot, Axis VM) cu un mic script de conversie.

## Ce se calculează

**Armare longitudinală.** Se parcurg diametrele Ø14…Ø32 și numerele de bare pe fiecare latură. Se alege soluția cu cea mai mică arie care respectă:

- distanța liberă minimă între bare (EC2 8.2);
- distanța maximă între barele legate: 150 mm (DCH) / 200 mm (DCM);
- ρ între 1 % și 4 % (DCH) sau între 0,8 % și 4 % (DCM); As ≥ As,min (EC2 9.5.2);
- încovoiere oblică (EC2 5.8.9) pentru fiecare combinație, cu MRd din compatibilitatea deformațiilor (bloc dreptunghiular);
- imperfecțiuni ei = l0/400, excentricitate minimă e0, efecte de ordinul 2 prin metoda curburii nominale.

**Forța axială normalizată.** În gruparea seismică se verifică νd ≤ 0,40 (DCH) / 0,55 (DCM). Dacă limita e depășită, secțiunea trebuie mărită.

**Forța tăietoare.**
- Gruparea fundamentală: VEd din fișier, cu cot θ ≤ 2,5.
- Gruparea seismică: VEd = max(VEd din fișier, γRd·(MRd,sus + MRd,jos)·min(1, ΣMRb/ΣMRc)/lcl), cu cot θ = 1.
- Raportul ΣMRb/ΣMRc se introduce în paletă. Valoarea 1,0 este acoperitoare.

**Zone critice.**
- lcr = max(1,5·hc; lcl/6; 600 mm) pentru DCH și max(hc; lcl/6; 450 mm) pentru DCM.
- Dacă lcl/hc < 3, toată înălțimea este zonă critică.
- Distanța între etrieri: s ≤ min(b0/3; 125; 6·dbL) pentru DCH și min(b0/2; 175; 8·dbL) pentru DCM.
- Confinare: ωwd ≥ 0,12 la baza stâlpilor DCH; în celelalte zone critice DCH, ωwd ≥ 0,08.

**Zona curentă.** s ≤ min(20·Ø, bmin, 400 mm) (EC2 9.5.3), plus condiția din forța tăietoare.

**Suprapuneri.** l0 = α6·lb,rqd cu α6 = 1,5 (EC2 8.7.3).

Toate valorile din P100 sunt grupate în `SeismicRules` (`P100_DCH`, `P100_DCM`) din `ColumnDesign.py`, ca să poată fi verificate și ajustate într-un singur loc.

## Limitări ale prototipului

- **Verificarea valorilor din normativ.** Valorile numerice din P100-1/2013 trebuie verificate de proiectant cu textul în vigoare și cu erata. La fel și valorile EC2 care depind de Anexa Națională.
- **Calculul la capacitate al momentelor.** Condiția stâlp tare – grindă slabă (ΣMRc ≥ 1,3·ΣMRb) nu se verifică, deoarece cere armarea grinzilor. Momentele seismice din fișier trebuie să fie deja cele de calcul, inclusiv amplificările cerute de P100.
- **Ordinul 2.** Se folosește Kφ = 1 și MEd = |M02| + N·ei + M2. Este acoperitor, dar fluajul nu este tratat explicit.
- **Combinarea momentelor.** La încovoierea oblică se combină maximele pe fiecare direcție, chiar dacă apar în secțiuni diferite. Este o ipoteză acoperitoare.
- **Geometrie.** Doar secțiune dreptunghiulară, cu aceeași armare pe toată înălțimea și bare de același diametru.
- **Fără verificare în Allplan.** Generarea armăturii în Allplan nu a fost testată pe o instalație Allplan. Logica a fost rulată cu modulele Allplan simulate. Poziția agrafelor (`create_s_hook`) și a etrierilor trebuie verificată vizual la prima rulare.
- **Responsabilitate.** Rezultatul este o propunere de armare. Responsabilitatea rămâne a inginerului proiectant.

## Teste

```
cd NewAll/PythonPartsExampleScripts
python -m unittest discover -s ReinforcementExamples/SeismicColumn/tests -t .
```
