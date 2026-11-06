---
name: definition-of-done
description: Criteriile după care o sarcină este considerată gata. Folosește-l înainte de a raporta utilizatorului că o sarcină e terminată.
---

# Definiția lui „gata”

O sarcină e gata doar când toate punctele sunt bifate:

- [ ] Criteriul de acceptare din plan este îndeplinit
- [ ] Codul nou este în `NewAll/`; exemplele din rădăcină nu au fost modificate
- [ ] Verificarea de sintaxă trece (`python -m compileall -q .` din `NewAll/PythonPartsExampleScripts`)
- [ ] Toată suita de teste trece, inclusiv testele noi
- [ ] Linter-ul nu raportează erori (`ruff check --select E9,F .`)
- [ ] `code-reviewer` a dat verdict APROBAT (sau problemele BLOCANTE sunt rezolvate)
- [ ] `security-reviewer` a aprobat, dacă sarcina îl cerea
- [ ] Pentru cod de calcul: `norm-verifier` a dat verdict CONFORM și cazurile de referință trec
      (cu referințe `NEVALIDAT`, rezultatul se raportează ca prototip)
- [ ] Pentru cod Allplan: lista cu ce trebuie verificat vizual în Allplan este în raport și în README
- [ ] Documentația și `NewAll/CHANGELOG.md` sunt actualizate, dacă schimbarea e vizibilă
- [ ] Nu au rămas `TODO`-uri noi fără explicație

Dacă un punct nu poate fi bifat, raportează utilizatorului ce lipsește și de ce, în loc de „gata”.
