"""Moteur d'analyse : maison R+0 à R+2, ossature poteaux-poutres, norme BAEL 91 mod. 99."""
from math import ceil, pi, sqrt

from .bael import AREA, Mat, bars, flex, pick, r5, slab_layout, stirrups

VERSION = "0.2.0"
WALL = 2.6 * 0.85      # kN/m² de mur, parpaing 15 enduit 2 faces, 15 % d'ouvertures
ACROT = 1.5            # kN/m, acrotère
QUSE = {"habitation": 1.5, "bureaux": 2.5, "commerce": 5.0}
rd = lambda x, n=2: round(float(x), n)


# ---------------------------------------------------------------- dalles
def slab_at(h, lx, ly, Gfin, Q, m, cr="FP"):
    rho = lx / ly
    G = 25 * h + Gfin
    pu, ps = 1.35 * G + 1.5 * Q, G + Q
    if rho >= 0.4:
        mx = 1 / (8 * (1 + 2.4 * rho ** 3))
        my = max(rho ** 2 * (1 - 0.95 * (1 - rho) ** 2), 0.25)
    else:
        mx, my = 1 / 8, 0.0
    M0x = mx * pu * lx ** 2
    M0y = my * M0x
    S0x, S0y = mx * ps * lx ** 2, my * mx * ps * lx ** 2
    Msx, Msy = S0x + 0.2 * S0y, S0y + 0.2 * S0x     # ELS, ν = 0,2
    dx, dy = h - 0.03, h - 0.04
    r0 = 0.0008 if m.fe <= 400 else 0.0006
    Axm, Aym = r0 * (3 - rho) / 2 * h * 1e4, r0 * h * 1e4
    tx = flex(0.85 * M0x, 0.85 * Msx, 1, dx, m, cr, Axm)
    ty = flex(0.85 * M0y, 0.85 * Msy, 1, dy, m, cr, Aym) if my else {"ok": True, "As": 0.0}
    ap = flex(0.5 * M0x, 0.5 * Msx, 1, dx, m, cr, Axm)
    ok = tx["ok"] and ty["ok"] and ap["ok"]
    out = {"ok": ok, "G": G, "pu": pu, "ps": ps, "rho": rho, "M0x": M0x, "M0y": M0y}
    if ok:
        Ay = max(ty["As"], tx["As"] / 4, Aym)
        c1 = h / lx >= 0.85 / 20
        c2 = tx["As"] / 1e4 / dx <= 2 / m.fe
        out.update(tx=tx, ty=ty, ap=ap, Ay=Ay,
                   verif_fleche=[{"nom": "h/lx ≥ Mt/(20·M0)", "valeur": rd(h / lx, 4), "limite": rd(0.85 / 20, 4), "ok": c1},
                                 {"nom": "A/(b·d) ≤ 2/fe", "valeur": rd(tx["As"] / 1e4 / dx, 5), "limite": rd(2 / m.fe, 5), "ok": c2}])
        out["ok"] = c1 and c2
    return out


def design_slabs(lx, ly, Gfl, Qfl, Grf, Qrf, F, m):
    h = max(0.12, ceil(lx / 35 * 100 - 1e-9) / 100)
    while h < 0.40:
        sf = slab_at(h, lx, ly, Gfl, Qfl, m) if F > 1 else None
        sr = slab_at(h, lx, ly, Grf, Qrf, m)
        if (sf is None or sf["ok"]) and sr["ok"]:
            return h, sf, sr
        h = round(h + 0.01, 2)
    raise ValueError("Portée trop grande pour une dalle pleine : réduire la portée entre poteaux")


def slab_out(s, h, nom):
    return {"niveau": nom, "epaisseur_cm": rd(h * 100, 0), "charge_permanente_kN_m2": rd(s["G"]), "pu_kN_m2": rd(s["pu"]),
            "armatures_travee_x": {"As_cm2_m": rd(s["tx"]["As"]), "choix": slab_layout(s["tx"]["As"], h)},
            "armatures_travee_y": {"As_cm2_m": rd(s["Ay"]), "choix": slab_layout(s["Ay"], h)},
            "chapeaux_appui": {"As_cm2_m": rd(s["ap"]["As"]), "choix": slab_layout(s["ap"]["As"], h)},
            "verif_els": {"sigma_bc_MPa": rd(s["tx"]["sigma_bc"]), "sigma_s_MPa": rd(s["tx"]["sigma_s"])},
            "verif_fleche": s["verif_fleche"]}


