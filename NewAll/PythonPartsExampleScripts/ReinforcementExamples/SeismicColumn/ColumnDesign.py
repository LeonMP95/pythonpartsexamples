"""Dimensionarea și alcătuirea armăturii stâlpilor dreptunghiulari din beton armat

Reguli implementate (prototip, vezi README.md pentru limitări):

SR EN 1992-1-1 (EC2)
    -   3.1.6 / 3.2.7  rezistențe de calcul, γc = 1.5, γs = 1.15, αcc = 1.0
    -   3.1.7          bloc dreptunghiular de compresiuni (λ, η, εcu3)
    -   5.2(9)         imperfecțiuni geometrice ei = l0/400
    -   5.8.3.1        zveltețea limită λlim
    -   5.8.8          metoda curburii nominale (Kφ = 1)
    -   5.8.9          încovoiere oblică (exponentul a)
    -   6.1(4)         excentricitatea minimă e0 = max(h/30, 20 mm)
    -   6.2.3          forța tăietoare, VRd,s și VRd,max
    -   8.2, 8.4, 8.7  distanțe între bare, ancoraj, suprapuneri
    -   9.5.2, 9.5.3   armare longitudinală minimă / maximă, etrieri

P100-1/2013 (stâlpi, DCH / DCM)
    -   forța axială normalizată νd
    -   procente minime / maxime de armare longitudinală
    -   distanța maximă între barele longitudinale legate (agrafe)
    -   lungimea zonelor critice lcr
    -   distanța maximă între etrieri în zonele critice
    -   coeficientul mecanic de armare transversală ωwd (confinare)
    -   forța tăietoare din calculul la capacitate:
        VEd = γRd (MRd,sus + MRd,jos) · min(1, ΣMRb/ΣMRc) / lcl

Valorile numerice ale normativului sunt grupate în SeismicRules (P100_DCH, P100_DCM)
ca să poată fi verificate și corectate ușor. Unități interne: mm, N, MPa.
"""

from __future__ import annotations

import math

from dataclasses import dataclass, field

CONCRETE_CLASSES: dict[str, float] = {
    "C16/20": 16.0,
    "C20/25": 20.0,
    "C25/30": 25.0,
    "C30/37": 30.0,
    "C35/45": 35.0,
    "C40/50": 40.0,
    "C45/55": 45.0,
    "C50/60": 50.0,
}

BAR_DIAMETERS     = (14.0, 16.0, 18.0, 20.0, 22.0, 25.0, 28.0, 32.0)
STIRRUP_DIAMETERS = (8.0, 10.0, 12.0, 14.0)

SPACING_STEP     = 25.0     # pasul de rotunjire a distanței dintre etrieri
MIN_STIRRUP_STEP = 50.0     # distanța minimă practică între etrieri
FIRST_STIRRUP    = 50.0     # distanța de la fața elementului de capăt la primul etrier


# ----------------------------------------------------------------------------------------------
# Materiale
# ----------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Materials:
    """Proprietățile de calcul ale betonului și oțelului (EC2 cap. 3)"""

    fck     : float
    fyk     : float = 500.0
    gamma_c : float = 1.5
    gamma_s : float = 1.15
    alpha_cc: float = 1.0
    es      : float = 200000.0

    @property
    def fcd(self) -> float:
        """rezistența de calcul la compresiune a betonului"""
        return self.alpha_cc * self.fck / self.gamma_c

    @property
    def fyd(self) -> float:
        """rezistența de calcul a armăturii"""
        return self.fyk / self.gamma_s

    @property
    def eps_yd(self) -> float:
        """deformația specifică de curgere"""
        return self.fyd / self.es

    @property
    def eps_cu3(self) -> float:
        """deformația specifică ultimă a betonului (bloc dreptunghiular)"""
        if self.fck <= 50:
            return 0.0035
        return (2.6 + 35.0 * ((90.0 - self.fck) / 100.0) ** 4) / 1000.0

    @property
    def eps_c3(self) -> float:
        """deformația specifică la compresiune centrică"""
        if self.fck <= 50:
            return 0.00175
        return (1.75 + 0.55 * (self.fck - 50.0) / 40.0) / 1000.0

    @property
    def lam(self) -> float:
        """factorul λ al înălțimii blocului de compresiuni"""
        return 0.8 if self.fck <= 50 else 0.8 - (self.fck - 50.0) / 400.0

    @property
    def eta(self) -> float:
        """factorul η al rezistenței efective"""
        return 1.0 if self.fck <= 50 else 1.0 - (self.fck - 50.0) / 200.0

    @property
    def fctd(self) -> float:
        """rezistența de calcul la întindere, αct = 1.0"""
        fctm = 0.30 * self.fck ** (2.0 / 3.0)
        return 0.7 * fctm / self.gamma_c

    @property
    def fbd(self) -> float:
        """efortul unitar ultim de aderență, condiții bune (η1 = η2 = 1)"""
        return 2.25 * self.fctd


