"""Validation humaine/IA du classifieur.

1) python validate.py sample data_work/dataset_classe.jsonl validation/a_annoter.csv --n 600
   -> tire un échantillon ALÉATOIRE (stratifié proportionnellement par plateforme, graine
      fixe) et exporte une feuille à annoter : colonnes gold_* vides.
2) Un·e annotateur·rice relit chaque commentaire DANS SON CONTEXTE (URL de la publication,
   réponses) et remplit gold_party_main, gold_sentiment_main, gold_cred_main, gold_sarcasm.
3) python validate.py score validation/a_annoter.csv validation/rapport_validation.json
   -> taux d'erreur par dimension (IC de Wilson), kappa de Cohen, matrices de confusion.
   Règle : si une dimension clé dépasse 10 % d'erreur, le classifieur doit être amélioré
   (dictionnaire, ou classify_llm.py) puis revalidé sur un NOUVEL échantillon.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict

from common import read_jsonl
from stats_utils import cohen_kappa, wilson

THREE = {"tres_favorable": "favorable", "favorable": "favorable", "neutre": "neutre",
         "defavorable": "defavorable", "tres_defavorable": "defavorable"}
MACRO = {"R1": "ACCEPTE", "R2": "SURPRISE", "R3": "INCOMPREHENSION", "R4": "DOUTE",
         "R5": "ACCUSATION", "R6": "ACCUSATION", "R7": "ACCUSATION", "R8": "STRUCTUREL",
         "R9": "STRUCTUREL", "R10": "AUCUNE"}
KEY_DIMENSIONS = ["party_main", "sentiment_3", "cred_macro"]
FIELDS = ["sample_id", "platform", "post_url", "comment_id", "text",
          "pred_party_main", "pred_sentiment_main", "pred_cred_main", "pred_sarcasm",
          "pred_intentions", "gold_party_main", "gold_sentiment_main", "gold_cred_main",
          "gold_sarcasm", "annotateur", "notes"]


def main_sentiment(r: dict) -> str:
    if r.get("party_main") not in (None, "aucun", "multiple"):
        return r.get("sentiment_by_party", {}).get(r["party_main"], "neutre")
    return r.get("sentiment_global", "neutre")


def sample(src: str, dst: str, n: int = 600, seed: int = 2026) -> None:
    rows = read_jsonl(src)
    by_platform = defaultdict(list)
    for r in rows:
        by_platform[r.get("platform")].append(r)
    rng = random.Random(seed)
    chosen = []
    for plat, items in sorted(by_platform.items(), key=lambda kv: str(kv[0])):
        k = max(1, round(n * len(items) / len(rows)))
        chosen += rng.sample(items, min(k, len(items)))
    rng.shuffle(chosen)
    with open(dst, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for i, r in enumerate(chosen):
            w.writerow({
                "sample_id": i, "platform": r.get("platform"), "post_url": r.get("post_url"),
                "comment_id": r.get("comment_id"), "text": r.get("text"),
                "pred_party_main": r.get("party_main"), "pred_sentiment_main": main_sentiment(r),
                "pred_cred_main": r.get("cred_main"), "pred_sarcasm": r.get("sarcasm_flag"),
                "pred_intentions": json.dumps(r.get("intentions"), ensure_ascii=False),
            })
    print(f"{len(chosen)} commentaires tirés -> {dst}")


def _dimension(pairs: list[tuple[str, str]]) -> dict:
    pairs = [(p, g) for p, g in pairs if g not in (None, "")]
    n = len(pairs)
    errors = sum(p != g for p, g in pairs)
    rate, lo, hi = wilson(errors, n)
    confusion = Counter(f"{g} -> {p}" for p, g in pairs if p != g)
    return {"n": n, "erreurs": errors, "taux_erreur": rate, "ic95": [lo, hi],
            "kappa": cohen_kappa([p for p, _ in pairs], [g for _, g in pairs]),
            "confusions_principales": confusion.most_common(10)}


def score(src: str, dst: str) -> None:
    with open(src, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    res = {
        "party_main": _dimension([(r["pred_party_main"], r["gold_party_main"]) for r in rows]),
        "sentiment_5": _dimension([(r["pred_sentiment_main"], r["gold_sentiment_main"]) for r in rows]),
        "sentiment_3": _dimension([(THREE.get(r["pred_sentiment_main"], r["pred_sentiment_main"]),
                                    THREE.get(r["gold_sentiment_main"], r["gold_sentiment_main"]))
                                   for r in rows]),
        "cred_main": _dimension([(r["pred_cred_main"], r["gold_cred_main"]) for r in rows]),
        "cred_macro": _dimension([(MACRO.get(r["pred_cred_main"], ""), MACRO.get(r["gold_cred_main"], ""))
                                  for r in rows if r["gold_cred_main"]]),
        "sarcasm": _dimension([(str(r["pred_sarcasm"]).lower(), str(r["gold_sarcasm"]).lower())
                               for r in rows if r["gold_sarcasm"] != ""]),
    }
    worst = max(res[d]["taux_erreur"] for d in KEY_DIMENSIONS if res[d]["n"])
    res["decision"] = "VALIDE (<= 10 %)" if worst <= 0.10 else "A_AMELIORER (> 10 %) : enrichir le dictionnaire ou classify_llm.py, puis revalider sur un nouvel echantillon"
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
    for d in ["party_main", "sentiment_3", "sentiment_5", "cred_macro", "cred_main", "sarcasm"]:
        x = res[d]
        print(f"{d:12s} n={x['n']:4d} erreur={100 * x['taux_erreur']:.1f} % kappa={x['kappa']:.2f}")
    print(res["decision"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "score"])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    sample(a.src, a.dst, a.n, a.seed) if a.cmd == "sample" else score(a.src, a.dst)