# ---------------------------------------------------------------- poutres
def beam_one(Lb, other, pos, lev, bw, h, hf, hd, m):
    lxp, lyp = min(Lb, other), max(Lb, other)
    rho = lxp / lyp
    c = lxp / 3 if Lb <= other else lxp / 2 * (1 - rho ** 2 / 3)   # charge équivalente (moment)
    n = 2 if pos == "courante" else 1
    wall = 0.0 if pos == "courante" else (WALL * (hf - h) if not lev["roof"] else (ACROT if lev["terr"] else 0.0))
    g = n * c * lev["G"] + 25 * bw * h + wall
    q = n * c * lev["Q"]
    qu, qs = 1.35 * g + 1.5 * q, g + q
    M0, S0 = qu * Lb ** 2 / 8, qs * Lb ** 2 / 8
    d = h - 0.04
    amin = 0.23 * bw * d * m.ft28 / m.fe * 1e4
    t = flex(0.85 * M0, 0.85 * S0, bw, d, m, "FP", amin)
    a = flex(0.6 * M0, 0.6 * S0, bw, d, m, "FP", amin)
    r = flex(0.15 * M0, 0.15 * S0, bw, d, m, "FP", amin)
    row = {"ok": t["ok"] and a["ok"] and r["ok"], "qu": qu, "M0": M0}
    if not row["ok"]:
        return row
    Vu = 1.15 * qu * Lb / 2
    tau = Vu / 1000 / (bw * d)
    tau_lim = min(0.15 * m.fc28 / m.gb, 4.0)
    ats = max(bw * (tau - 0.3 * m.ft28) / (0.9 * m.fsu), 0.4 * bw / m.fe) * 1e4  # cm²/m
    phi, st = stirrups(ats, d)
    c = [{"nom": "h/L ≥ 1/16", "valeur": rd(h / Lb, 4), "limite": 0.0625, "ok": h / Lb >= 1 / 16},
         {"nom": "h/L ≥ Mt/(10·M0)", "valeur": rd(h / Lb, 4), "limite": 0.085, "ok": h / Lb >= 0.085},
         {"nom": "A/(b·d) ≤ 4,2/fe", "valeur": rd(t["As"] / 1e4 / (bw * d), 5), "limite": rd(4.2 / m.fe, 5), "ok": t["As"] / 1e4 / (bw * d) <= 4.2 / m.fe}]
    row["ok"] = all(x["ok"] for x in c) and tau <= tau_lim
    row.update(t=t, a=a, r=r, Vu=Vu, tau=tau, tau_lim=tau_lim, phi=phi, st=st, fleche=c)
    return row


def design_beams(ax, ay, F, hf, hd, levels, m):
    bw = 0.20 if max(ax, ay) <= 4.5 else 0.25
    h = max(0.30, r5(max(ax, ay) / 12))
    while h <= 0.90:
        rows, ok = [], True
        for lev in levels:
            for dr, Lb, ot in (("x", ax, ay), ("y", ay, ax)):
                for pos in ("courante", "rive"):
                    r = beam_one(Lb, ot, pos, lev, bw, h, hf, hd, m)
                    rows.append((lev, dr, Lb, pos, r))
                    ok &= r["ok"]
        if ok:
            return bw, h, rows
        h = round(h + 0.05, 2)
    raise ValueError("Portée trop grande pour des poutres courantes")


def beam_out(lev, dr, Lb, pos, r, bw, h):
    return {"niveau": lev["nom"], "direction": dr, "position": pos, "portee_m": rd(Lb), "section_cm": [rd(bw * 100, 0), rd(h * 100, 0)],
            "qu_kN_m": rd(r["qu"]), "Mu_travee_kNm": rd(0.85 * r["M0"]),
            "travee": {"As_cm2": rd(r["t"]["As"]), "choix": bars(r["t"]["As"], 2, 4, (10, 12, 14, 16, 20))},
            "appui_courant": {"As_cm2": rd(r["a"]["As"]), "choix": bars(r["a"]["As"], 2, 4, (10, 12, 14, 16, 20))},
            "appui_rive": {"As_cm2": rd(r["r"]["As"]), "choix": bars(r["r"]["As"], 2, 4, (10, 12, 14, 16, 20))},
            "effort_tranchant": {"Vu_kN": rd(r["Vu"]), "tau_u_MPa": rd(r["tau"]), "limite_MPa": rd(r["tau_lim"]), "cadres": f"HA{r['phi']} e={r['st'] * 100:g} cm"},
            "verif_fleche": r["fleche"], "verif_els": {"sigma_bc_MPa": rd(r["t"]["sigma_bc"]), "sigma_s_MPa": rd(r["t"]["sigma_s"])}}