# ----------------------------------------------------------------------------------------------
# Reguli P100-1/2013
# ----------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class SeismicRules:
    """Valorile din P100-1/2013 pentru stâlpi, pentru o clasă de ductilitate.

    ATENȚIE: valorile trebuie verificate de proiectant cu textul în vigoare al normativului
    (inclusiv eventualele erate) înainte de utilizarea în proiecte reale.
    """

    name                 : str
    nu_max               : float    # forța axială normalizată maximă νd
    rho_min              : float    # procent minim de armare longitudinală totală
    rho_max              : float    # procent maxim de armare longitudinală totală
    max_bar_distance     : float    # distanța maximă între barele longitudinale legate [mm]
    min_long_diameter    : float    # diametrul minim al barelor longitudinale [mm]
    min_stirrup_diameter : float    # diametrul minim al etrierilor [mm]
    min_section_dim      : float    # dimensiunea minimă a secțiunii [mm]
    lcr_factor_h         : float    # lcr >= factor * hc
    lcr_min              : float    # lcr >= valoare [mm]
    s_cr_b0_divisor      : float    # s <= b0 / divizor
    s_cr_max             : float    # s <= valoare [mm]
    s_cr_dbl_factor      : float    # s <= factor * dbL
    omega_wd_base        : float    # ωwd minim în zona critică de la baza stâlpilor
    omega_wd_other       : float    # ωwd minim în celelalte zone critice
    gamma_rd             : float    # factorul de suprarezistență pentru calculul la capacitate
    cot_theta_seismic    : float    # cot θ folosit la forța tăietoare în gruparea seismică

    def critical_length(self, h_max: float, clear_height: float) -> float:
        """Lungimea zonei critice lcr la fiecare capăt al stâlpului

        Args:
            h_max:         dimensiunea maximă a secțiunii
            clear_height:  înălțimea liberă a stâlpului

        Returns:
            lcr; dacă lcl / hc < 3 întreaga înălțime este zonă critică
        """
        if clear_height / h_max < 3.0:
            return clear_height

        lcr = max(self.lcr_factor_h * h_max, clear_height / 6.0, self.lcr_min)

        return min(lcr, clear_height / 2.0)

    def critical_stirrup_spacing(self, b0_min: float, d_bl: float) -> float:
        """Distanța maximă între etrieri în zona critică

        Args:
            b0_min: latura minimă a miezului de beton confinat (axele etrierilor)
            d_bl:   diametrul minim al barelor longitudinale

        Returns:
            distanța maximă
        """
        return min(b0_min / self.s_cr_b0_divisor, self.s_cr_max, self.s_cr_dbl_factor * d_bl)


P100_DCH = SeismicRules(name                 = "DCH",
                        nu_max               = 0.40,
                        rho_min              = 0.010,
                        rho_max              = 0.040,
                        max_bar_distance     = 150.0,
                        min_long_diameter    = 14.0,
                        min_stirrup_diameter = 8.0,
                        min_section_dim      = 300.0,
                        lcr_factor_h         = 1.5,
                        lcr_min              = 600.0,
                        s_cr_b0_divisor      = 3.0,
                        s_cr_max             = 125.0,
                        s_cr_dbl_factor      = 6.0,
                        omega_wd_base        = 0.12,
                        omega_wd_other       = 0.08,
                        gamma_rd             = 1.3,
                        cot_theta_seismic    = 1.0)

P100_DCM = SeismicRules(name                 = "DCM",
                        nu_max               = 0.55,
                        rho_min              = 0.008,
                        rho_max              = 0.040,
                        max_bar_distance     = 200.0,
                        min_long_diameter    = 14.0,
                        min_stirrup_diameter = 8.0,
                        min_section_dim      = 250.0,
                        lcr_factor_h         = 1.0,
                        lcr_min              = 450.0,
                        s_cr_b0_divisor      = 2.0,
                        s_cr_max             = 175.0,
                        s_cr_dbl_factor      = 8.0,
                        omega_wd_base        = 0.08,
                        omega_wd_other       = 0.0,
                        gamma_rd             = 1.1,
                        cot_theta_seismic    = 1.0)

SEISMIC_RULES = {"DCH": P100_DCH, "DCM": P100_DCM}


# ----------------------------------------------------------------------------------------------
# Date de intrare
# ----------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class ColumnGeometry:
    """Geometria stâlpului.

    Sistemul local: X de-a lungul laturii b, Y de-a lungul laturii h, Z axa stâlpului.
    """

    b              : float          # latura pe direcția X [mm]
    h              : float          # latura pe direcția Y [mm]
    clear_height   : float          # înălțimea liberă lcl [mm]
    cover          : float          # stratul de acoperire nominal până la etrier [mm]
    buckling_factor: float = 1.0    # l0 = factor * lcl

    @property
    def area(self) -> float:
        """aria secțiunii de beton"""
        return self.b * self.h

    @property
    def l0(self) -> float:
        """lungimea de flambaj"""
        return self.buckling_factor * self.clear_height


