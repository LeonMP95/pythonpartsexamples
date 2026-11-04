# NewAll

Fișierele noi adăugate în acest repo: prototipul **Stâlp armat EC2 + P100-1**
(vezi `PythonPartsExampleScripts/ReinforcementExamples/SeismicColumn/README.md`).

Structura de directoare este aceeași ca a exemplelor PythonParts, ca importurile
și calea scriptului din fișierul `.pyp` să funcționeze fără modificări.

## Instalare în Allplan

Copiați conținutul acestui director (`Library` și `PythonPartsExampleScripts`)
**direct** în directorul USR al Allplan, de exemplu:

    C:\Users\<utilizator>\Documents\Nemetschek\Allplan\<versiune>\Usr\Local

PythonPart-ul apare apoi în
**Library → Private → Examples → PythonParts → ReinforcementExamples → SeismicColumn**.

## Teste

    cd NewAll/PythonPartsExampleScripts
    python -m unittest discover -s ReinforcementExamples/SeismicColumn/tests -t .
