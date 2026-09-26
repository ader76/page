"""Opinion numérique : trois lectures + synthèse prudente.

  1. PAR COMMENTAIRE  : chaque commentaire compte (IC par bootstrap sur les comptes) ;
  2. PAR COMPTE UNIQUE : un compte = une voix par parti (moyenne de ses commentaires) ;
  3. PAR PLATEFORME    : chaque plateforme pèse autant (moyenne des parts par plateforme),
     pour qu'une plateforme dominante ne dicte pas la conclusion.

Rien ici n'est une estimation de l'opinion de la population marocaine : ce sont des parts
observées DANS l'échantillon de commentaires publics collectés.

Usage : python analyze_opinion.py data_work/dataset_classe.jsonl results [--brut data_work/dataset_brut_classe.jsonl]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from common import read_jsonl
from stats_utils import cluster_bootstrap_share, fmt_pct, wilson

MAJOR = ["PAM", "RNI", "PI", "PJD", "MP", "USFP", "PPS", "UC"]
NUM = {"tres_defavorable": -2, "defavorable": -1, "neutre": 0, "favorable": 1, "tres_favorable": 2}
SUPPORT = {"A_VOTE", "VEUT_VOTER", "SOUTIENT"}
PRIORITY = ["R5", "R6", "R4", "R7", "R3", "R2", "R8", "R9", "R1", "R10"]
MACRO_Q = {"R1": "accepte", "R2": "surprise_incomprehension", "R3": "surprise_incomprehension",
           "R4": "doute", "R5": "fraude_achat_clientelisme", "R6": "fraude_achat_clientelisme",
           "R7": "fraude_achat_clientelisme", "R8": "mode_scrutin_abstention",
           "R9": "mode_scrutin_abstention", "R10": "aucune_position"}
DOUBT = {"R4", "R5", "R6", "R7"}
MIN_N = 30  # en dessous, une part par plateforme n'est pas publiée


def sent3(label: str) -> str:
    v = NUM.get(label, 0)
    return "favorable" if v > 0 else ("defavorable" if v < 0 else "neutre")


def load(path: str) -> pd.DataFrame:
    df = pd.DataFrame(read_jsonl(path))
    df["acct"] = df["platform"].astype(str) + ":" + df["author_hash"].astype(str)
    for col, default in [("coord_prob", "faible"), ("copypasta_flag", False), ("neardup_flag", False)]:
        if col not in df:
            df[col] = default
    return df


def long_party(df: pd.DataFrame) -> pd.DataFrame:
    recs = []
    for r in df.itertuples():
        for party, label in (r.sentiment_by_party or {}).items():
            recs.append({"row_id": r.row_id, "platform": r.platform, "acct": r.acct, "party": party,
                         "label": label, "s3": sent3(label), "num": NUM.get(label, 0),
                         "period": r.period, "coord_prob": r.coord_prob})
    return pd.DataFrame(recs)


def party_table(lp: pd.DataFrame) -> pd.DataFrame:
    """Parts favorable/neutre/défavorable par plateforme et parti, par commentaire ET par compte."""
    out = []
    platforms = sorted(lp["platform"].unique()) + ["TOUTES"]
    for plat in platforms:
        sub = lp if plat == "TOUTES" else lp[lp["platform"] == plat]
        for party in [p for p in MAJOR if p in set(sub["party"])]:
            s = sub[sub["party"] == party]
            users = s.groupby("acct")["num"].mean().map(lambda v: "favorable" if v > 0 else ("defavorable" if v < 0 else "neutre"))
            row = {"plateforme": plat, "parti": party, "n_commentaires": len(s), "n_comptes": users.size}
            for cat in ["favorable", "neutre", "defavorable"]:
                p, lo, hi = cluster_bootstrap_share((s["s3"] == cat).to_numpy(), s["acct"].to_numpy())
                row[f"{cat}_commentaires"] = fmt_pct(p, lo, hi) if len(s) >= MIN_N else "n<30"
                k = int((users == cat).sum())
                p2, lo2, hi2 = wilson(k, users.size)
                row[f"{cat}_comptes"] = fmt_pct(p2, lo2, hi2) if users.size >= MIN_N else "n<30"
            out.append(row)
    return pd.DataFrame(out)


def platform_equal_weight(lp: pd.DataFrame, cat: str = "defavorable", B: int = 1000, seed: int = 7) -> pd.DataFrame:
    """Moyenne des parts par plateforme (chaque plateforme pèse autant), IC par bootstrap des comptes."""
    rng = np.random.default_rng(seed)
    out = []
    for party in MAJOR:
        per_plat = []
        for plat, s in lp[lp["party"] == party].groupby("platform"):
            users = s.groupby("acct")["num"].mean()
            if users.size >= MIN_N:
                per_plat.append(((users < 0) if cat == "defavorable" else (users > 0)).to_numpy().astype(float))
        if not per_plat:
            continue
        point = float(np.mean([v.mean() for v in per_plat]))
        boots = [np.mean([rng.choice(v, size=v.size).mean() for v in per_plat]) for _ in range(B)]
        out.append({"parti": party, "categorie": cat, "n_plateformes": len(per_plat),
                    "part_moyenne_plateformes": fmt_pct(point, np.quantile(boots, .025), np.quantile(boots, .975))})
    return pd.DataFrame(out)


def explicit(df: pd.DataFrame) -> pd.DataFrame:
    """Soutien/rejet EXPLICITES (déclarations), comptés en comptes uniques. Jamais des votes."""
    sup, rej = {}, {}
    for r in df.itertuples():
        for kind, party in (r.intentions or []):
            if not party:
                continue
            (sup if kind in SUPPORT else rej if kind == "REJETTE" else {}).setdefault(party, set()).add(r.acct)
    n_sup = len(set().union(*sup.values())) if sup else 0
    n_rej = len(set().union(*rej.values())) if rej else 0
    out = []
    for party in MAJOR:
        ks, kr = len(sup.get(party, ())), len(rej.get(party, ()))
        out.append({"parti": party,
                    "comptes_soutien_explicite": ks,
                    "part_du_soutien_explicite": fmt_pct(*wilson(ks, n_sup)) if n_sup else "n.d.",
                    "comptes_rejet_explicite": kr,
                    "part_du_rejet_explicite": fmt_pct(*wilson(kr, n_rej)) if n_rej else "n.d."})
    return pd.DataFrame(out)


def credibility(df: pd.DataFrame) -> pd.DataFrame:
    """Réponse à la question C, par commentaire et par compte (code le plus grave du compte)."""
    out = []
    for plat in sorted(df["platform"].unique()) + ["TOUTES"]:
        s = df if plat == "TOUTES" else df[df["platform"] == plat]
        cm = s["cred_main"].map(MACRO_Q)
        user_code = s.groupby("acct")["cred_codes"].apply(
            lambda cs: next(c for c in PRIORITY if any(c in x for x in cs)))
        um = user_code.map(MACRO_Q)
        user_doubt = s.groupby("acct")["cred_codes"].apply(lambda cs: any(set(x) & DOUBT for x in cs))
        for cat in ["accepte", "surprise_incomprehension", "doute", "fraude_achat_clientelisme",
                    "mode_scrutin_abstention", "aucune_position"]:
            p, lo, hi = cluster_bootstrap_share((cm == cat).to_numpy(), s["acct"].to_numpy())
            out.append({"plateforme": plat, "categorie": cat, "n_commentaires": len(s),
                        "part_commentaires": fmt_pct(p, lo, hi),
                        "n_comptes": um.size, "part_comptes": fmt_pct(*wilson(int((um == cat).sum()), um.size))})
        out.append({"plateforme": plat, "categorie": "AU_MOINS_UN_DOUTE (R4-R7, comptes)",
                    "n_commentaires": len(s), "part_commentaires": "",
                    "n_comptes": user_doubt.size,
                    "part_comptes": fmt_pct(*wilson(int(user_doubt.sum()), user_doubt.size))})
    return pd.DataFrame(out)


def periods(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Même mesure par période ; test du chi2 P2 (avant) vs P4 (après résultats)."""
    tab = pd.crosstab(df["period"], df["cred_main"].map(MACRO_Q))
    shares = (tab.T / tab.sum(axis=1)).T.round(3)
    test = {}
    if {"P2", "P4"} <= set(tab.index):
        sub = tab.loc[["P2", "P4"]]
        sub = sub.loc[:, sub.sum() > 0]
        chi2, p, dof, _ = stats.chi2_contingency(sub)
        test = {"P2_vs_P4_chi2": float(chi2), "p": float(p), "ddl": int(dof)}
    return shares, test