@dataclass(frozen=True)
class EffortCase:
    """O combinație de eforturi la capetele stâlpului.

    Convenții: N > 0 compresiune [kN]; Mx rotește în jurul axei X (solicită latura h) [kNm];
    My rotește în jurul axei Y (solicită latura b) [kNm]; Vx, Vy forțe tăietoare [kN].
    kind = "FUND" (grupare fundamentală) sau "SEISM" (grupare seismică).
    """

    name  : str
    kind  : str
    n     : float
    mx_top: float = 0.0
    my_top: float = 0.0
    mx_bot: float = 0.0
    my_bot: float = 0.0
    vx    : float = 0.0
    vy    : float = 0.0

    @property
    def is_seismic(self) -> bool:
        """True pentru gruparea seismică"""
        return self.kind.upper().startswith("SEIS")


@dataclass(frozen=True)
class DesignOptions:
    """Opțiuni de proiectare"""

    ductility      : str = "DCH"
    is_base_column : bool = True    # stâlp la baza clădirii (zona critică de la bază)
    max_aggregate  : float = 16.0   # dimensiunea maximă a agregatului dg [mm]
    beam_column_ratio: float = 1.0  # ΣMRb / ΣMRc în nod pentru VEd de capacitate (1.0 = acoperitor)

    @property
    def rules(self) -> SeismicRules:
        """regulile P100 pentru clasa de ductilitate"""
        return SEISMIC_RULES[self.ductility.upper()]


# ----------------------------------------------------------------------------------------------
# Dispunerea armăturii
# ----------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class BarLayout:
    """Bare longitudinale identice, distribuite uniform pe contur.

    nx = numărul de bare pe latura b (inclusiv colțurile), ny = numărul de bare pe latura h.
    """

    diameter: float
    nx      : int
    ny      : int

    @property
    def count(self) -> int:
        """numărul total de bare"""
        return 2 * self.nx + 2 * self.ny - 4

    @property
    def bar_area(self) -> float:
        """aria unei bare"""
        return math.pi * self.diameter ** 2 / 4.0

    @property
    def area(self) -> float:
        """aria totală a armăturii longitudinale"""
        return self.count * self.bar_area

    def positions(self, geom: ColumnGeometry, stirrup_diameter: float) -> list[tuple[float, float]]:
        """Pozițiile axelor barelor, măsurate față de colțul (0, 0) al secțiunii

        Args:
            geom:             geometria stâlpului
            stirrup_diameter: diametrul etrierului

        Returns:
            lista de coordonate (x, y)
        """
        edge = geom.cover + stirrup_diameter + self.diameter / 2.0

        xs = _linspace(edge, geom.b - edge, self.nx)
        ys = _linspace(edge, geom.h - edge, self.ny)

        pnts = [(x, ys[0]) for x in xs] + [(x, ys[-1]) for x in xs]
        pnts += [(xs[0], y) for y in ys[1:-1]] + [(xs[-1], y) for y in ys[1:-1]]

        return pnts

    def x_coordinates(self, geom: ColumnGeometry, stirrup_diameter: float) -> list[float]:
        """coordonatele X ale barelor de pe laturile b"""
        edge = geom.cover + stirrup_diameter + self.diameter / 2.0
        return _linspace(edge, geom.b - edge, self.nx)

    def y_coordinates(self, geom: ColumnGeometry, stirrup_diameter: float) -> list[float]:
        """coordonatele Y ale barelor de pe laturile h"""
        edge = geom.cover + stirrup_diameter + self.diameter / 2.0
        return _linspace(edge, geom.h - edge, self.ny)

    def __str__(self) -> str:
        return f"{self.count}Ø{self.diameter:g} ({self.nx} bare pe b, {self.ny} bare pe h)"


def _linspace(start: float, end: float, count: int) -> list[float]:
    if count == 1:
        return [(start + end) / 2.0]
    step = (end - start) / (count - 1)
    return [start + i * step for i in range(count)]


# ----------------------------------------------------------------------------------------------
# Analiza secțiunii
# ----------------------------------------------------------------------------------------------

