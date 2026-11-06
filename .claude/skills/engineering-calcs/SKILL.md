---
name: engineering-calcs
description: Reguli pentru codul de calcul ingineresc (SR EN 1992-1-1, P100-1/2013) - de unde vin formulele, unități, cazuri de referință, validare de către utilizator. Folosește-l la scrierea sau verificarea oricărui calcul de inginerie.
---

# Calcule de inginerie

## Sursa formulelor
- Singura sursă acceptată: fișierele din `references/` ale acestui skill, validate de utilizator.
- Fiecare fișier de referință are în antet: normă, articol, status (`VALIDAT` / `NEVALIDAT`), data validării.
- Fișierele `NEVALIDAT` se pot folosi doar pentru prototip, iar rezultatul se marchează ca atare.
- Nicio valoare sau formulă din memoria modelului. Ce lipsește se raportează.
- Toate fișierele de referință actuale sunt `NEVALIDAT`: au fost precompletate din codul prototipului `SeismicColumn`, nu din textul normei.

## Fișiere
```
references/
  index.md                  lista fișierelor și statusul lor
  materiale-ec2.md          rezistențe, coeficienți parțiali, bloc de compresiuni
  stalpi-ec2.md             armare minimă/maximă, ordinul 2, oblic, tăietoare, ancoraje
  stalpi-p100.md            reguli seismice pentru stâlpi (DCH, DCM)
```
Un subiect per fișier, tabele în format markdown. Fișiere noi (grinzi, pereți, acoperiri, ancoraje) se adaugă la fel și se trec în `index.md`.

## Legătura cu codul
- Fiecare valoare dintr-un fișier de referință are un identificator (de ex. `P100-STALP-DCH-RHO-MIN`).
- Codul care folosește valoarea pune identificatorul în comentariu sau în docstring.
- La validare, utilizatorul corectează valoarea în fișier; `calc-engineer` actualizează codul și `norm-verifier` confirmă.

## Reguli de cod
- Unități SI interne (N, mm, MPa), conversii doar la intrare și ieșire.
- Docstring: sursă, unități, domeniu de valabilitate.
- Eroare explicită în afara domeniului de valabilitate.
- Rotunjiri doar la afișare și la alegerea constructivă finală (de ex. distanța etrierilor rotunjită în jos la 25 mm), niciodată în calculul intermediar.
- Rotunjirile constructive se fac mereu în sens acoperitor.

## Cazuri de referință
- `NewAll/reference_cases/<subiect>/`: date de intrare, rezultat așteptat, sursa (calcul manual al utilizatorului, exemplu din manual, alt soft validat), toleranța.
- Un modul de calcul nu e gata fără cel puțin un caz de referință trecut.

## Validare
Rezultatele se folosesc pe proiecte reale doar după ce utilizatorul a validat modulul pe cazurile de referință.
