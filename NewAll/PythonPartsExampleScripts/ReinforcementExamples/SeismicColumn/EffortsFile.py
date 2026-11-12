"""Citirea eforturilor de calcul dintr-un fișier CSV

Formatul fișierului (separator ";" sau ",", prima linie = antet, liniile care încep
cu "#" sunt comentarii; cu separatorul ";" se acceptă și virgula zecimală):

    Stalp;Combinatie;Tip;N;Mx_sus;My_sus;Mx_jos;My_jos;Vx;Vy
    S1;GF1;FUND;2450;35;20;-60;-25;30;45
    S1;GS1;SEISM;1650;180;60;-260;-80;95;140

Unități: kN și kNm. N > 0 compresiune. Tip = FUND (grupare fundamentală) sau
SEISM (grupare seismică). Coloana Stalp este opțională: dacă există, se pot filtra
rândurile unui singur stâlp.
"""

from __future__ import annotations

import csv
import io
import os

from .ColumnDesign import EffortCase

COLUMN_ALIASES = {
    "column": ("stalp", "stâlp", "element", "column", "id"),
    "name"  : ("combinatie", "combinație", "comb", "combination", "name"),
    "kind"  : ("tip", "grupare", "type", "kind"),
    "n"     : ("n", "ned", "n_ed"),
    "mx_top": ("mx_sus", "mx_top", "mxsus"),
    "my_top": ("my_sus", "my_top", "mysus"),
    "mx_bot": ("mx_jos", "mx_bot", "mx_bottom", "mxjos"),
    "my_bot": ("my_jos", "my_bot", "my_bottom", "myjos"),
    "vx"    : ("vx", "vx_ed"),
    "vy"    : ("vy", "vy_ed"),
}

NUMERIC_FIELDS = ("n", "mx_top", "my_top", "mx_bot", "my_bot", "vx", "vy")

MAX_FILE_BYTES = 20_000_000     # 20 MB
MAX_ROWS       = 200_000


class EffortsFileError(Exception):
    """Eroare de format în fișierul de eforturi"""


def parse_efforts(text: str, column_id: str = "") -> list[EffortCase]:
    """Interpretează conținutul unui fișier de eforturi

    Args:
        text:       conținutul fișierului
        column_id:  dacă nu este gol, se păstrează doar rândurile acestui stâlp

    Returns:
        lista combinațiilor de eforturi

    Raises:
        EffortsFileError: dacă formatul este greșit
    """
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]

    if not lines:
        raise EffortsFileError("Fișierul de eforturi este gol")

    if len(lines) > MAX_ROWS:
        raise EffortsFileError(f"Fișierul de eforturi are prea multe rânduri ({len(lines)}); maximum {MAX_ROWS}")

    delimiter     = ";" if lines[0].count(";") >= lines[0].count(",") else ","
    decimal_comma = delimiter == ";"

    reader = csv.reader(io.StringIO("\n".join(lines)), delimiter = delimiter)
    header = [cell.strip().lower() for cell in next(reader)]

    index: dict[str, int] = {}

    for key, aliases in COLUMN_ALIASES.items():
        for i, cell in enumerate(header):
            if cell in aliases:
                index[key] = i
                break

    if "n" not in index:
        raise EffortsFileError("Antetul trebuie să conțină cel puțin coloana N")

    cases: list[EffortCase] = []

    for row_nr, row in enumerate(reader, start = 2):
        if not any(cell.strip() for cell in row):
            continue

        def cell(key: str, default: str = "") -> str:
            pos = index.get(key)
            return row[pos].strip() if pos is not None and pos < len(row) else default

        if column_id and "column" in index and cell("column").lower() != column_id.strip().lower():
            continue

        values: dict[str, float] = {}

        for key in NUMERIC_FIELDS:
            raw = cell(key, "0") or "0"

            if decimal_comma:
                raw = raw.replace(",", ".")
            try:
                values[key] = float(raw)
            except ValueError as err:
                raise EffortsFileError(f"Rândul {row_nr}: valoare numerică invalidă '{raw}' "
                                       f"în coloana {key}") from err

        kind = cell("kind", "FUND").upper() or "FUND"

        if not (kind.startswith("FUND") or kind.startswith("SEIS")):
            raise EffortsFileError(f"Rândul {row_nr}: tipul grupării trebuie să fie FUND sau SEISM, nu '{kind}'")

        cases.append(EffortCase(name = cell("name") or f"C{len(cases) + 1}", kind = kind, **values))

    if not cases:
        raise EffortsFileError("Nu există combinații de eforturi" +
                               (f" pentru stâlpul '{column_id}'" if column_id else ""))

    return cases


def read_efforts_file(path: str, column_id: str = "") -> list[EffortCase]:
    """Citește fișierul de eforturi (UTF-8, cu sau fără BOM; altfel cp1250)

    Args:
        path:       calea fișierului
        column_id:  filtrul pentru stâlp (opțional)

    Returns:
        lista combinațiilor de eforturi

    Raises:
        EffortsFileError: fișier prea mare sau format greșit
        OSError:          fișierul nu poate fi citit
    """
    if os.path.getsize(path) > MAX_FILE_BYTES:
        raise EffortsFileError(f"Fișierul de eforturi este prea mare (peste {MAX_FILE_BYTES // 1_000_000} MB)")

    try:
        with open(path, encoding = "utf-8-sig") as file:
            text = file.read()
    except UnicodeDecodeError:
        with open(path, encoding = "cp1250") as file:
            text = file.read()

    return parse_efforts(text, column_id)
