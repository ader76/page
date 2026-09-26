"""Indices de comportement coordonné au niveau des comptes.

Ne déclare JAMAIS un compte « bot ». Attribue une probabilité qualitative de
comportement coordonné (faible / moyenne / élevée) à partir d'indices observables,
et conserve pour chaque compte la liste des indices (colonne `indices`).

Les indices sont calculés sur dataset_dedup_technique.jsonl (AVANT suppression des
répétitions), puis la probabilité est reportée sur les lignes du jeu nettoyé.

Indices FORTS (comportement difficilement explicable par une expression spontanée) :
  sync     : >= 2 fois, un texte identique/quasi identique publié par au moins 2 AUTRES
             comptes à +/- 10 minutes (horodatage exact requis) ;
  rafale   : le même texte publié par le compte sous >= 3 publications différentes.
Indices MOYENS (compatibles avec une expression spontanée, à corroborer) :
  copie    : >= 50 % des commentaires du compte sont des textes partagés par >= 3 comptes
             (les formules banales longues peuvent le déclencher : jamais suffisant seul) ;
  repetition : même texte publié >= 3 fois par le compte ;
  hashtags : même jeu de >= 2 hashtags que >= 5 comptes dans la même heure ;
  jeune    : compte créé < 30 jours avant son premier commentaire (si connu) et >= 5 commentaires ;
  volume   : nombre de commentaires >= max(20, 99e centile de la plateforme).
Règle : élevée = 2 indices forts, ou 1 fort + >= 1 moyen ; moyenne = 1 fort, ou >= 3 moyens ;
faible sinon. « Activité exclusivement politique » exige l'historique complet du compte :
non évaluée (NA).

Usage : python coordination.py data_work/dataset_dedup_technique.jsonl \
            data_work/dataset_nettoye.jsonl data_work
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from common import read_jsonl

HASHTAG = re.compile(r"#[\wء-ي_]+")
SYNC_WINDOW = timedelta(minutes=10)


def _ts(x):
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def account_features(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()
    df["ts"] = df["published_at"].map(_ts)
    df["acct"] = df["platform"].astype(str) + ":" + df["author_hash"].astype(str)
    df["group"] = df["neardup_cluster"].where(df["neardup_flag"].fillna(False).astype(bool), None)
    df["group"] = df["group"].fillna(df["text_key"].where(df["copypasta_flag"].fillna(False).astype(bool), None))

    # sync : membres d'un même groupe de textes publiés à +/- 10 minutes par >= 2 autres comptes
    sync_hits = defaultdict(int)
    exact_ts = ~df["published_at_approx"].fillna(False).astype(bool)
    for _, g in df[df["group"].notna() & df["ts"].notna() & exact_ts].groupby("group"):
        times, accts = list(g["ts"]), list(g["acct"])
        for i, t in enumerate(times):
            others = {accts[j] for j, u in enumerate(times) if j != i and abs(u - t) <= SYNC_WINDOW}
            others.discard(accts[i])
            if len(others) >= 2:
                sync_hits[accts[i]] += 1

    # rafale / répétition : même texte (non vide) du même compte
    nonempty = df[df["text_norm"].fillna("").str.len() >= 10]
    same = nonempty.groupby(["acct", "text_key"]).agg(n=("text", "size"), posts=("post_id", "nunique"))
    burst = same[same["posts"] >= 3].reset_index().groupby("acct").size()
    repeat = same[same["n"] >= 3].reset_index().groupby("acct").size()

    # hashtags partagés dans la même heure
    df["tags"] = df["text"].fillna("").map(lambda t: tuple(sorted({h.lower() for h in HASHTAG.findall(t)})))
    df["hour"] = df["ts"].map(lambda t: t.replace(minute=0, second=0, microsecond=0) if t else None)
    tag_hits = defaultdict(int)
    for _, g in df[df["tags"].map(len) >= 2].groupby(["tags", "hour"]):
        if g["acct"].nunique() >= 5:
            for a in g["acct"]:
                tag_hits[a] += 1

    agg = df.groupby("acct").agg(
        platform=("platform", "first"),
        n_commentaires=("text", "size"),
        n_publications=("post_id", "nunique"),
        n_copies=("copypasta_flag", "sum"),
        n_quasi_doublons=("neardup_flag", "sum"),
        premier=("ts", "min"),
        cree_le=("author_created_at", "first"),
    ).reset_index()
    agg["part_copies"] = (agg[["n_copies", "n_quasi_doublons"]].max(axis=1) / agg["n_commentaires"]).clip(upper=1)
    agg["n_sync"] = agg["acct"].map(sync_hits).fillna(0).astype(int)
    agg["n_rafales"] = agg["acct"].map(burst).fillna(0).astype(int)
    agg["n_repetitions"] = agg["acct"].map(repeat).fillna(0).astype(int)
    agg["n_hashtags_partages"] = agg["acct"].map(tag_hits).fillna(0).astype(int)
    p99 = agg.groupby("platform")["n_commentaires"].transform(lambda s: s.quantile(0.99))
    agg["volume_anormal"] = agg["n_commentaires"] >= p99.clip(lower=20)
    created = agg["cree_le"].map(_ts)
    agg["compte_jeune"] = [bool(c and p and (p - c) < timedelta(days=30) and n >= 5)
                           for c, p, n in zip(created, agg["premier"], agg["n_commentaires"])]
    agg["activite_exclusivement_politique"] = pd.NA

    probs, indices = [], []
    for r in agg.itertuples():
        strong = [x for x, ok in ((f"sync({r.n_sync})", r.n_sync >= 2),
                                  (f"rafale({r.n_rafales})", r.n_rafales >= 1)) if ok]
        medium = [x for x, ok in ((f"copie({r.part_copies:.0%})", r.part_copies >= 0.5 and r.n_commentaires >= 3),
                                  (f"repetition({r.n_repetitions})", r.n_repetitions >= 1),
                                  ("hashtags", r.n_hashtags_partages >= 1),
                                  ("compte_jeune", r.compte_jeune),
                                  (f"volume({r.n_commentaires})", r.volume_anormal)) if ok]
        if len(strong) >= 2 or (strong and medium):
            probs.append("elevee")
        elif strong or len(medium) >= 3:
            probs.append("moyenne")
        else:
            probs.append("faible")
        indices.append(";".join(strong + medium))
    agg["probabilite_coordination"] = probs
    agg["indices"] = indices
    return agg.drop(columns=["premier"])


def main(features_src: str, clean_src: str, out_dir: str) -> None:
    feats = account_features(read_jsonl(features_src))
    out = Path(out_dir)
    feats.to_csv(out / "comptes_coordination.csv", index=False)
    prob = dict(zip(feats["acct"], feats["probabilite_coordination"]))
    rows = read_jsonl(clean_src)
    with (out / "dataset_nettoye_coord.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            r["coord_prob"] = prob.get(f"{r.get('platform')}:{r.get('author_hash')}", "faible")
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(feats["probabilite_coordination"].value_counts().to_string())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
