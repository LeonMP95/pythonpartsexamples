---
name: architecture-docs
description: Șablon pentru planuri de arhitectură și decizii tehnice (ADR). Folosește-l când proiectezi o funcție nouă sau iei o decizie de arhitectură.
---

# Documente de arhitectură

## Plan de implementare
```
# Plan: <funcția>
Obiectiv: <o propoziție>
Module afectate: <listă>
Interfețe noi/modificate:
  - <semnătură> — <ce face>
Sarcini:
  1. <sarcină> — fișiere: <...> — acceptare: <...> — agent: <...>
Riscuri: <...>
Întrebări pentru utilizator: <...>
```

## Decizie de arhitectură (ADR)
Salvează în `NewAll/docs/adr/NNNN-titlu.md`:
```
# NNNN. <Titlu>
Data: <AAAA-LL-ZZ>   Status: propusă | acceptată | înlocuită
Context: <problema>
Decizie: <ce am ales>
Alternative respinse: <ce și de ce>
Consecințe: <ce câștigăm, ce pierdem>
```

## Principii
- Trei straturi separate pentru fiecare PythonPart:
  1. calcul (Python pur, fără `NemAll_Python_*`, testat complet);
  2. I/O (fișiere de eforturi, rapoarte);
  3. modelare Allplan (citește paleta, apelează calculul, creează elementele).
- Dependențele merg spre interior: scriptul Allplan → calcul, niciodată invers.
- Preferă funcțiile existente din API-ul Allplan (`StdReinfShapeBuilder` etc.) în locul codului scris de la zero.
