"""Analyse électorale à partir des seules données publiées et sourcées (dossier data/).

Ce qui est calculé :
  1. sièges et parts de sièges 2026 (et variation 2021 quand elle est sourcée) ;
  2. répartition urbain/rural des sièges : chi2 d'indépendance, V de Cramér, et pour chaque
     parti un test exact de Fisher (parti vs reste des partis) ;
  3. mécanique du quotient électoral (inscrits / sièges) : part minimale des suffrages
     valides pour obtenir un siège au quotient = 1 / (S x participation x (1 - nuls)) ;
  4. indice de conversion (part des sièges / part des voix) dans la circonscription où la
     distribution des voix est publiée (Tanger-Assilah) ;
  5. tests participation <-> performance et ASD <-> vote : exécutés seulement si les
     données provinciales existent (data/provinces.csv), sinon « DONNÉES INSUFFISANTES ».

Usage : python analyze_elections.py ../data ../resultats
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from stats_utils import correlations  # noqa: E402

# Palette de référence (dataviz/references/palette.md), mode clair
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#e1e0d9", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"
ORDINAL_BLUE = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]  # pas 250 -> 700

N_CONSTITUENCIES = 92 + 12  # circonscriptions locales + régionales


def _style(ax, title, subtitle=None):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.set_title(title, loc="left", color=INK, fontsize=12, fontweight="bold", pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=9, va="bottom")


def fr(x: float, nd: int = 1) -> str:
    """Nombre au format français (virgule décimale)."""
    return f"{x:.{nd}f}".replace(".", ",")


def _save(fig, path):
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def seats(data: Path) -> pd.DataFrame:
    df = pd.read_csv(data / "resultats_nationaux_2026.csv")
    df["part_sieges_2026"] = df["sieges_2026"] / df["sieges_2026"].sum()
    df["sieges_2021"] = pd.to_numeric(df["sieges_2021"], errors="coerce")
    df["variation"] = df["sieges_2026"] - df["sieges_2021"]
    df["sieges_par_circonscription"] = df["sieges_2026"] / N_CONSTITUENCIES
    return df


def urban_rural(data: Path) -> dict:
    ur = pd.read_csv(data / "sieges_urbain_rural_2026.csv")
    ur = ur[ur["parti"] != "TOTAL"].set_index("parti")
    table = ur[["sieges_urbains", "sieges_ruraux"]].astype(int)
    chi2, p, dof, _ = stats.chi2_contingency(table)
    n = table.to_numpy().sum()
    cramer = float(np.sqrt(chi2 / (n * (min(table.shape) - 1))))
    tot_u, tot_r = table["sieges_urbains"].sum(), table["sieges_ruraux"].sum()
    per_party = {}
    for party, row in table.iterrows():
        u, r = int(row["sieges_urbains"]), int(row["sieges_ruraux"])
        odds, pf = stats.fisher_exact([[u, r], [tot_u - u, tot_r - r]])
        per_party[party] = {"urbains": u, "ruraux": r, "part_urbaine": u / (u + r),
                            "part_urbaine_autres_partis": (tot_u - u) / (n - u - r),
                            "odds_ratio": float(odds), "p_fisher": float(pf)}
    return {"chi2": float(chi2), "p": float(p), "ddl": int(dof), "cramer_v": cramer,
            "part_urbaine_ensemble": float(tot_u / n), "partis": per_party}


def quotient_threshold(seats_s: int, turnout: float, invalid: float = 0.0) -> float:
    """Part minimale des suffrages VALIDES pour atteindre le quotient (inscrits / sièges)."""
    return 1.0 / (seats_s * turnout * (1.0 - invalid))


def tanger_assilah(data: Path) -> dict:
    c = pd.read_csv(data / "circonscriptions_2026_echantillon.csv")
    t = c[c["circonscription"] == "Tanger-Assilah"].copy()
    t["pct"] = pd.to_numeric(t["pct_publie"], errors="coerce") / 100
    t["elu_b"] = t["elu"].str.startswith("oui")
    seats_s, registered, turnout = 5, 412447, 0.2551
    t["part_sieges"] = np.where(t["elu_b"], 1 / seats_s, 0.0)
    t["indice_conversion"] = t["part_sieges"] / t["pct"]
    pjd = t[t["parti"] == "PJD"].iloc[0]
    valid_est = float(pjd["voix"]) / float(pjd["pct"])
    quotient = registered / seats_s
    return {
        "sieges": seats_s, "inscrits": registered, "participation": turnout,
        "quotient_voix": quotient,
        "suffrages_valides_estimes": valid_est,
        "plus_forte_liste_voix": float(pjd["voix"]),
        "quotient_atteignable": bool(pjd["voix"] >= quotient),
        "seuil_quotient_sans_nuls": quotient_threshold(seats_s, turnout),
        "listes": t[["parti", "voix", "pct", "part_sieges", "indice_conversion", "elu_b"]]
        .rename(columns={"pct": "part_voix", "elu_b": "elu"}).to_dict("records"),
        "remarque": ("parts de voix issues d'un dépouillement à ~90 % ; suffrages valides estimés = "
                     "voix PJD / part PJD (approximation)"),
    }


def provincial_tests(data: Path) -> dict:
    """Participation <-> performance, ASD <-> vote : seulement si data/provinces.csv existe.

    Colonnes attendues (une ligne par province, chaque valeur sourcée) : province,
    participation, part_PAM, part_PJD, part_RNI, part_PI, part_ASD, taux_pauvrete,
    taux_urbanisation. Une corrélation, même forte, ne dit rien de la causalité.
    """
    path = data / "provinces.csv"
    if not path.exists():
        return {"statut": "DONNEES_INSUFFISANTES",
                "manque": "voix par parti, participation, bénéficiaires ASD/RSU, pauvreté et urbanisation "
                          "PAR PROVINCE (non publiés ou inaccessibles au 26/09/2026)"}
    prov = pd.read_csv(path)
    out = {}
    for party in ["PAM", "PJD", "RNI", "PI"]:
        col = f"part_{party}"
        if col in prov:
            out[f"participation~{party}"] = correlations(prov["participation"], prov[col])
            if "part_ASD" in prov:
                out[f"ASD~{party}"] = correlations(prov["part_ASD"], prov[col])
                # corrélation partielle en contrôlant urbanisation et pauvreté (résidus OLS)
                ctrl = [c for c in ("taux_urbanisation", "taux_pauvrete", "participation") if c in prov]
                if ctrl:
                    X = np.column_stack([np.ones(len(prov))] + [prov[c] for c in ctrl])
                    rx = prov["part_ASD"] - X @ np.linalg.lstsq(X, prov["part_ASD"], rcond=None)[0]
                    ry = prov[col] - X @ np.linalg.lstsq(X, prov[col], rcond=None)[0]
                    out[f"ASD~{party}|controles"] = correlations(rx, ry)
    return out


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def fig_seats(df: pd.DataFrame, path: Path) -> None:
    d = df[df["sieges_2021"].notna()].sort_values("sieges_2026")
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    y = np.arange(len(d))
    for yi, (_, r) in zip(y, d.iterrows()):
        ax.plot([r["sieges_2021"], r["sieges_2026"]], [yi, yi], color=BASELINE, lw=2, solid_capstyle="round", zorder=1)
    ax.scatter(d["sieges_2021"], y, s=70, color=MUTED, edgecolor=SURFACE, linewidth=2, zorder=2, label="2021")
    ax.scatter(d["sieges_2026"], y, s=70, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3, label="2026")
    for yi, (_, r) in zip(y, d.iterrows()):
        ax.text(max(r["sieges_2021"], r["sieges_2026"]) + 4, yi,
                f"{int(r['sieges_2021'])} → {int(r['sieges_2026'])} ({int(r['variation']):+d})",
                va="center", color=INK2, fontsize=9)
    ax.set_yticks(y, d["parti_sigle"])
    ax.set_xlim(0, 130)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.set_xlabel("sièges (sur 395)", color=MUTED, fontsize=9)
    _style(ax, "Sièges des quatre premiers partis, 2021 → 2026",
           "Résultats définitifs du ministère de l'Intérieur (25/09/2026) ; 2021 d'après la presse")
    ax.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=INK2)
    _save(fig, path)


def fig_urban(ur: dict, path: Path) -> None:
    parts = sorted(ur["partis"].items(), key=lambda kv: kv[1]["part_urbaine"])
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    y = np.arange(len(parts))
    xs = [v["part_urbaine"] * 100 for _, v in parts]
    ax.axvline(ur["part_urbaine_ensemble"] * 100, color=BASELINE, lw=1, zorder=1)
    ax.text(ur["part_urbaine_ensemble"] * 100 + 1, len(parts) - 1.5,
            f"ensemble des sièges : {fr(100 * ur['part_urbaine_ensemble'])} %", color=MUTED, fontsize=8)
    ax.scatter(xs, y, s=80, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
    for yi, (name, v) in zip(y, parts):
        ax.text(v["part_urbaine"] * 100 + 2.5, yi, f"{v['urbains']}/{v['urbains'] + v['ruraux']}",
                va="center", color=INK2, fontsize=9)
    ax.set_yticks(y, [p for p, _ in parts])
    ax.set_xlim(0, 100)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.set_xlabel("part des sièges du parti élus en milieu urbain (%)", color=MUTED, fontsize=9)
    _style(ax, "Où chaque parti a gagné ses sièges",
           f"Classement urbain/rural rapporté par Belpresse ; χ² = {fr(ur['chi2'])}, p < 0,001, V de Cramér = {fr(ur['cramer_v'], 2)}")
    _save(fig, path)


def fig_threshold(path: Path) -> None:
    t = np.linspace(0.15, 0.80, 200)
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for color, s in zip(ORDINAL_BLUE, [2, 3, 4, 6, 12]):
        v = np.clip(100 * quotient_threshold(s, t), 0, 160)
        ax.plot(t * 100, v, color=color, lw=2, solid_capstyle="round")
        ax.text(80.8, min(v[-1], 158), f"{s} sièges", color=INK2, fontsize=8, va="center")
    ax.axhline(100, color=BASELINE, lw=1)
    ax.text(56, 103, "au-delà de 100 % : quotient impossible", color=MUTED, fontsize=8)
    for x, lab in [(25.5, "Tanger-Assilah\n25,5 %"), (38.0, "national\n38,0 %"), (77.0, "Laâyoune-S.E.H.\n77 %")]:
        ax.axvline(x, color=GRID, lw=1, zorder=0)
        ax.text(x + 0.6, 150, lab, color=MUTED, fontsize=7.5, va="top")
    ax.set_xlim(15, 88)
    ax.set_ylim(0, 160)
    ax.yaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.set_xlabel("participation (% des inscrits)", color=MUTED, fontsize=9)
    ax.set_ylabel("% des suffrages valides nécessaires", color=MUTED, fontsize=9)
    _style(ax, "Part des voix nécessaire pour gagner un siège « au quotient »",
           "Quotient = inscrits / sièges ; hypothèse 0 % de bulletins nuls (borne basse)")
    _save(fig, path)


def fig_tanger(ta: dict, path: Path) -> None:
    rows = sorted(ta["listes"], key=lambda r: r["part_voix"])
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    y = np.arange(len(rows))
    h = 0.34
    ax.barh(y + h / 2 + 0.02, [100 * r["part_voix"] for r in rows], height=h, color=BLUE, label="part des voix")
    ax.barh(y - h / 2 - 0.02, [100 * r["part_sieges"] for r in rows], height=h, color=ORANGE, label="part des sièges")
    for yi, r in zip(y, rows):
        if r["elu"]:
            ax.text(100 * r["part_voix"] + 0.8, yi + h / 2 + 0.02, f"{fr(100 * r['part_voix'])} %",
                    va="center", color=INK2, fontsize=8)
    ax.set_yticks(y, [r["parti"].replace("ALLIANCE_GAUCHE", "Alliance gauche") for r in rows])
    ax.set_xlim(0, 36)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.set_xlabel("%", color=MUTED, fontsize=9)
    _style(ax, "Tanger-Assilah : 5 sièges, 5 listes, 1 siège chacune",
           "Le PJD obtient 31,5 % des voix et 20 % des sièges ; le RNI 8,8 % des voix et 20 % des sièges")
    ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK2)
    _save(fig, path)


def main(data_dir: str, out_dir: str) -> dict:
    data, out = Path(data_dir), Path(out_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    df = seats(data)
    ur = urban_rural(data)
    ta = tanger_assilah(data)
    thresholds = {f"S={s}": {f"t={t:.2f}": round(100 * quotient_threshold(s, t), 1)
                             for t in (0.25, 0.30, 0.3802, 0.50, 0.77)} for s in (2, 3, 4, 5, 6, 12)}
    res = {
        "sieges": df[["parti_sigle", "sieges_2026", "sieges_2021", "variation", "part_sieges_2026",
                      "sieges_par_circonscription"]].to_dict("records"),
        "urbain_rural": ur,
        "seuils_quotient_pct_suffrages_valides": thresholds,
        "tanger_assilah": ta,
        "tests_provinciaux": provincial_tests(data),
        "voix_nationales": "NON PUBLIEES au 26/09/2026 : voix/siège et indice de conversion national non calculables",
    }
    fig_seats(df, out / "figures" / "01_sieges_2021_2026.png")
    fig_urban(ur, out / "figures" / "02_sieges_urbains_par_parti.png")
    fig_threshold(out / "figures" / "03_seuil_quotient.png")
    fig_tanger(ta, out / "figures" / "04_tanger_assilah_voix_sieges.png")
    (out / "analyse_electorale.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=float),
                                                 encoding="utf-8")
    return res


if __name__ == "__main__":
    r = main(sys.argv[1], sys.argv[2])
    print(json.dumps({k: r[k] for k in ("urbain_rural", "tests_provinciaux")}, ensure_ascii=False, indent=1, default=float)[:3000])
