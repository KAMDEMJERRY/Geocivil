"""Calculs de référence faits à la main (BAEL 91 mod. 99, fc28=25 MPa, fe=400 MPa)."""
from math import sqrt
from types import SimpleNamespace as N

import pytest

from app.engine.analysis import analyze, col_cap, footing, slab_at
from app.engine.bael import Mat, flex, r5, els

m = Mat()


def test_constantes_materiaux():
    assert m.fbu == pytest.approx(14.167, abs=1e-3)
    assert m.ft28 == pytest.approx(2.1)
    assert m.fsu == pytest.approx(347.83, abs=0.01)
    assert m.mu_l == pytest.approx(0.392, abs=0.001)
    assert m.ss("FP") == pytest.approx(201.6, abs=0.1)
    assert m.ss("TP") == pytest.approx(164.96, abs=0.1)


def test_flexion_simple_exemple_main():
    # b=0,20 d=0,315 Mu=50 kN·m : μ=0,1778 α=0,2466 z=0,2839 → As=5,06 cm²
    r = flex(50, 0, 0.20, 0.315, m, "FN")
    assert r["mu"] == pytest.approx(0.1778, abs=1e-3)
    assert r["As_elu"] == pytest.approx(5.06, rel=0.01)


def test_els_section_fissuree():
    sb, ss = els(0.035, 0.20, 0.315, 5.06e-4)
    assert 0 < sb < m.sbc and 100 < ss < 400


def test_poteau_elancement_35():
    lam, al, br = col_cap(0.20, 0.2 * 35 / (0.7 * sqrt(12)) * 1.0, m)  # λ = 35 → α = 0,85/1,2
    assert lam == pytest.approx(35, abs=0.01)
    assert al == pytest.approx(0.7083, abs=1e-3)
    assert br == pytest.approx(0.0324)


def test_semelle_isolee_dimension():
    f, A = footing(450, 300, 0.20, 200, "FP", m)
    assert A == r5(sqrt(1.1 * 300 / 200)) == 1.30
    assert f["verifications"][0]["ok"] and f["verifications"][2]["ok"]


def test_dalle_carree_coefficients():
    s = slab_at(0.15, 4, 4, 2.4, 1.5, m)       # ρ=1 : μx = 1/(8·3,4) = 0,0368 ; μy = 1
    assert s["M0x"] == pytest.approx(0.0368 * s["pu"] * 16, rel=1e-3)
    assert s["M0y"] == pytest.approx(s["M0x"], rel=1e-6)


SOIL = dict(soil_type="laterite", bearing_capacity_kpa=200, water_table_depth_m=3, flood_zone=False, geotech_study="rapport")
BLD = dict(footprint_m2=120, length_width_ratio=1.5, floors=1, floor_height_m=3.0, column_span_m=4.0,
           usage="habitation", roof_type="tole", roof_slope_pct=30)


def run(soil=None, bld=None):
    return analyze(N(**{**SOIL, **(soil or {})}), N(**{**BLD, **(bld or {})}))


def test_ordre_de_grandeur_charges():
    r = run()
    # ~ 9 à 14 kN/m² par niveau pour une maison courante
    assert 15 < r["verdict"]["pression_moyenne_kPa"] < 30
    assert r["toutes_verifications_ok"]


def test_plus_d_etages_plus_de_charge_et_sections():
    a, b, c = (run(bld={"floors": n}) for n in (0, 1, 2))
    q = [x["verdict"]["pression_moyenne_kPa"] for x in (a, b, c)]
    assert q[0] < q[1] < q[2]
    assert c["toutes_verifications_ok"]
    assert c["poteaux"]["section_cm"][0] >= a["poteaux"]["section_cm"][0]


def test_sol_faible_semelles_plus_larges():
    f1 = run()["fondations"]["semelles"]["courant"]["cote_A_m"]
    f2 = run(soil={"bearing_capacity_kpa": 100})["fondations"]["semelles"]["courant"]["cote_A_m"]
    assert f2 > f1


def test_sol_insuffisant_et_eau():
    r = run(soil={"bearing_capacity_kpa": 40, "water_table_depth_m": 0.5})
    assert r["verdict"]["niveau"] == "bad"
    assert r["fondations"]["classe_fissuration"] == "TP"
    assert any("Nappe" in a for a in r["alertes"])


def test_terrasse_commerce_passe():
    r = run(bld={"roof_type": "terrasse", "usage": "commerce", "floors": 2})
    assert r["toutes_verifications_ok"]


def test_grille_de_cas_sans_erreur():
    import itertools
    for S, rt, fl, sp, us, rf in itertools.product((30, 120, 400, 1500), (1, 2.5), (0, 1, 2), (3, 4.5, 6), ("habitation", "commerce"), ("tole", "terrasse")):
        try:
            r = run(bld=dict(footprint_m2=S, length_width_ratio=rt, floors=fl, column_span_m=sp, usage=us, roof_type=rf))
        except ValueError:
            continue  # portée jugée trop grande : refus explicite, pas de résultat faux
        assert r["poteaux"]["section_cm"][0] <= 60
