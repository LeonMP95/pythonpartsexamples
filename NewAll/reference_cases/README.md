# Cazuri de referință pentru calcule

Fiecare caz este un calcul cu rezultat cunoscut, făcut independent de cod (calcul manual, exemplu din manual,
alt program validat). Codul de calcul nu e considerat gata fără cel puțin un caz trecut.

## Structură
```
reference_cases/
  <subiect>/                 de ex. stalp-mrd, stalp-lcr, stalp-forta-taietoare
    <nume_caz>.md            descrierea, sursa și rezultatul așteptat
    <nume_caz>.csv           (opțional) datele de intrare, de ex. eforturi
```

## Șablon `<nume_caz>.md`
```
# <Titlu caz>
Sursă: <calcul manual / manual X pag. Y / program Z vers. W>
Autor și data: <...>
Status: NEVALIDAT | VALIDAT

## Date de intrare
- b × h = ... mm, lcl = ... mm, acoperire = ... mm
- beton ..., oțel fyk = ... MPa, clasa de ductilitate ...
- armare: ...
- eforturi: N = ... kN, M = ... kNm

## Rezultat așteptat
| Mărime | Valoare | Toleranță |
|---|---|---|
| MRd,x | ... kNm | ± 2 % |
```

## Cazuri existente
Niciunul încă. Primul de adăugat: un MRd calculat manual pentru o secțiune de stâlp cu armare dată.