def sensitivity(df: pd.DataFrame, lp: pd.DataFrame) -> pd.DataFrame:
    """Résultats AVEC / SANS comptes à probabilité de coordination moyenne ou élevée."""
    sus = set(df.loc[df["coord_prob"].isin(["moyenne", "elevee"]), "acct"])
    rows = []
    for party in MAJOR:
        a = lp[lp["party"] == party]
        b = a[~a["acct"].isin(sus)]
        if len(a) < MIN_N:
            continue
        with_, without = (a["s3"] == "defavorable").mean(), (b["s3"] == "defavorable").mean() if len(b) else float("nan")
        rows.append({"mesure": f"{party} % défavorable (commentaires)", "avec": with_, "sans": without})
    doubt_all = df["cred_codes"].map(lambda c: bool(set(c) & DOUBT)).mean()
    d2 = df[~df["acct"].isin(sus)]
    rows.append({"mesure": "% commentaires avec doute/accusation (R4-R7)", "avec": doubt_all,
                 "sans": d2["cred_codes"].map(lambda c: bool(set(c) & DOUBT)).mean() if len(d2) else float("nan")})
    out = pd.DataFrame(rows)
    out["ecart_points"] = (100 * (out["sans"] - out["avec"])).round(1)
    out["alerte_>5pts"] = out["ecart_points"].abs() > 5
    out["comptes_exclus"] = len(sus)
    return out