# ---------------------------------------------------------------- poteaux
def col_cap(a, l0, m):
    lam = 0.7 * l0 * sqrt(12) / a
    al = 0.85 / (1 + 0.2 * (lam / 35) ** 2) if lam <= 50 else 0.6 * (50 / lam) ** 2
    Br = (a - 0.02) ** 2
    return lam, al, Br


def col_loads(cat, i, F, ax, ay, lv, bw, hb, hf, a, terr):
    """Charges (kN) en pied du poteau du niveau i (1 = RDC), niveaux i..F cumulés (sans dégressivité)."""
    A = {"courant": ax * ay, "rive": ax * ay / 2, "angle": ax * ay / 4}[cat]
    Lbm = {"courant": ax + ay, "rive": max(ax + ay / 2, ay + ax / 2), "angle": (ax + ay) / 2}[cat]
    Lw = {"courant": 0.0, "rive": max(ax, ay), "angle": (ax + ay) / 2}[cat]
    G = Q = 0.0
    for j in range(i, F + 1):
        s = lv[F] if j == F else lv[1]
        G += s["G"] * A + 25 * bw * hb * Lbm + 25 * a * a * (hf - hb) + WALL * (hf - hb) * Lw
        Q += s["Q"] * A
        if j == F and terr:
            G += ACROT * Lw
    k = 1.0 if cat == "angle" else 1.10   # BAEL B.8.1 : majoration des poteaux voisins du 1er appui intermédiaire (poutres continues)
    return G * k, Q * k


def design_columns(F, ax, ay, lv, bw, hb, hf, terr, m):
    l0 = hf - hb
    a = 0.20 if F <= 2 else 0.25     # minimum constructif : 20 cm (R+0, R+1), 25 cm (R+2)
    while a <= 0.60:
        lam, al, Br = col_cap(a, l0, m)
        G, Q = col_loads("courant", 1, F, ax, ay, lv, bw, hb, hf, a, terr)
        Ath = ((1.35 * G + 1.5 * Q) / 1000 / al - Br * m.fc28 / (0.9 * m.gb)) * m.gs / m.fe * 1e4
        if lam <= 50 and Ath <= 0.02 * a * a * 1e4:
            break
        a = round(a + 0.05, 2)
    rows = []
    for i in range(1, F + 1):
        for cat in ("courant", "rive", "angle"):
            G, Q = col_loads(cat, i, F, ax, ay, lv, bw, hb, hf, a, terr)
            Nu, Ns = 1.35 * G + 1.5 * Q, G + Q
            lam, al, Br = col_cap(a, l0, m)
            Ath = (Nu / 1000 / al - Br * m.fc28 / (0.9 * m.gb)) * m.gs / m.fe * 1e4
            B = a * a * 1e4
            As = max(Ath, 4 * 4 * a, 0.002 * B)
            n = 4 if As <= 4 * AREA[25] else 8
            if n == 4:
                d = next(x for x in (12, 14, 16, 20, 25) if 4 * AREA[x] >= As)
            else:
                d = next((x for x in (14, 16, 20, 25) if 8 * AREA[x] >= As), 25)
            Asp = n * AREA[d]
            cap = al * (Br * m.fc28 / (0.9 * m.gb) + Asp / 1e4 * m.fe / m.gs) * 1000
            phit = 6 if d <= 16 else 8
            st = int(min(15 * d / 10, 40, a * 100 + 10) / 5) * 5
            rows.append({"niveau": "RDC" if i == 1 else f"Niveau {i - 1}", "categorie": cat, "Nu_kN": rd(Nu), "Nser_kN": rd(Ns), "section_cm": [rd(a * 100, 0)] * 2,
                         "elancement": rd(lam, 1), "As_theorique_cm2": rd(max(Ath, 0)), "armatures": f"{n}HA{d}", "cadres": f"HA{phit} e={st} cm",
                         "verifications": [{"nom": "Nu ≤ Nu,lim (B.8.4.1)", "valeur": rd(Nu), "limite": rd(cap), "ok": Nu <= cap},
                                           {"nom": "λ ≤ 50", "valeur": rd(lam, 1), "limite": 50, "ok": lam <= 50},
                                           {"nom": "As ≤ 5 % B", "valeur": rd(Asp), "limite": rd(0.05 * B), "ok": Asp <= 0.05 * B}],
                         "_Nu1": Nu if i == 1 else None, "_Ns1": Ns if i == 1 else None})
    return a, rows


