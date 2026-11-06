---
name: github-backup
description: Reguli pentru backup pe GitHub - când se face push, verificarea de secrete, .gitignore și pull request-uri. Folosește-l înainte de orice push.
---

# Backup pe GitHub

## Când
- După fiecare sarcină terminată (după `definition-of-done`)
- La finalul unei sesiuni de lucru, chiar dacă sarcina nu e gata: commit `wip: <ce>` pe branch-ul de lucru
- Înainte de orice schimbare mare sau riscantă
- În sesiunile cloud, containerul e temporar: tot ce nu e trimis pe GitHub se pierde.

## Verificare de secrete înainte de push
1. `git diff --cached --name-only`: niciun fișier `.env`, `*.pem`, `*.key`, `secrets/`, `credentials*`
2. Caută în schimbări: `password`, `secret`, `token`, `api_key`, `BEGIN PRIVATE KEY`
3. Fișiere mari (peste ~10 MB, de ex. modele IFC/DWG/NDW de test): nu intră în repo; folosește Git LFS sau le exclude
4. Fișierele de eforturi ale proiectelor reale ale clienților nu intră în repo; doar exemple.
Orice suspiciune → oprire și raport, fără push.

## .gitignore
Repo-ul are deja `.gitignore` (inclusiv `__pycache__/`). Se adaugă la nevoie: `.env`, `.env.*`, `secrets/`, `*.pem`, `*.key`, `*.log`.

## Push
- Doar pe branch-ul de lucru (`claude/...` în cloud; `feat/`, `fix/`, `docs/`, `chore/` local)
- Prima dată: `git push -u origin <branch>`; la erori de rețea, reîncercare de până la 4 ori (2 s, 4 s, 8 s, 16 s)
- `main` se actualizează doar prin pull request aprobat

## Pull request
Doar la cererea utilizatorului. În sesiunile cloud, cu instrumentele GitHub MCP (`gh` nu e disponibil); local, cu
`gh pr create --title "<tip>: <ce>" --body "<ce, de ce, cum s-a testat>"`.
