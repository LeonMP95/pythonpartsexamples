# Echipă de agenți Claude Code

Pachet de pornire adaptat proiectului de automatizare a armării în Allplan: un orchestrator (sesiunea principală, regulile din `CLAUDE.md`), 12 subagenți și 12 skill-uri.

(Fișierul `README.md` din rădăcină rămâne cel al exemplelor ALLPLAN; acesta descrie echipa de agenți.)

## Instalare
`CLAUDE.md` și folderul `.claude/` sunt deja în rădăcina repo-ului. Pornește `claude` din rădăcină și verifică agenții cu `/agents`.

## Structură
```
CLAUDE.md                  regulile orchestratorului și ale proiectului
.claude/settings.json      permisiuni: ce rulează fără confirmare
.claude/agents/            subagenții
  researcher.md            Sonnet · web + citire · research cu surse
  architect.md             Opus · doar citire · planifică
  calc-engineer.md         Opus   · module de calcul ingineresc, cu surse
  norm-verifier.md         Opus   · doar citire + teste · verifică față de normă
  allplan-dev.md           Opus   · cod pe API-ul Allplan și palete .pyp (înlocuiește frontend-dev)
  backend-dev.md           Opus   · Python fără Allplan: import/export, convertoare
  tester.md                Sonnet · scrie și rulează teste
  code-reviewer.md         Sonnet · doar citire · review
  security-reviewer.md     Sonnet · doar citire · securitate
  docs-writer.md           Haiku · documentație
  devops.md                Sonnet · CI, împachetare pentru Allplan
  git-manager.md           Haiku · commit, backup GitHub
.claude/skills/            cunoștințe comune
  project-conventions/     structură NewAll, denumiri, stil
  allplan-api/             cum se folosesc exemplele ALLPLAN ca documentație (nou)
  architecture-docs/       șabloane de plan și ADR
  git-workflow/            branch-uri, commit-uri, PR
  definition-of-done/      când e o sarcină gata
  testing-guide/           cum se testează (unittest, mock pentru Allplan)
  review-checklist/        checklist de review
  security-checklist/      checklist de securitate
  docs-format/             format documentație
  deploy-guide/            instalarea în Allplan
  github-backup/           reguli de backup și verificare de secrete
  engineering-calcs/       surse validate, unități, cazuri de referință
```

## Permisiuni și autonomie
- `.claude/settings.json` pornește în modul `acceptEdits`: editările de fișiere nu mai cer confirmare.
- Testele, lint-ul, verificarea de sintaxă, git local și căutarea web rulează fără întrebări.
- Push pe branch-uri de lucru (`claude/`, `feat/`, `fix/`, `docs/`, `chore/`) rulează fără întrebări.
- Cer confirmare: push pe `main`, merge de PR, instalarea de pachete, `docker`.
- Interzise: citirea `.env` și a secretelor, `git push --force`, `git reset --hard`, `rm -rf`, `sudo`.
- Pentru și mai puține confirmări: modul `auto` în `~/.claude/settings.json` (nu funcționează din setările proiectului).

## Ce mai ai de completat
- **Valorile din normă:** fișierele din `.claude/skills/engineering-calcs/references/` sunt precompletate cu valorile folosite acum în cod, toate cu status `NEVALIDAT`. Verifică-le cu SR EN 1992-1-1, Anexa Națională și P100-1/2013, corectează-le și treci statusul pe `VALIDAT` cu data.
- **Cazuri de referință:** adaugă calcule manuale sau din alt program validat în `NewAll/reference_cases/` (vezi `NewAll/reference_cases/README.md`).

## Istoric adaptări
- 2026-11-06: pachet instalat și adaptat proiectului:
  - `frontend-dev` → `allplan-dev` (proiectul nu are UI web; „interfața” sunt paletele `.pyp` și modelul Allplan);
  - skill nou `allplan-api`;
  - comenzi de test/lint/verificare completate; deploy = copiere în `Usr\Local`;
  - fluxul git adaptat sesiunilor cloud (branch `claude/...` desemnat; PR doar la cerere);
  - referințele `engineering-calcs` precompletate cu valorile din cod, marcate `NEVALIDAT`.
- 2026-11-12: regulile de blocare din `settings.json` pentru exemplele ALLPLAN ancorate la rădăcina proiectului
  (`/PythonPartsExampleScripts/**`); varianta cu `./` se raporta la folderul curent și bloca scrierea în `NewAll/`.
