# Materiale - SR EN 1992-1-1

Normă: SR EN 1992-1-1 cap. 3 și Anexa Națională · Status: NEVALIDAT · Validat la: -
Proveniență: valorile folosite în `ColumnDesign.py` (prototip SeismicColumn). De verificat cu textul normei și cu Anexa Națională.

| ID | Mărime | Valoare / formulă | Articol | Observații |
|---|---|---|---|---|
| EC2-MAT-GAMMA-C | γc (fundamentală și seismică) | 1,5 | 2.4.2.4 | P100-1 cere aceleași valori în gruparea seismică - de verificat |
| EC2-MAT-GAMMA-S | γs | 1,15 | 2.4.2.4 | |
| EC2-MAT-ALPHA-CC | αcc | 1,0 | 3.1.6(1) | valoarea din Anexa Națională - de verificat |
| EC2-MAT-FCD | fcd | αcc·fck/γc | 3.1.6(1) | |
| EC2-MAT-FYD | fyd | fyk/γs | 3.2.7 | diagramă biliniară fără consolidare |
| EC2-MAT-ES | Es | 200 000 MPa | 3.2.7(4) | |
| EC2-MAT-ECU3 | εcu3 | 3,5 ‰ pentru fck ≤ 50; 2,6 + 35·((90−fck)/100)^4 ‰ altfel | tab. 3.1 | |
| EC2-MAT-EC3 | εc3 | 1,75 ‰ pentru fck ≤ 50; 1,75 + 0,55·(fck−50)/40 ‰ altfel | tab. 3.1 | |
| EC2-MAT-LAMBDA | λ | 0,8 pentru fck ≤ 50; 0,8 − (fck−50)/400 altfel | 3.1.7(3) | |
| EC2-MAT-ETA | η | 1,0 pentru fck ≤ 50; 1,0 − (fck−50)/200 altfel | 3.1.7(3) | |
| EC2-MAT-FCTM | fctm | 0,30·fck^(2/3) (fck ≤ 50) | tab. 3.1 | |
| EC2-MAT-FCTD | fctd | αct·0,7·fctm/γc, αct = 1,0 | 3.1.6(2) | αct din Anexa Națională - de verificat |
| EC2-MAT-FBD | fbd | 2,25·η1·η2·fctd, η1 = η2 = 1 | 8.4.2 | condiții bune de aderență (bare verticale), Ø ≤ 32 |
| EC2-MAT-FYK | fyk oțel | 500 MPa (implicit, B500C) | - | se introduce în paletă |