class RectSection:
    """Secțiune dreptunghiulară armată, analiză prin compatibilitatea deformațiilor"""

    def __init__(self,
                 geom: ColumnGeometry,
                 mat : Materials,
                 bars: list[tuple[float, float, float]]):
        """
        Args:
            geom: geometria
            mat:  materialele
            bars: lista (x, y, arie) pentru fiecare bară
        """
        self.geom = geom
        self.mat  = mat
        self.bars = bars

    @property
    def steel_area(self) -> float:
        """aria totală de armătură"""
        return sum(bar[2] for bar in self.bars)

    @property
    def n_rd_max(self) -> float:
        """capacitatea la compresiune centrică (EC2 5.8.9(4)) [N]"""
        return self.geom.area * self.mat.fcd + self.steel_area * self.mat.fyd

    def _axis_data(self, axis: str) -> tuple[float, float, list[tuple[float, float]]]:
        """(adâncimea D, lățimea, [(u, arie)]) pentru direcția de încovoiere

        axis = "x": moment Mx, solicită latura h (u = y)
        axis = "y": moment My, solicită latura b (u = x)
        """
        if axis == "x":
            return self.geom.h, self.geom.b, [(bar[1], bar[2]) for bar in self.bars]

        return self.geom.b, self.geom.h, [(bar[0], bar[2]) for bar in self.bars]

    def _strain(self, u: float, x: float, depth: float) -> float:
        mat = self.mat

        if x <= depth:
            return mat.eps_cu3 * (x - u) / x

        u_c = (1.0 - mat.eps_c3 / mat.eps_cu3) * depth

        return mat.eps_c3 * (x - u) / (x - u_c)

    def forces(self, x: float, axis: str) -> tuple[float, float]:
        """Rezultantele (N, M) pentru o poziție a axei neutre

        Args:
            x:    adâncimea axei neutre măsurată de la fibra cea mai comprimată
            axis: "x" sau "y"

        Returns:
            N [N] (compresiune pozitivă), M [Nmm] față de centrul de greutate
        """
        mat                 = self.mat
        depth, width, bars  = self._axis_data(axis)
        block               = min(mat.lam * x, depth)
        sigma_c             = mat.eta * mat.fcd

        n_tot = sigma_c * width * block
        m_tot = n_tot * (depth / 2.0 - block / 2.0)

        for u, area in bars:
            sigma_s = max(-mat.fyd, min(mat.fyd, mat.es * self._strain(u, x, depth)))

            if u < block:
                sigma_s -= sigma_c

            force  = sigma_s * area
            n_tot += force
            m_tot += force * (depth / 2.0 - u)

        return n_tot, m_tot

    def m_rd(self, n_ed: float, axis: str) -> float:
        """Momentul capabil pentru o forță axială dată

        Args:
            n_ed: forța axială [N], compresiune pozitivă
            axis: "x" sau "y"

        Returns:
            MRd [Nmm]; 0 dacă forța axială depășește capacitatea secțiunii
        """
        depth = self._axis_data(axis)[0]

        x_low, x_high = 1e-6 * depth, 1e4 * depth

        if n_ed <= self.forces(x_low, axis)[0] or n_ed >= self.forces(x_high, axis)[0]:
            return 0.0

        for _ in range(200):
            x_mid = 0.5 * (x_low + x_high)

            if self.forces(x_mid, axis)[0] < n_ed:
                x_low = x_mid
            else:
                x_high = x_mid

            if x_high - x_low < 1e-6 * depth:
                break

        return abs(self.forces(0.5 * (x_low + x_high), axis)[1])


def biaxial_exponent(n_ratio: float) -> float:
    """Exponentul a din EC2 5.8.9 (14), interpolare liniară"""
    if n_ratio <= 0.1:
        return 1.0
    if n_ratio <= 0.7:
        return 1.0 + (n_ratio - 0.1) / 0.6 * 0.5
    if n_ratio <= 1.0:
        return 1.5 + (n_ratio - 0.7) / 0.3 * 0.5
    return 2.0


# ----------------------------------------------------------------------------------------------
# Eforturi de calcul
# ----------------------------------------------------------------------------------------------

@dataclass
class AxisMoment:
    """Momentul de calcul pe o direcție și proveniența lui"""

    m_ed         : float    # [Nmm]
    slenderness  : float
    lambda_lim   : float
    second_order : float    # M2 [Nmm]


def design_moment(n_ed     : float,
                  m_top    : float,
                  m_bot    : float,
                  depth    : float,
                  geom     : ColumnGeometry,
                  mat      : Materials,
                  omega    : float,
                  d_eff    : float) -> AxisMoment:
    """Momentul de calcul pe o direcție, cu imperfecțiuni, e0 minim și efecte de ordinul 2

    Pentru stâlpii cadrelor necontravântuite se folosește acoperitor
    MEd = max(|M02| + N·ei + M2, N·e0), cu C = 0.7 în λlim și Kφ = 1.

    Args:
        n_ed:   forța axială [N]
        m_top:  momentul la capătul superior [Nmm]
        m_bot:  momentul la capătul inferior [Nmm]
        depth:  latura secțiunii pe direcția de încovoiere [mm]
        geom:   geometria
        mat:    materialele
        omega:  coeficientul mecanic de armare As·fyd / (Ac·fcd)
        d_eff:  înălțimea utilă pe direcția de încovoiere [mm]

    Returns:
        momentul de calcul
    """
    m02 = max(abs(m_top), abs(m_bot))

    if n_ed <= 0:
        return AxisMoment(m02, 0.0, 0.0, 0.0)

    l0       = geom.l0
    e_i      = l0 / 400.0
    e_0      = max(depth / 30.0, 20.0)
    n_rel    = n_ed / (geom.area * mat.fcd)
    radius   = depth / math.sqrt(12.0)
    slender  = l0 / radius
    lam_lim  = 20.0 * 0.7 * 1.1 * 0.7 / math.sqrt(n_rel)

    m_2 = 0.0

    if slender > lam_lim:
        n_u      = 1.0 + omega
        k_r      = min(1.0, max(0.0, (n_u - n_rel) / (n_u - 0.4)))
        curv     = k_r * mat.eps_yd / (0.45 * d_eff)
        m_2      = n_ed * curv * l0 ** 2 / 10.0

    m_ed = max(m02 + n_ed * e_i + m_2, n_ed * e_0)

    return AxisMoment(m_ed, slender, lam_lim, m_2)


