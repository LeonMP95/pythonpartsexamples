"""Regulile de recunoaștere: ce layer conține ce tip de element și toleranțele geometrice

Regulile se citesc dintr-un fișier JSON (vezi data/RulesDefault.json). Modulul nu depinde de Allplan.
"""

from __future__ import annotations

import fnmatch
import json

from dataclasses import dataclass

ELEMENT_TYPES = ("column", "wall", "beam", "slab")


class RulesError(ValueError):
    """Fișier de reguli invalid"""


@dataclass(frozen=True)
class LayerRule:
    """Asociază un model de nume de layer (fnmatch, fără diferență între litere mari/mici) cu un tip de element"""

    pattern: str
    element: str

    def matches(self, layer: str) -> bool:
        """True dacă layerul se potrivește cu modelul"""
        return fnmatch.fnmatchcase(layer.upper(), self.pattern.upper())


@dataclass(frozen=True)
class RecognitionRules:
    """Reguli și toleranțe (toate lungimile în mm, unghiurile în grade)"""

    layers                : tuple[LayerRule, ...]
    column_min_size       : float = 150.0     # latura minimă a unui stâlp
    column_max_size       : float = 2000.0    # latura maximă a unui stâlp
    wall_min_thickness    : float = 100.0     # distanța minimă între fețele unui perete
    wall_max_thickness    : float = 800.0     # distanța maximă între fețele unui perete
    wall_min_length       : float = 300.0     # lungimea minimă a unui perete
    parallel_tolerance_deg: float = 1.0       # abaterea unghiulară admisă între fețele unui perete
    point_tolerance       : float = 5.0       # distanța sub care două puncte sunt considerate identice
    beam_width            : float = 300.0     # lățimea grinzilor desenate doar prin axă
    beam_depth            : float = 500.0     # înălțimea grinzilor (nu apare în planșele de arhitectură)
    slab_thickness        : float = 150.0     # grosimea plăcilor

    def element_for_layer(self, layer: str) -> str | None:
        """Tipul de element pentru un layer (prima regulă care se potrivește) sau None"""
        for rule in self.layers:
            if rule.matches(layer):
                return rule.element
        return None

    def layers_for(self, element: str, all_layers: set[str]) -> set[str]:
        """Layerele dintr-o mulțime care conțin tipul de element dat"""
        return {layer for layer in all_layers if self.element_for_layer(layer) == element}


_NUMERIC_FIELDS = ("column_min_size", "column_max_size", "wall_min_thickness", "wall_max_thickness",
                   "wall_min_length", "parallel_tolerance_deg", "point_tolerance", "beam_width",
                   "beam_depth", "slab_thickness")


def rules_from_dict(data: dict) -> RecognitionRules:
    """Construiește regulile dintr-un dicționar (conținutul fișierului JSON)

    Raises:
        RulesError: dacă datele sunt invalide
    """
    if not isinstance(data, dict):
        raise RulesError("Fișierul de reguli trebuie să conțină un obiect JSON")

    raw_layers = data.get("layers")

    if not isinstance(raw_layers, list) or not raw_layers:
        raise RulesError("Cheia 'layers' trebuie să fie o listă nevidă de reguli {\"pattern\": ..., \"element\": ...}")

    layers = []

    for nr, item in enumerate(raw_layers, start = 1):
        if not isinstance(item, dict) or not isinstance(item.get("pattern"), str) or not item["pattern"].strip():
            raise RulesError(f"Regula de layer nr. {nr}: lipsește 'pattern' (text)")

        if item.get("element") not in ELEMENT_TYPES:
            raise RulesError(f"Regula de layer nr. {nr}: 'element' trebuie să fie unul dintre {', '.join(ELEMENT_TYPES)}")

        layers.append(LayerRule(item["pattern"].strip(), item["element"]))

    values = {}

    for key in _NUMERIC_FIELDS:
        if key in data:
            value = data[key]

            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise RulesError(f"'{key}' trebuie să fie un număr pozitiv")

            values[key] = float(value)

    unknown = set(data) - set(_NUMERIC_FIELDS) - {"layers", "description"}

    if unknown:
        raise RulesError(f"Chei necunoscute în fișierul de reguli: {', '.join(sorted(unknown))}")

    rules = RecognitionRules(tuple(layers), **values)

    if rules.column_min_size >= rules.column_max_size:
        raise RulesError("column_min_size trebuie să fie mai mic decât column_max_size")

    if rules.wall_min_thickness >= rules.wall_max_thickness:
        raise RulesError("wall_min_thickness trebuie să fie mai mic decât wall_max_thickness")

    return rules


def load_rules(path: str) -> RecognitionRules:
    """Citește regulile dintr-un fișier JSON (UTF-8)

    Raises:
        RulesError: dacă fișierul nu poate fi citit sau este invalid
    """
    try:
        with open(path, encoding = "utf-8-sig") as file:
            data = json.load(file)
    except OSError as err:
        raise RulesError(f"Fișierul de reguli nu poate fi citit: {err}") from err
    except json.JSONDecodeError as err:
        raise RulesError(f"Fișierul de reguli nu este JSON valid (linia {err.lineno}): {err.msg}") from err

    return rules_from_dict(data)