# ---------------------------------------------------------------- fondations
def footing(Nu, Ns, a, sigma, cr, m):
    A = max(0.80, r5(sqrt(1.1 * Ns / sigma)))
    h = max(0.30, r5((A - a) / 4 + 0.05))
    d = h - 0.05
    As_u = Nu / 1000 * (A - a) / (8 * d * m.fsu) * 1e4
    As_s = Ns / 1000 * (A - a) / (8 * d * m.ss(cr)) * 1e4
    As = max(As_u, As_s, 0.23 * A * d * m.ft28 / m.fe * 1e4)
    n, dia = pick(As, 5, 20, (10, 12, 14, 16))
    qu = Nu / A ** 2
    Qp = (Nu - qu * (a + h) ** 2) / 1000
    Qlim = 0.045 * 4 * (a + h) * h * m.fc28 / m.gb
    ls = dia / 1000 * m.fe / (4 * 0.6 * 1.5 ** 2 * m.ft28)
    anc = "barres droites" if ls <= A / 8 else ("crochets recommandés" if ls <= A / 4 else "crochets obligatoires")
    sig = 1.1 * Ns / A ** 2
    return {"cote_A_m": rd(A), "hauteur_h_cm": rd(h * 100, 0), "d_m": rd(d), "As_cm2_par_sens": rd(As),
            "armatures": f"{n}HA{dia} par sens (e≈{(A - 0.10) / (n - 1) * 100:.0f} cm)", "ancrage": f"ls={ls * 100:.0f} cm : {anc}",
            "classe_fissuration": cr,
            "verifications": [{"nom": "σ sol ≤ σ adm (kPa)", "valeur": rd(sig, 1), "limite": sigma, "ok": sig <= sigma + 1e-6},
                              {"nom": "Poinçonnement Qu ≤ 0,045·uc·h·fc28/γb (MN)", "valeur": rd(Qp, 3), "limite": rd(Qlim, 3), "ok": Qp <= Qlim},
                              {"nom": "Bielles : d ≥ (A−a)/4", "valeur": rd(d), "limite": rd((A - a) / 4), "ok": d >= (A - a) / 4 - 1e-9}]}, A


