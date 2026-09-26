"""Test de bout en bout de la chaîne sur un jeu SYNTHÉTIQUE.

Le jeu est généré dans un dossier temporaire à chaque exécution : ce ne sont PAS des
commentaires réels, ils ne sont jamais écrits dans data/ ni utilisés dans le rapport.
Il sert uniquement à vérifier que chaque étape détecte ce qu'elle doit détecter.
"""
import json
import os
import random
from datetime import datetime, timedelta, timezone

import pandas as pd

os.environ.setdefault("AUDIT_SALT", "sel-de-test-uniquement")

import analyze_opinion  # noqa: E402
import classify  # noqa: E402
import clean_dedup  # noqa: E402
import coordination  # noqa: E402
from common import pseudonymize  # noqa: E402

BASE = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
TEMPLATES = [  # phrases de test synthétiques
    "TEST مبروك للبيجيدي تستاهلو", "TEST البام فاسدين", "TEST Bravo au RNI victoire méritée",
    "TEST الانتخابات مزورة", "TEST ما صوتش هاد العام", "TEST النتيجة طبيعية الشعب قال كلمته",
    "TEST كيفاش ربح البام مفهمتش", "TEST PAM dégage", "TEST حزب الاستقلال الله يعاونكم",
    "TEST واخا البام محبوب 😂😂",
]
COORD_TEXT = "TEST نص منسق طويل بما يكفي ليعتبر نسخا ولصقا بين عدة حسابات مختلفة"


def _row(i, platform, author, text, minutes, comment_id=None):
    return {
        "platform": platform, "source_type": "social", "post_id": f"{platform}-post-{i % 7}",
        "post_url": f"https://example.invalid/{platform}/{i % 7}", "post_title": "TEST",
        "post_author": "TEST", "post_published_at": BASE.isoformat(),
        "comment_id": comment_id or f"{platform}-c{i}", "parent_comment_id": None, "is_reply": False,
        "author_hash": pseudonymize(platform, author), "author_created_at": None, "text": text,
        "published_at": (BASE + timedelta(minutes=minutes)).isoformat(), "published_at_approx": False,
        "like_count": 0, "query": "TEST", "sample_stratum": "test", "collected_at": BASE.isoformat(),
        "collector": "synthetique",
    }


def make_raw(raw_dir):
    rng = random.Random(1)
    rows, i = [], 0
    for platform, n_accounts in (("testplat_a", 60), ("testplat_b", 45)):
        for a in range(n_accounts):
            for _ in range(3):
                rows.append(_row(i, platform, f"{platform}-u{a}", f"{rng.choice(TEMPLATES)} #{i}", rng.randint(0, 3000)))
                i += 1
    for k in range(5):  # 5 comptes, même texte, dans la même fenêtre de 5 minutes, 2 fois
        for rep in range(2):
            rows.append(_row(i, "testplat_a", f"coord-{k}", COORD_TEXT, 100 + 300 * rep + k))
            i += 1
    for _ in range(3):  # un compte qui répète trois fois le même texte
        rows.append(_row(i, "testplat_b", "repeteur", "TEST البام فاسدين نفس النص", 50))
        i += 1
    rows.append(_row(i, "testplat_b", "spammeur", "TEST تابعوني على انستغرام whatsapp", 10))
    rows.append(dict(rows[0]))  # doublon technique (même comment_id)
    raw_dir.mkdir(parents=True)
    with open(raw_dir / "synthetique.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def test_chaine_complete(tmp_path):
    n = make_raw(tmp_path / "raw")
    work = tmp_path / "work"
    rep = clean_dedup.build(str(tmp_path / "raw"), str(work))
    assert rep["n_brut"] == n
    assert rep["retires_doublons_techniques"] == 1
    assert rep["retires_repetitions_meme_compte"] == 2 + 5  # répéteur + 2e texte identique des comptes coordonnés
    assert rep["retires_spam"] == 1
    assert rep["marques_copier_coller"] == 5

    coordination.main(str(work / "dataset_dedup_technique.jsonl"), str(work / "dataset_nettoye.jsonl"), str(work))
    acc = pd.read_csv(work / "comptes_coordination.csv")
    coord = acc[acc["acct"].str.contains(pseudonymize("testplat_a", "coord-0"))]
    assert coord["probabilite_coordination"].iloc[0] in ("moyenne", "elevee")
    rep_acct = acc[acc["acct"].str.contains(pseudonymize("testplat_b", "repeteur"))]
    assert "rafale" in rep_acct["indices"].iloc[0]  # même texte sous 3 publications
    organic = acc[~acc["indices"].fillna("").str.contains("sync|rafale")]
    # des phrases gabarits partagées ne suffisent pas à rendre un compte suspect
    assert (organic["probabilite_coordination"] == "faible").all()

    classify.main(str(work / "dataset_nettoye_coord.jsonl"), str(work / "dataset_classe.jsonl"))
    analyze_opinion.run(str(work / "dataset_classe.jsonl"), str(tmp_path / "results"))
    res = tmp_path / "results"
    for name in ["opinion_par_plateforme_parti", "soutien_rejet_explicites", "credibilite",
                 "sensibilite_coordination", "credibilite_par_periode"]:
        assert (res / f"{name}.csv").exists(), name
    cred = pd.read_csv(res / "credibilite.csv")
    assert set(cred["plateforme"]) >= {"testplat_a", "testplat_b", "TOUTES"}
    sens = pd.read_csv(res / "sensibilite_coordination.csv")
    assert (sens["comptes_exclus"] == 6).all()  # 5 comptes synchronisés + le répéteur