def counts(df: pd.DataFrame) -> dict:
    return {"n_commentaires": int(len(df)), "n_comptes_uniques": int(df["acct"].nunique()),
            "n_publications": int(df["post_id"].nunique()), "n_plateformes": int(df["platform"].nunique()),
            "langues": df["lang"].value_counts().to_dict() if "lang" in df else {},
            "periodes": df["period"].value_counts().to_dict()}


def run(src: str, out_dir: str, brut: str | None = None) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = load(src)
    lp = long_party(df)
    summary = {"nettoye": counts(df)}
    tables = {
        "opinion_par_plateforme_parti": party_table(lp) if len(lp) else pd.DataFrame(),
        "rejet_poids_egal_plateformes": platform_equal_weight(lp, "defavorable") if len(lp) else pd.DataFrame(),
        "soutien_poids_egal_plateformes": platform_equal_weight(lp, "favorable") if len(lp) else pd.DataFrame(),
        "soutien_rejet_explicites": explicit(df),
        "credibilite": credibility(df),
        "sensibilite_coordination": sensitivity(df, lp) if len(lp) else pd.DataFrame(),
    }
    shares, test = periods(df)
    tables["credibilite_par_periode"] = shares.reset_index()
    summary["test_periodes"] = test
    if brut:
        b = load(brut)
        summary["brut"] = counts(b)
        summary["doute_brut_vs_nettoye"] = {
            "brut": float(b["cred_codes"].map(lambda c: bool(set(c) & DOUBT)).mean()),
            "nettoye": float(df["cred_codes"].map(lambda c: bool(set(c) & DOUBT)).mean())}
    md = ["# Résultats — opinion numérique (échantillon, pas population)\n",
          "```json", json.dumps(summary, ensure_ascii=False, indent=2), "```\n"]
    for name, t in tables.items():
        t.to_csv(out / f"{name}.csv", index=False)
        md += [f"## {name}\n", t.to_markdown(index=False) if len(t) else "_aucune donnée_", ""]
    (out / "resume_opinion.md").write_text("\n".join(md), encoding="utf-8")
    (out / "resume_opinion.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(md[:4]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out_dir")
    ap.add_argument("--brut")
    a = ap.parse_args()
    run(a.src, a.out_dir, a.brut)