def analyze(soil, bld, m: Mat = Mat()) -> dict:
    S, F, hf = bld.footprint_m2, bld.floors + 1, bld.floor_height_m
    L = sqrt(S * bld.length_width_ratio)
    l = S / L
    nx, ny = ceil(L / bld.column_span_m) + 1, ceil(l / bld.column_span_m) + 1
    ax, ay = L / (nx - 1), l / (ny - 1)
    terr = bld.roof_type == "terrasse"
    Qfl = QUSE[bld.usage]
    Qrf = 1.5 if terr else 1.0
    Gfl, Grf = 2.4, (2.3 if terr else 0.8)
    sigma = soil.bearing_capacity_kpa
    cr_f = "TP" if (soil.water_table_depth_m < 1.0 or soil.flood_zone) else "FP"

    hd, sf, sr = design_slabs(min(ax, ay), max(ax, ay), Gfl, Qfl, Grf, Qrf, F, m)
    lv = {j: {"G": 25 * hd + (Grf if j == F else Gfl), "Q": Qrf if j == F else Qfl} for j in range(1, F + 1)}
    levels = ([{"nom": "Plancher courant", "G": lv[1]["G"], "Q": lv[1]["Q"], "roof": False, "terr": terr}] if F > 1 else []) + \
             [{"nom": "Toiture", "G": lv[F]["G"], "Q": lv[F]["Q"], "roof": True, "terr": terr}]
    bw, hb, brows = design_beams(ax, ay, F, hf, hd, levels, m)
    a, crow = design_columns(F, ax, ay, lv, bw, hb, hf, terr, m)

    cnt = {"angle": 4, "rive": 2 * (nx - 2) + 2 * (ny - 2), "courant": (nx - 2) * (ny - 2)}
    base = {r["categorie"]: r for r in crow if r["_Nu1"]}
    fond, cover, Ntot = {}, 0.0, 0.0
    for cat, n in cnt.items():
        if not n:
            continue
        extra = 25 * a * a * 1.0
        Nu, Ns = base[cat]["_Nu1"] + 1.35 * extra, base[cat]["_Ns1"] + extra
        fond[cat], A = footing(Nu, Ns, a, sigma, cr_f, m)
        fond[cat]["nombre"] = n
        cover += n * A * A
        Ntot += n * 1.1 * Ns
    q = Ntot / S
    ratio = q / sigma
    cover /= S
    for r in crow:
        r.pop("_Nu1"), r.pop("_Ns1")

    if sigma < 60 or ratio > 1:
        niv, txt = "bad", "Sol insuffisant pour des fondations superficielles : fondations profondes ou amélioration du sol"
    elif ratio > 0.85:
        niv, txt = "warn", "Sol à la limite : marge faible, étude géotechnique indispensable"
    else:
        niv, txt = "ok", "Le sol peut porter le bâtiment" + (" avec une bonne marge" if ratio <= 0.5 else "")
    type_fond = "semelles isolées" if cover <= 0.35 else ("semelles filantes (ferraillage non détaillé en phase 1)" if cover <= 0.5 else "radier général (non détaillé en phase 1)")
    if niv == "bad":
        type_fond = "pieux (hors périmètre phase 1)"

    al = []
    if soil.geotech_study == "none":
        al.append("Aucune étude de sol : la contrainte admissible est une estimation. Sondages (pénétromètre, SPT) à réaliser avant exécution.")
    if soil.water_table_depth_m < 1.5:
        al.append(f"Nappe à {soil.water_table_depth_m} m : drainage, étanchéité des fondations, béton compact ; fissuration traitée en classe très préjudiciable.")
    if soil.flood_zone:
        al.append("Zone inondable : plancher bas à surélever d'au moins 0,50 m ; fissuration traitée en classe très préjudiciable.")
    if soil.soil_type in ("argile", "marais"):
        al.append("Sol sensible (gonflement, tassements différentiels) : purge ou fondations profondes à étudier ; semelles à relier par longrines.")
    if cover > 0.35 and niv != "bad":
        al.append("Semelles isolées trop rapprochées : passer en semelles filantes ou radier (étude dédiée, prévue dans une phase suivante).")
    chk = [v["ok"] for r in crow for v in r["verifications"]] + [v["ok"] for f in fond.values() for v in f["verifications"]]
    return {"version_moteur": VERSION, "norme": "BAEL 91 modifié 99", "materiaux": {"fc28_MPa": m.fc28, "fe_MPa": m.fe},
            "verdict": {"niveau": niv, "texte": txt, "pression_moyenne_kPa": rd(q, 1), "contrainte_admissible_kPa": sigma, "taux": rd(ratio, 2)},
            "geometrie": {"L_m": rd(L), "l_m": rd(l), "poteaux_x": nx, "poteaux_y": ny, "portee_x_m": rd(ax), "portee_y_m": rd(ay), "niveaux": F, "repartition_poteaux": cnt},
            "dalles": [slab_out(s, hd, n) for s, n in ((sf, "Plancher courant"), (sr, "Toiture")) if s],
            "poutres": [beam_out(lev, dr, Lb, pos, r, bw, hb) for lev, dr, Lb, pos, r in brows],
            "poteaux": {"section_cm": [rd(a * 100, 0)] * 2, "detail": crow},
            "fondations": {"type_retenu": type_fond, "classe_fissuration": cr_f, "taux_occupation": rd(cover, 2), "semelles": fond},
            "toutes_verifications_ok": all(chk), "alertes": al,
            "hypotheses": ["Ossature poteaux-poutres en béton armé, dalles pleines, trame régulière.",
                           "Poutres continues : méthode forfaitaire simplifiée (Mt = 0,85·M0, appui courant 0,6·M0, appui de rive 0,15·M0).",
                           "Charges d'exploitation NF P06-001, sans dégressivité ; charges cumulées conservatives sur les poteaux, majorées de 10 % hors poteaux d'angle.",
                           "Fissuration préjudiciable (climat tropical humide), très préjudiciable en présence d'eau.",
                           "Pré-dimensionnement à valider par un ingénieur agréé : ni vent, ni séisme, ni escalier, ni longrines calculés."]}
