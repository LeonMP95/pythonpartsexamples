---
name: git-workflow
description: Fluxul git al proiectului - branch-uri, mesaje de commit, pull request-uri. Folosește-l înainte de orice commit sau PR.
---

# Flux git

## Branch-uri
- `main` este mereu funcțional. Nu se lucrează direct pe el.
- În sesiunile Claude Code din cloud, branch-ul de lucru este cel desemnat de sesiune (`claude/<nume>`). Se lucrează și se face push doar pe el.
- În sesiuni locale: branch nou per sarcină: `feat/<scurt>`, `fix/<scurt>`, `docs/<scurt>`, `chore/<scurt>`.

## Commit-uri
Format: `<tip>: <ce s-a schimbat>` (imperativ, sub 72 de caractere)
- Tipuri: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
- Un commit = o schimbare logică. Testele trec la fiecare commit.
- Mesajul se încheie cu liniile de atribuire cerute de sesiune (dacă există).

## Pull request
- Se deschide doar când utilizatorul îl cere.
- Titlu ca un commit.
- Descriere: ce, de ce, cum s-a testat, ce trebuie verificat în Allplan.
- Se face merge doar după review aprobat și teste trecute, și doar de utilizator.

## Interzis
- `git push --force` pe `main`
- Secrete (parole, chei) în commit-uri
- Modificări în `PythonPartsExampleScripts/` și `Library/` din rădăcină