# ----------------------------------------------------------------------------------------------
# Rezultatul dimensionării
# ----------------------------------------------------------------------------------------------

@dataclass
class TransverseDesign:
    """Armarea transversală"""

    diameter        : float
    spacing_critical: float
    spacing_current : float
    critical_length : float
    legs_x          : int       # ramuri paralele cu X (preiau Vx)
    legs_y          : int       # ramuri paralele cu Y (preiau Vy)
    omega_wd        : float
    governing       : str


@dataclass
class ColumnDesignResult:
    """Rezultatul complet al dimensionării"""

    ok           : bool
    layout       : BarLayout | None = None
    transverse   : TransverseDesign | None = None
    lap_length   : float = 0.0
    messages     : list[str] = field(default_factory = list)
    warnings     : list[str] = field(default_factory = list)

    def report_text(self) -> str:
        """Raportul de calcul ca text"""
        lines = ["RAPORT DIMENSIONARE STÂLP  (SR EN 1992-1-1 + P100-1/2013) - PROTOTIP", "=" * 72]
        lines += self.messages

        if self.warnings:
            lines += ["", "AVERTISMENTE:"] + [f"  - {msg}" for msg in self.warnings]

        lines += ["", "REZULTAT: " + ("ARMARE STABILITĂ" if self.ok else "DIMENSIONARE EȘUATĂ")]

        if self.ok and self.layout and self.transverse:
            trv = self.transverse
            lines += [f"  Armare longitudinală: {self.layout}",
                      f"  Etrieri + agrafe Ø{trv.diameter:g}: "
                      f"/{trv.spacing_critical:g} mm în zonele critice (lcr = {trv.critical_length:.0f} mm), "
                      f"/{trv.spacing_current:g} mm în zona curentă",
                      f"  Lungime de suprapunere (mustăți): {self.lap_length:.0f} mm"]

        lines.append("")
        lines.append("Rezultatul trebuie verificat de un inginer proiectant autorizat.")

        return "\n".join(lines)


# ----------------------------------------------------------------------------------------------
# Dimensionarea
# ----------------------------------------------------------------------------------------------

