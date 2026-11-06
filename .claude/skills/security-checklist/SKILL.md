---
name: security-checklist
description: Checklist de securitate pentru cod cu input extern, autentificare, date sensibile, fișiere sau dependențe noi.
---

# Checklist de securitate

## Input
- Tot inputul extern (utilizator, fișiere, rețea) este validat?
- Interogările către baza de date sunt parametrizate?
- Căile de fișiere sunt verificate (fără `../` scăpat de sub control)?
- Fișierele importate (CSV de eforturi, exporturi ETABS/SAP2000/Robot, DXF, IFC, JSON) au limite de mărime și sunt parsate în siguranță (fără `eval`, `exec`, `pickle`)?

## Secrete și date
- Nicio parolă, cheie sau token în cod sau în log-uri
- Datele personale sunt minime și protejate
- Datele proiectelor clienților nu ajung în repo
- Mesajele de eroare nu expun detalii interne

## Autentificare și acces
- Fiecare acțiune verifică drepturile utilizatorului
- Parolele sunt stocate doar ca hash (bcrypt/argon2)

## Dependențe
- Sursă de încredere, întreținută activ
- Fără vulnerabilități cunoscute (de ex. `pip-audit`)
- Versiuni fixate
- Disponibile în interpretorul Python din Allplan

Severitate: CRITIC · MARE · MEDIU · MIC
