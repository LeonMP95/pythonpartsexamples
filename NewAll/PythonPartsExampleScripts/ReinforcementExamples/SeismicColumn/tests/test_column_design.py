"""Teste pentru modulul de calcul (rulează fără Allplan)

    cd NewAll/PythonPartsExampleScripts
    python -m unittest discover -s ReinforcementExamples/SeismicColumn/tests -t .
"""

import math
import os
import unittest

from ReinforcementExamples.SeismicColumn.ColumnDesign import (P100_DCH, P100_DCM, BarLayout, ColumnGeometry,
                                                              DesignOptions, EffortCase, Materials,
                                                              RectSection, biaxial_exponent, design_column)
from ReinforcementExamples.SeismicColumn.EffortsFile import (EffortsFileError, parse_efforts,
                                                             read_efforts_file)

EXAMPLE_FILE = os.path.join(os.path.dirname(__file__), "..", "EforturiStalpi_Exemplu.csv")


class MaterialsTest(unittest.TestCase):
    """materiale"""

    def test_design_strengths(self):
        mat = Materials(30.0)
        self.assertAlmostEqual(mat.fcd, 20.0)
        self.assertAlmostEqual(mat.fyd, 434.78, places = 2)
        self.assertAlmostEqual(mat.eps_cu3, 0.0035)
        self.assertAlmostEqual(mat.lam, 0.8)


class SectionTest(unittest.TestCase):
    """analiza secțiunii"""

    def setUp(self):
        self.geom = ColumnGeometry(400.0, 400.0, 3000.0, 30.0)
        self.mat  = Materials(30.0)

    def test_pure_bending_matches_hand_calculation(self):
        # două rânduri de bare, câte 3Ø20 sus și jos, armare simetrică
        area = math.pi * 20 ** 2 / 4
        bars = [(x, y, area) for y in (50.0, 350.0) for x in (50.0, 200.0, 350.0)]
        section = RectSection(self.geom, self.mat, bars)

        m_rd = section.m_rd(0.0, "x")

        # calcul manual: armătura întinsă curge, x ≈ 56 mm, z ≈ d - λx/2 = 350 - 22.4 ≈ 327 mm
        # MRd ≈ As·fyd·z ≈ 942 · 434.8 · 327 ≈ 134 kNm
        a_s = 3 * area
        self.assertGreater(m_rd, 0.97 * a_s * self.mat.fyd * 327.0)
        self.assertLess(m_rd, 1.03 * a_s * self.mat.fyd * 327.0)

    def test_moment_decreases_beyond_balance_point(self):
        area = math.pi * 20 ** 2 / 4
        bars = [(x, y, area) for y in (50.0, 350.0) for x in (50.0, 200.0, 350.0)]
        section = RectSection(self.geom, self.mat, bars)

        self.assertGreater(section.m_rd(1000e3, "x"), section.m_rd(0.0, "x"))
        self.assertGreater(section.m_rd(1000e3, "x"), section.m_rd(3000e3, "x"))
        self.assertEqual(section.m_rd(section.n_rd_max * 1.01, "x"), 0.0)

    def test_biaxial_exponent(self):
        self.assertEqual(biaxial_exponent(0.05), 1.0)
        self.assertAlmostEqual(biaxial_exponent(0.7), 1.5)
        self.assertEqual(biaxial_exponent(1.2), 2.0)


class RulesTest(unittest.TestCase):
    """reguli P100"""

    def test_critical_length_dch(self):
        self.assertAlmostEqual(P100_DCH.critical_length(500.0, 3000.0), 750.0)
        self.assertAlmostEqual(P100_DCH.critical_length(600.0, 1500.0), 1500.0)   # lcl/hc < 3

    def test_critical_spacing(self):
        self.assertAlmostEqual(P100_DCH.critical_stirrup_spacing(420.0, 20.0), 120.0)
        self.assertAlmostEqual(P100_DCM.critical_stirrup_spacing(420.0, 20.0), 160.0)

    def test_layout_positions(self):
        layout = BarLayout(20.0, 4, 3)
        geom   = ColumnGeometry(500.0, 400.0, 3000.0, 30.0)
        pnts   = layout.positions(geom, 10.0)
        self.assertEqual(len(pnts), layout.count)
        self.assertEqual(layout.count, 10)
        self.assertIn((50.0, 50.0), pnts)
        self.assertIn((450.0, 350.0), pnts)


class EffortsFileTest(unittest.TestCase):
    """fișierul de eforturi"""

    def test_example_file(self):
        cases = read_efforts_file(EXAMPLE_FILE, "S1")
        self.assertEqual(len(cases), 6)
        self.assertTrue(cases[2].is_seismic)
        self.assertAlmostEqual(cases[0].n, 2450.0)
        self.assertAlmostEqual(cases[2].my_bot, -290.0)

    def test_comma_separator_without_column(self):
        cases = parse_efforts("N,Mx_sus,Mx_jos,Tip\n1000,50,-50,FUND\n")
        self.assertEqual(len(cases), 1)
        self.assertAlmostEqual(cases[0].mx_top, 50.0)

    def test_decimal_comma(self):
        cases = parse_efforts("N;Mx_sus\n1000,5;12,25\n")
        self.assertAlmostEqual(cases[0].n, 1000.5)

    def test_errors(self):
        with self.assertRaises(EffortsFileError):
            parse_efforts("Mx;My\n1;2\n")
        with self.assertRaises(EffortsFileError):
            parse_efforts("N;Tip\n100;VANT\n")
        with self.assertRaises(EffortsFileError):
            read_efforts_file(EXAMPLE_FILE, "S99")


class DesignTest(unittest.TestCase):
    """dimensionarea completă"""

    def test_example_column_dch(self):
        geom   = ColumnGeometry(600.0, 600.0, 3000.0, 30.0)
        result = design_column(geom, Materials(30.0), read_efforts_file(EXAMPLE_FILE, "S1"),
                               DesignOptions("DCH", True))

        self.assertTrue(result.ok, result.report_text())
        rho = result.layout.area / geom.area
        self.assertGreaterEqual(rho, P100_DCH.rho_min)
        self.assertLessEqual(result.transverse.spacing_critical, 125.0)
        self.assertGreaterEqual(result.transverse.omega_wd, P100_DCH.omega_wd_base)
        self.assertGreaterEqual(result.transverse.spacing_current, result.transverse.spacing_critical)

    def test_axial_force_limit(self):
        geom  = ColumnGeometry(400.0, 400.0, 3000.0, 30.0)
        cases = [EffortCase("GS", "SEISM", 2000.0)]      # νd = 0.625
        result = design_column(geom, Materials(30.0), cases, DesignOptions("DCH"))
        self.assertFalse(result.ok)
        self.assertIn("νd", result.report_text())

    def test_more_load_needs_more_steel(self):
        geom  = ColumnGeometry(500.0, 500.0, 3000.0, 30.0)
        small = design_column(geom, Materials(30.0), [EffortCase("G", "SEISM", 1000.0, 100.0, 50.0, -100.0, -50.0)],
                              DesignOptions("DCM"))
        large = design_column(geom, Materials(30.0), [EffortCase("G", "SEISM", 1000.0, 400.0, 200.0, -400.0, -200.0)],
                              DesignOptions("DCM"))
        self.assertTrue(small.ok and large.ok, large.report_text())
        self.assertGreater(large.layout.area, small.layout.area)


if __name__ == "__main__":
    unittest.main()