class ColumnDesigner:
    """Determină armarea longitudinală și transversală a unui stâlp"""

    def __init__(self,
                 geom   : ColumnGeometry,
                 mat    : Materials,
                 cases  : list[EffortCase],
                 options: DesignOptions):
        self.geom    = geom
        self.mat     = mat
        self.cases   = cases
        self.options = options
        self.rules   = options.rules

    # ------------------------------------------------------------------------------------------

    def design(self) -> ColumnDesignResult:
        """Execută dimensionarea

        Returns:
            rezultatul
        """
        result = ColumnDesignResult(ok = False)
        geom, mat, rules = self.geom, self.mat, self.rules

        result.messages += [
            f"Secțiune b x h = {geom.b:.0f} x {geom.h:.0f} mm, lcl = {geom.clear_height:.0f} mm, "
            f"l0 = {geom.l0:.0f} mm, acoperire = {geom.cover:.0f} mm",
            f"Beton fck = {mat.fck:g} MPa (fcd = {mat.fcd:.2f}), oțel fyk = {mat.fyk:g} MPa "
            f"(fyd = {mat.fyd:.1f}), clasa de ductilitate {rules.name}"
            + (", stâlp la bază" if self.options.is_base_column else ""),
            f"Combinații de eforturi: {len(self.cases)}"]

        if not self.cases:
            result.messages.append("Nu există combinații de eforturi.")
            return result

        if min(geom.b, geom.h) < rules.min_section_dim:
            result.warnings.append(f"Latura minimă {min(geom.b, geom.h):.0f} mm < "
                                   f"{rules.min_section_dim:.0f} mm cerută pentru {rules.name}")

        if not self._check_axial_force(result):
            return result

        for layout, stirrup_d in self._candidate_layouts():
            if not self._check_longitudinal(layout, stirrup_d, None):
                continue

            transverse = self._design_transverse(layout, stirrup_d)

            if transverse is None:
                continue

            if transverse.diameter != stirrup_d and \
               not self._check_longitudinal(layout, transverse.diameter, None):
                continue

            result.ok         = True
            result.layout     = layout
            result.transverse = transverse
            result.lap_length = self._lap_length(layout.diameter)

            result.messages.append("")
            self._check_longitudinal(layout, transverse.diameter, result.messages)
            self._report_transverse(transverse, result.messages)
            self._check_cover(layout, transverse, result)

            return result

        result.messages.append("Nu s-a găsit o armare longitudinală care să satisfacă toate verificările; "
                               "măriți secțiunea sau clasa betonului.")
        return result

    # ------------------------------------------------------------------------------------------

    def _check_axial_force(self, result: ColumnDesignResult) -> bool:
        ok = True

        for case in self.cases:
            if not case.is_seismic:
                continue

            nu_d = case.n * 1e3 / (self.geom.area * self.mat.fcd)

            if nu_d > self.rules.nu_max:
                result.messages.append(f"[{case.name}] νd = {nu_d:.3f} > {self.rules.nu_max:.2f} "
                                       f"(P100-1, {self.rules.name}) - secțiunea trebuie mărită")
                ok = False

        return ok

    def _candidate_layouts(self) -> list[tuple[BarLayout, float]]:
        """Toate dispunerile admisibile constructiv, ordonate după aria de armătură"""
        geom, rules = self.geom, self.rules
        candidates: list[tuple[BarLayout, float]] = []

        for diameter in BAR_DIAMETERS:
            if diameter < rules.min_long_diameter:
                continue

            stirrup_d = self._min_stirrup_diameter(diameter)
            edge      = geom.cover + stirrup_d + diameter / 2.0
            clear_min = max(diameter, self.options.max_aggregate + 5.0, 20.0)

            span_x, span_y = geom.b - 2 * edge, geom.h - 2 * edge

            if span_x <= 0 or span_y <= 0:
                continue

            nx_min = max(2, math.ceil(span_x / rules.max_bar_distance - 1e-9) + 1)
            ny_min = max(2, math.ceil(span_y / rules.max_bar_distance - 1e-9) + 1)
            nx_max = math.floor(span_x / (diameter + clear_min)) + 1
            ny_max = math.floor(span_y / (diameter + clear_min)) + 1

            for n_x in range(nx_min, nx_max + 1):
                for n_y in range(ny_min, ny_max + 1):
                    candidates.append((BarLayout(diameter, n_x, n_y), stirrup_d))

        def spacing_difference(item: tuple[BarLayout, float]) -> float:
            layout, stirrup_d = item
            edge = geom.cover + stirrup_d + layout.diameter / 2.0
            return abs((geom.b - 2 * edge) / (layout.nx - 1) - (geom.h - 2 * edge) / (layout.ny - 1))

        candidates.sort(key = lambda item: (round(item[0].area), item[0].count, spacing_difference(item)))

        return candidates

    def _min_stirrup_diameter(self, bar_diameter: float) -> float:
        required = max(self.rules.min_stirrup_diameter, 6.0, bar_diameter / 4.0, 0.4 * bar_diameter)

        for diameter in STIRRUP_DIAMETERS:
            if diameter >= required - 1e-9:
                return diameter

        return STIRRUP_DIAMETERS[-1]

    def _section(self, layout: BarLayout, stirrup_d: float) -> RectSection:
        bars = [(x, y, layout.bar_area) for x, y in layout.positions(self.geom, stirrup_d)]
        return RectSection(self.geom, self.mat, bars)

    def _effective_depth(self, layout: BarLayout, stirrup_d: float, depth: float) -> float:
        return depth - self.geom.cover - stirrup_d - layout.diameter / 2.0

    def _check_longitudinal(self,
                            layout   : BarLayout,
                            stirrup_d: float,
                            messages : list[str] | None) -> bool:
        """Verificările armăturii longitudinale; scrie detaliile în messages, dacă este dat"""
        geom, mat, rules = self.geom, self.mat, self.rules

        rho       = layout.area / geom.area
        n_max     = max(case.n for case in self.cases) * 1e3
        as_min    = max(0.10 * max(n_max, 0.0) / mat.fyd, 0.002 * geom.area)
        omega     = layout.area * mat.fyd / (geom.area * mat.fcd)
        section   = self._section(layout, stirrup_d)
        ok        = True

        def log(text: str):
            if messages is not None:
                messages.append(text)

        log(f"Armare longitudinală {layout}: As = {layout.area:.0f} mm², ρ = {rho * 100:.2f} %")

        if rho < rules.rho_min - 1e-12 or rho > rules.rho_max + 1e-12:
            log(f"  ρ în afara intervalului P100 [{rules.rho_min * 100:.1f} %, {rules.rho_max * 100:.1f} %]")
            ok = False

        if layout.area < as_min:
            log(f"  As < As,min = {as_min:.0f} mm² (EC2 9.5.2)")
            ok = False

        if not ok:
            return False

        log(f"  ρ ∈ [{rules.rho_min * 100:.1f} %, {rules.rho_max * 100:.1f} %] (P100-1), "
            f"As ≥ As,min = {as_min:.0f} mm² (EC2 9.5.2): OK")

        d_x = self._effective_depth(layout, stirrup_d, geom.h)
        d_y = self._effective_depth(layout, stirrup_d, geom.b)

        for case in self.cases:
            n_ed = case.n * 1e3

            m_x = design_moment(n_ed, case.mx_top * 1e6, case.mx_bot * 1e6, geom.h, geom, mat, omega, d_x)
            m_y = design_moment(n_ed, case.my_top * 1e6, case.my_bot * 1e6, geom.b, geom, mat, omega, d_y)

            mrd_x = section.m_rd(n_ed, "x")
            mrd_y = section.m_rd(n_ed, "y")

            if mrd_x <= 0 or mrd_y <= 0:
                log(f"  [{case.name}] N = {case.n:.0f} kN depășește capacitatea axială a secțiunii")
                return False

            exponent = biaxial_exponent(n_ed / section.n_rd_max)
            util     = (m_x.m_ed / mrd_x) ** exponent + (m_y.m_ed / mrd_y) ** exponent

            second = ""
            if m_x.second_order > 0 or m_y.second_order > 0:
                second = (f", M2 = {m_x.second_order / 1e6:.1f} / {m_y.second_order / 1e6:.1f} kNm "
                          f"(λ = {m_x.slenderness:.0f}/{m_y.slenderness:.0f})")

            log(f"  [{case.name}] N = {case.n:.0f} kN, MEdx = {m_x.m_ed / 1e6:.1f} kNm "
                f"(MRdx = {mrd_x / 1e6:.1f}), MEdy = {m_y.m_ed / 1e6:.1f} kNm (MRdy = {mrd_y / 1e6:.1f}), "
                f"a = {exponent:.2f}, utilizare = {util:.2f}{second}" + ("" if util <= 1.0 else "  NU"))

            if util > 1.0:
                ok = False
                if messages is None:
                    return False

        return ok

    # ------------------------------------------------------------------------------------------

    def _design_transverse(self, layout: BarLayout, min_stirrup_d: float) -> TransverseDesign | None:
        """Dimensionează etrierii și agrafele; fiecare bară longitudinală intermediară este legată de o agrafă"""
        geom, mat, rules = self.geom, self.mat, self.rules

        lcr    = rules.critical_length(max(geom.b, geom.h), geom.clear_height)
        legs_x = 2 + (layout.ny - 2)
        legs_y = 2 + (layout.nx - 2)

        omega_min = rules.omega_wd_base if self.options.is_base_column else rules.omega_wd_other

        for diameter in STIRRUP_DIAMETERS:
            if diameter < min_stirrup_d:
                continue

            section = self._section(layout, diameter)
            asw_one = math.pi * diameter ** 2 / 4.0

            s_shear = self._shear_spacing(layout, diameter, section, asw_one, legs_x, legs_y, lcr)

            if s_shear is None:
                return None

            b_0 = geom.b - 2 * geom.cover - diameter
            h_0 = geom.h - 2 * geom.cover - diameter

            s_detail = rules.critical_stirrup_spacing(min(b_0, h_0), layout.diameter)

            hoop_length = 2 * (b_0 + h_0) + (layout.nx - 2) * h_0 + (layout.ny - 2) * b_0
            s_conf = math.inf if omega_min <= 0 else \
                     asw_one * hoop_length * mat.fyd / (mat.fcd * b_0 * h_0 * omega_min)

            s_ec2 = min(20.0 * layout.diameter, min(geom.b, geom.h), 400.0)

            s_cr  = _round_down(min(s_shear, s_detail, s_conf))
            s_cur = _round_down(min(s_shear, s_ec2))

            if s_cr < MIN_STIRRUP_STEP:
                continue

            s_cur    = max(s_cur, s_cr)
            omega_wd = asw_one * hoop_length / (b_0 * h_0 * s_cr) * mat.fyd / mat.fcd

            governing = min((s_shear, "forță tăietoare"), (s_detail, "alcătuire P100"),
                            (s_conf, "confinare ωwd"))[1]

            return TransverseDesign(diameter, s_cr, s_cur, lcr, legs_x, legs_y, omega_wd, governing)

        return None

    def _shear_spacing(self, layout, diameter, section, asw_one, legs_x, legs_y, lcr) -> float | None:
        """Distanța maximă între etrieri din forța tăietoare (toate combinațiile, ambele direcții)"""
        geom, mat, rules = self.geom, self.mat, self.rules
        s_req  = math.inf
        nu_1   = 0.6 * (1.0 - mat.fck / 250.0)

        self.shear_log: list[str] = []

        for case in self.cases:
            n_ed = case.n * 1e3

            for axis, v_file, depth, width, legs in (("x", case.vy, geom.h, geom.b, legs_y),
                                                     ("y", case.vx, geom.b, geom.h, legs_x)):
                d_eff = depth - geom.cover - diameter - layout.diameter / 2.0
                z_lev = 0.9 * d_eff
                v_ed  = abs(v_file) * 1e3
                v_cap = 0.0

                if case.is_seismic:
                    m_rd  = section.m_rd(n_ed, axis)
                    ratio = min(1.0, max(0.0, self.options.beam_column_ratio))
                    v_cap = rules.gamma_rd * 2.0 * m_rd * ratio / geom.clear_height
                    v_ed  = max(v_ed, v_cap)

                if v_ed <= 0:
                    continue

                cot_max = rules.cot_theta_seismic if case.is_seismic else 2.5
                cot     = _cot_theta(v_ed, width, z_lev, nu_1 * mat.fcd, cot_max)

                if cot is None:
                    self.shear_log.append(f"  [{case.name}] V{'y' if axis == 'x' else 'x'}Ed = "
                                          f"{v_ed / 1e3:.0f} kN > VRd,max - secțiunea trebuie mărită")
                    return None

                s_case = legs * asw_one * z_lev * mat.fyd * cot / v_ed
                s_req  = min(s_req, s_case)

                self.shear_log.append(
                    f"  [{case.name}] V{'y' if axis == 'x' else 'x'}Ed = {v_ed / 1e3:.0f} kN"
                    + (f" (capacitate γRd·ΣMRd·min(1, ΣMRb/ΣMRc) / lcl = {v_cap / 1e3:.0f} kN)" if case.is_seismic else "")
                    + f", cot θ = {cot:.2f}, {legs} ramuri → s ≤ {s_case:.0f} mm")

        return s_req

    def _report_transverse(self, trv: TransverseDesign, messages: list[str]):
        rules = self.rules
        messages += ["", f"Armare transversală Ø{trv.diameter:g} (etrier perimetral + agrafe la fiecare "
                         f"bară intermediară; ramuri: {trv.legs_y} pe Y, {trv.legs_x} pe X)"]
        messages += self.shear_log
        messages += [f"  lcr = {trv.critical_length:.0f} mm (P100-1, {rules.name})",
                     f"  zona critică: s = {trv.spacing_critical:g} mm (determinant: {trv.governing}), "
                     f"ωwd = {trv.omega_wd:.3f}",
                     f"  zona curentă: s = {trv.spacing_current:g} mm (EC2 9.5.3 și forța tăietoare)",
                     f"  distanța între barele legate ≤ {rules.max_bar_distance:.0f} mm: OK (agrafe la toate barele)"]

    def _check_cover(self, layout: BarLayout, trv: TransverseDesign, result: ColumnDesignResult):
        if self.geom.cover + trv.diameter < layout.diameter:
            result.warnings.append("Acoperirea barelor longitudinale este mai mică decât diametrul lor "
                                   "(EC2 4.4.1.2, cmin,b)")

    def _lap_length(self, diameter: float) -> float:
        """Lungimea de suprapunere EC2 8.7.3, α1..α5 = 1, α6 = 1.5 (100 % bare înnădite în aceeași secțiune)"""
        mat     = self.mat
        lb_rqd  = diameter / 4.0 * mat.fyd / mat.fbd
        alpha_6 = 1.5

        return math.ceil(max(alpha_6 * lb_rqd, 0.3 * alpha_6 * lb_rqd, 15.0 * diameter, 200.0) / 10.0) * 10.0


def _round_down(value: float) -> float:
    if math.isinf(value):
        return 400.0
    return math.floor(value / SPACING_STEP + 1e-9) * SPACING_STEP


def _cot_theta(v_ed: float, width: float, z_lev: float, nu_fcd: float, cot_max: float) -> float | None:
    """Cea mai mare valoare cot θ ∈ [1, cot_max] pentru care VRd,max ≥ VEd (αcw = 1)"""
    def v_rd_max(cot: float) -> float:
        return width * z_lev * nu_fcd / (cot + 1.0 / cot)

    if v_rd_max(1.0) < v_ed:
        return None

    cot = cot_max
    while cot > 1.0 and v_rd_max(cot) < v_ed:
        cot = max(1.0, cot - 0.05)

    return cot


def design_column(geom   : ColumnGeometry,
                  mat    : Materials,
                  cases  : list[EffortCase],
                  options: DesignOptions) -> ColumnDesignResult:
    """Funcție de conveniență pentru dimensionare"""
    return ColumnDesigner(geom, mat, cases, options).design()
