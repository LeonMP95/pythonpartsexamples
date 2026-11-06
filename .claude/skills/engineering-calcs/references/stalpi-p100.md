# Stâlpi - P100-1/2013

Normă: P100-1/2013 cap. 5 (structuri de beton armat, stâlpi) · Status: NEVALIDAT · Validat la: -
Proveniență: valorile folosite în `ColumnDesign.py` (`P100_DCH`, `P100_DCM`). Au fost scrise din memorie, pornind de la reguli similare din SR EN 1998-1; unele pot diferi de P100-1/2013. Verifică fiecare rând cu textul normativului și cu erata, completează articolul și corectează valoarea.

| ID | Regulă | DCH | DCM | Articol | Observații |
|---|---|---|---|---|---|
| P100-STALP-NU-MAX | forța axială normalizată νd = NEd/(Ac·fcd) | ≤ 0,40 | ≤ 0,55 | TODO | |
| P100-STALP-RHO-MIN | procent minim de armare longitudinală totală | 1,0 % | 0,8 % | TODO | DCM: de verificat |
| P100-STALP-RHO-MAX | procent maxim de armare longitudinală totală | 4 % | 4 % | TODO | |
| P100-STALP-BAR-DIST | distanța maximă între barele longitudinale legate | 150 mm | 200 mm | TODO | |
| P100-STALP-DBL-MIN | diametrul minim al barelor longitudinale | 14 mm | 14 mm | TODO | de verificat |
| P100-STALP-DBW-MIN | diametrul minim al etrierilor | max(8 mm; 0,4·dbL,max) | max(8 mm; 0,4·dbL,max) | TODO | 0,4·dbL·√(fydL/fydw) la oțeluri diferite |
| P100-STALP-SEC-MIN | latura minimă a secțiunii | 300 mm | 250 mm | TODO | doar avertisment în cod |
| P100-STALP-LCR | lungimea zonei critice | max(1,5·hc; lcl/6; 600 mm) | max(hc; lcl/6; 450 mm) | TODO | lcl/hc < 3 → toată înălțimea critică |
| P100-STALP-S-CR | distanța între etrieri în zona critică | min(b0/3; 125 mm; 6·dbL) | min(b0/2; 175 mm; 8·dbL) | TODO | DCH: 6·dbL sau 7·dbL - de verificat |
| P100-STALP-OMEGA-BAZA | ωwd minim în zona critică de la bază | 0,12 | 0,08 | TODO | |
| P100-STALP-OMEGA-ALTE | ωwd minim în celelalte zone critice | 0,08 | - | TODO | |
| P100-STALP-GAMMA-RD | γRd pentru forța tăietoare de capacitate | 1,3 | 1,1 | TODO | de verificat |
| P100-STALP-V-CAP | forța tăietoare de capacitate | VEd = γRd·(MRd,sus + MRd,jos)·min(1; ΣMRb/ΣMRc)/lcl | idem | TODO | |
| P100-STALP-COT | cot θ în gruparea seismică | 1,0 | 1,0 | TODO | ales acoperitor |
| P100-STALP-HOOK | cârligele etrierilor și agrafelor | 135°, 10·dbw | 135°, 10·dbw | TODO | |
| P100-STALP-FIRST | primul etrier de la fața elementului | 50 mm | 50 mm | TODO | |
| P100-STALP-GAMMA | γc, γs în gruparea seismică | 1,5 / 1,15 | 1,5 / 1,15 | TODO | |

Nu sunt implementate (de adăugat în fișier când se implementează):
- condiția stâlp tare – grindă slabă (ΣMRc ≥ 1,3·ΣMRb);
- verificarea de confinare α·ωwd ≥ 30·μφ·νd·εsy,d·bc/b0 − 0,035 (dacă P100 o cere);
- reguli pentru înnădirea barelor în zonele critice.
