"""Teste pentru citirea regulilor de recunoaștere"""

import json
import os
import tempfile
import unittest

from StructuralModeling.FromDrawing.RecognitionRules import (MAX_LAYER_RULES, RulesError, load_rules,
                                                             rules_from_dict)

DEFAULT_RULES = os.path.join(os.path.dirname(__file__), "..", "data", "RulesDefault.json")


class RulesTest(unittest.TestCase):
    """reguli"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, content: bytes) -> str:
        path = os.path.join(self.tmp.name, "reguli.json")
        with open(path, "wb") as file:
            file.write(content)
        return path

    def test_default_rules_match_romanian_layers(self):
        rules = load_rules(DEFAULT_RULES)
        self.assertEqual(rules.element_for_layer("A-STALPI"), "column")
        self.assertEqual(rules.element_for_layer("S-GRINZI"), "beam")
        self.assertEqual(rules.element_for_layer("A-PERETI-BA"), "wall")
        self.assertEqual(rules.element_for_layer("S-PLACA"), "slab")
        self.assertIsNone(rules.element_for_layer("A-MOBILIER"))

    def test_invalid_json_gives_rules_error(self):
        with self.assertRaises(RulesError):
            load_rules(self._write(b"{nu e json"))

    def test_non_utf8_gives_rules_error(self):
        with self.assertRaises(RulesError):
            load_rules(self._write('{"layers": [{"pattern": "Ș", "element": "wall"}]}'.encode("utf-16")))

    def test_deep_json_gives_rules_error(self):
        with self.assertRaises(RulesError):
            load_rules(self._write(b"[" * 100000 + b"]" * 100000))

    def test_too_large_file_gives_rules_error(self):
        with self.assertRaises(RulesError):
            load_rules(self._write(b" " * 1_000_001 + b"{}"))

    def test_missing_file_gives_rules_error(self):
        with self.assertRaises(RulesError):
            load_rules(os.path.join(self.tmp.name, "lipsa.json"))

    def test_validation(self):
        layer = [{"pattern": "*", "element": "wall"}]
        with self.assertRaises(RulesError):
            rules_from_dict({"layers": [{"pattern": "*", "element": "acoperis"}]})
        with self.assertRaises(RulesError):
            rules_from_dict({"layers": layer, "beam_depth": -1})
        with self.assertRaises(RulesError):
            rules_from_dict({"layers": layer, "cheie_gresita": 1})
        with self.assertRaises(RulesError):
            rules_from_dict({"layers": layer, "wall_min_thickness": 900})
        with self.assertRaises(RulesError):
            rules_from_dict({"layers": layer * (MAX_LAYER_RULES + 1)})
        self.assertEqual(rules_from_dict(json.loads('{"layers": [{"pattern": "x", "element": "slab"}]}'))
                         .element_for_layer("X"), "slab")


if __name__ == "__main__":
    unittest.main()
