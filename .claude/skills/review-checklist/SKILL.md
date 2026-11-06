---
name: review-checklist
description: Checklist pentru revizuirea codului. Folosește-l când revizuiești o schimbare.
---

# Checklist de review

## Corectitudine
- Face codul ce cere criteriul de acceptare?
- Sunt tratate cazurile limită și erorile?
- Unitățile de măsură sunt consecvente?

## Claritate
- Numele spun ce face codul?
- Funcțiile sunt scurte și au o singură responsabilitate?
- Există cod duplicat care ar trebui extras?

## Structură
- Respectă `project-conventions`?
- Calculul este separat de Allplan și de I/O?
- Codul nou e în `NewAll/` și exemplele din rădăcină sunt neatinse?
- Schimbarea e limitată la ce era necesar?

## API Allplan
- Fiecare funcție API folosită are un exemplu în `PythonPartsExampleScripts/` care o folosește la fel?
- Parametrii din `.pyp` se potrivesc cu `build_ele.<Nume>` din script?
- Calea `<Script><Name>` din `.pyp` este corectă?

## Teste
- Există teste pentru codul nou?
- Testele verifică rezultatul, nu doar că funcția rulează?

## Performanță
- `create_element` se apelează la fiecare schimbare din paletă: fără calcule sau citiri de fișiere inutil de lente?
- Bucle inutile, citiri repetate de fișiere?

Severitate: BLOCANT · IMPORTANT · SUGESTIE
