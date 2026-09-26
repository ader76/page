"""DATASET_BRUT -> DATASET_NETTOYE.

Étapes (chaque étape est comptée dans rapport_nettoyage.json) :
 1. doublons techniques : même (plateforme, comment_id) collecté deux fois -> 1 seul gardé ;
 2. répétitions d'un même compte : même compte, même texte normalisé -> 1 seul gardé ;
 3. spam (liens promotionnels, auto-promotion) -> retiré ;
 4. copier-coller entre comptes : même texte (>= 25 caractères) chez >= 3 comptes -> GARDÉ
    mais marqué (copypasta_*), pour pouvoir comparer les résultats avec/sans ;
 5. quasi-doublons (MinHash sur 5-grammes de caractères, Jaccard >= 0,8) chez >= 3 comptes
    -> GARDÉS mais marqués (neardup_*).
Les marques 4-5 sont calculées AVANT l'étape 2, sur dataset_dedup_technique.jsonl, fichier
que coordination.py utilise (sinon le nettoyage effacerait les indices de coordination).
Les textes génériques très courts ("مبروك", "bravo") ne sont jamais marqués comme
copier-coller : leur répétition est naturelle.

Usage : python clean_dedup.py data_work/raw data_work
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from classify import classify
from common import assign_period, normalize, read_jsonl

MIN_COPY_CHARS = 25
MIN_COPY_ACCOUNTS = 3
NEAR_DUP_JACCARD = 0.8
N_PERM, BANDS = 64, 16  # 16 bandes x 4 lignes
_P = np.uint64((1 << 61) - 1)
_rng = np.random.default_rng(20260923)
# a, b < 2^31 et x < 2^32 : a*x + b < 2^64, pas de débordement avant le modulo
_A = _rng.integers(1, 1 << 31, size=N_PERM, dtype=np.uint64)
_B = _rng.integers(0, 1 << 31, size=N_PERM, dtype=np.uint64)


def text_key(norm: str) -> str:
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def shingles(norm: str, k: int = 5) -> set[str]:
    s = norm.replace(" ", "_")
    return {s[i:i + k] for i in range(max(1, len(s) - k + 1))}


def minhash(sh: set[str]) -> np.ndarray:
    x = np.array([int.from_bytes(hashlib.blake2b(t.encode(), digest_size=4).digest(), "little")
                  for t in sh], dtype=np.uint64)
    return ((np.multiply.outer(_A, x) + _B[:, None]) % _P).min(axis=1)


class UnionFind:
    def __init__(self):
        self.parent: dict[int, int] = {}

    def find(self, a: int) -> int:
        self.parent.setdefault(a, a)
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def near_duplicate_clusters(rows: list[dict]) -> dict[int, int]:
    """Retourne {index de ligne: id de cluster} pour les quasi-doublons (Jaccard >= seuil)."""
    idx = [i for i, r in enumerate(rows) if len(r["text_norm"]) >= MIN_COPY_CHARS]
    sigs, shs = {}, {}
    for i in idx:
        shs[i] = shingles(rows[i]["text_norm"])
        sigs[i] = minhash(shs[i])
    buckets: dict[tuple, list[int]] = defaultdict(list)
    rows_per_band = N_PERM // BANDS
    for i in idx:
        for b in range(BANDS):
            buckets[(b, sigs[i][b * rows_per_band:(b + 1) * rows_per_band].tobytes())].append(i)
    uf = UnionFind()
    for members in buckets.values():
        if len(members) < 2:
            continue
        head = members[0]
        for other in members[1:]:
            a, b = shs[head], shs[other]
            if len(a & b) / max(1, len(a | b)) >= NEAR_DUP_JACCARD:
                uf.union(head, other)
    return {i: uf.find(i) for i in uf.parent}


def _flag_copies(rows: list[dict]) -> None:
    """Copier-coller exact et quasi-doublons partagés par >= 3 comptes (marquage seulement)."""
    authors_by_text: dict[str, set] = defaultdict(set)
    for r in rows:
        if len(r["text_norm"]) >= MIN_COPY_CHARS and r["n_tokens"] > 3:
            authors_by_text[r["text_key"]].add((r.get("platform"), r.get("author_hash")))
    for r in rows:
        n = len(authors_by_text.get(r["text_key"], ()))
        r["copypasta_n_accounts"] = n
        r["copypasta_flag"] = n >= MIN_COPY_ACCOUNTS
    clusters = near_duplicate_clusters(rows)
    members: dict[int, set] = defaultdict(set)
    for i, c in clusters.items():
        members[c].add((rows[i].get("platform"), rows[i].get("author_hash")))
    for i, r in enumerate(rows):
        c = clusters.get(i)
        r["neardup_cluster"] = c if c is not None and len(members[c]) >= MIN_COPY_ACCOUNTS else None
        r["neardup_n_accounts"] = len(members[c]) if c is not None else 1
        r["neardup_flag"] = r["neardup_cluster"] is not None


def build(raw_dir: str, out_dir: str) -> dict:
    raw_files = sorted(Path(raw_dir).glob("*.jsonl"))
    rows = [r for f in raw_files for r in read_jsonl(f)]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = {"fichiers_bruts": [f.name for f in raw_files], "n_brut": len(rows)}

    # DATASET_BRUT : toutes les lignes, enrichies, sans suppression
    for i, r in enumerate(rows):
        r["row_id"] = i
        r["text_norm"] = normalize(r.get("text") or "", keep_emojis=False)
        r["text_key"] = text_key(r["text_norm"])
        r["period"] = assign_period(r.get("published_at"))
        r["n_tokens"] = len(r["text_norm"].split())
        r["spam_flag"] = classify(r.get("text") or "")["spam_flag"] or (r.get("text") or "").count("http") >= 2
    with (out / "dataset_brut.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 1. doublons techniques
    seen, kept = set(), []
    for r in rows:
        key = (r.get("platform"), r.get("comment_id"))
        if r.get("comment_id") and key in seen:
            continue
        seen.add(key)
        kept.append(r)
    report["retires_doublons_techniques"] = len(rows) - len(kept)

    # Marquage copier-coller / quasi-doublons sur les données AVANT dédoublonnage de contenu :
    # la coordination doit voir les répétitions que le nettoyage retire ensuite.
    _flag_copies(kept)
    with (out / "dataset_dedup_technique.jsonl").open("w", encoding="utf-8") as fh:
        for r in kept:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 2. répétitions d'un même compte
    seen, step2 = set(), []
    for r in kept:
        key = (r.get("platform"), r.get("author_hash"), r["text_key"])
        if r.get("author_hash") and r["text_norm"] and key in seen:
            continue
        seen.add(key)
        step2.append(r)
    report["retires_repetitions_meme_compte"] = len(kept) - len(step2)

    # 3. spam
    step3 = [r for r in step2 if not r["spam_flag"]]
    report["retires_spam"] = len(step2) - len(step3)

    # 4-5. les marques copier-coller / quasi-doublons (posées avant l'étape 2) restent
    # sur les lignes conservées : elles ne sont PAS retirées, pour comparer avec/sans.
    report["n_nettoye"] = len(step3)
    report["marques_copier_coller"] = sum(r["copypasta_flag"] for r in step3)
    report["marques_quasi_doublons"] = sum(r["neardup_flag"] for r in step3)
    report["n_clusters_quasi_doublons"] = len({r["neardup_cluster"] for r in step3 if r["neardup_flag"]})
    with (out / "dataset_nettoye.jsonl").open("w", encoding="utf-8") as fh:
        for r in step3:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (out / "rapport_nettoyage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))
