"""Briques de calcul BAEL 91 modifié 99 (unités : kN, kN·m, m, MPa ; sections d'acier en cm²)."""
from dataclasses import dataclass
from math import ceil, pi, sqrt

AREA = {6: .283, 8: .503, 10: .785, 12: 1.131, 14: 1.539, 16: 2.011, 20: 3.142, 25: 4.909}  # cm²


@dataclass(frozen=True)
class Mat:
    fc28: float = 25.0
    fe: float = 400.0
    gb: float = 1.5
    gs: float = 1.15
    eta: float = 1.6      # coefficient de fissuration, barres HA
    Es: float = 200000.0

    @property
    def fbu(self): return 0.85 * self.fc28 / self.gb
    @property
    def ft28(self): return 0.6 + 0.06 * self.fc28
    @property
    def fsu(self): return self.fe / self.gs
    @property
    def sbc(self): return 0.6 * self.fc28
    @property
    def mu_l(self):
        al = 3.5 / (3.5 + 1000 * self.fsu / self.Es)
        return 0.8 * al * (1 - 0.4 * al)

    def ss(self, cr: str) -> float:
        """Contrainte limite de l'acier à l'ELS selon la fissuration (FN, FP, TP)."""
        return {"FN": self.fe,
                "FP": min(2 / 3 * self.fe, 110 * sqrt(self.eta * self.ft28)),
                "TP": min(0.5 * self.fe, 90 * sqrt(self.eta * self.ft28))}[cr]


def r5(x: float) -> float:
    return ceil(x * 20 - 1e-9) / 20


def els(Ms_MNm, b, d, As_m2, n=15):
    """Contraintes ELS section rectangulaire fissurée (béton comprimé, acier tendu)."""
    A, B, C = b / 2, n * As_m2, -n * As_m2 * d
    y = (-B + sqrt(B * B - 4 * A * C)) / (2 * A)
    I = b * y ** 3 / 3 + n * As_m2 * (d - y) ** 2
    return Ms_MNm * y / I, n * Ms_MNm * (d - y) / I


def flex(Mu, Ms, b, d, m: Mat, cr="FP", asmin_cm2=0.0) -> dict:
    """Flexion simple ELU + vérification ELS (béton et acier). Mu, Ms en kN·m."""
    Mu_, Ms_ = Mu / 1000, Ms / 1000
    mu = Mu_ / (b * d * d * m.fbu)
    if mu > m.mu_l:
        return {"ok": False, "mu": mu, "As": 0.0}
    al = 1.25 * (1 - sqrt(1 - 2 * mu))
    As_elu = Mu_ / (d * (1 - 0.4 * al) * m.fsu)
    As = max(As_elu, asmin_cm2 / 1e4)
    lim = m.ss(cr)
    for _ in range(800):
        sb, ss = els(Ms_, b, d, As)
        if sb <= m.sbc and ss <= lim:
            break
        As *= 1.02
    else:
        return {"ok": False, "mu": mu, "As": As * 1e4}
    return {"ok": True, "mu": mu, "As": As * 1e4, "As_elu": As_elu * 1e4, "sigma_bc": sb, "sigma_s": ss}


def pick(As, nmin=2, nmax=8, dias=(10, 12, 14, 16, 20, 25)):
    for d in dias:
        n = max(nmin, ceil(As / AREA[d] - 1e-9))
        if n <= nmax:
            return n, d
    return ceil(As / AREA[dias[-1]]), dias[-1]


def bars(As, nmin=2, nmax=8, dias=(10, 12, 14, 16, 20, 25)) -> str:
    n, d = pick(As, nmin, nmax, dias)
    return f"{n}HA{d}"


def slab_layout(As, h, cr="FP") -> str:
    smax = min(2 * h, 0.25) if cr != "FN" else min(3 * h, 0.33)
    for d in (8, 10, 12):
        for s in (0.25, 0.20, 0.15, 0.125, 0.10):
            if s <= smax + 1e-9 and AREA[d] / s >= As:
                return f"HA{d} e={s * 100:g} cm"
    return "HA12 e=10 cm (à renforcer)"


def stirrups(At_over_st_cm2_m, d, nlegs=2):
    """Cadres HA6 (sinon HA8) : espacement en cm, multiple de 5, plafonné à min(0.9d, 40 cm)."""
    for phi in (6, 8):
        At = nlegs * AREA[phi]
        st = At / max(At_over_st_cm2_m, 1e-9)  # m (cm² / cm²/m)
        st = min(st, 0.9 * d, 0.20)
        st = int(st * 20) / 20
        if st >= 0.075 or phi == 8:
            return phi, max(st, 0.05)
