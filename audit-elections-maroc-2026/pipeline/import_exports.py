"""Import d'exports de commentaires produits par des outils tiers (Facebook, Instagram,
TikTok, X, etc.) vers le schéma commun.

Facebook, Instagram, TikTok et X exigent une connexion ou un accès API pour lire les
commentaires. La voie réaliste est d'utiliser un outil autorisé (Meta Content Library
pour la recherche, API TikTok Research, API X, ou un export conforme aux conditions des
plateformes), puis d'importer le CSV/JSON ici. Les correspondances de colonnes ci-dessous
sont des GABARITS À ADAPTER aux en-têtes réels de l'export.

Usage : python import_exports.py export.csv facebook data_work/raw/facebook.jsonl \
            --mapping facebook_generique --post-url URL --strate neutre --requete "..."
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone

from common import now_iso, pseudonymize, write_jsonl

MAPPINGS = {
    # clé du schéma : nom de colonne dans l'export
    "facebook_generique": {"comment_id": "comment_id", "author": "author_id", "text": "text",
                           "published_at": "created_time", "like_count": "like_count",
                           "parent_comment_id": "parent_id", "post_id": "post_id", "post_url": "post_url"},
    "instagram_generique": {"comment_id": "id", "author": "username", "text": "text",
                            "published_at": "timestamp", "like_count": "like_count",
                            "parent_comment_id": "parent_id", "post_id": "media_id", "post_url": "permalink"},
    "tiktok_generique": {"comment_id": "cid", "author": "uniqueId", "text": "text",
                         "published_at": "createTimeISO", "like_count": "diggCount",
                         "parent_comment_id": "repliesToId", "post_id": "videoId", "post_url": "videoWebUrl",
                         "author_created_at": "authorCreateTime"},
    "x_generique": {"comment_id": "id", "author": "author_id", "text": "text", "published_at": "created_at",
                    "like_count": "like_count", "parent_comment_id": "in_reply_to_id",
                    "post_id": "conversation_id", "post_url": "url", "author_created_at": "author_created_at"},
}


def _iso(v):
    if v in (None, ""):
        return None
    if str(v).isdigit():  # epoch
        return datetime.fromtimestamp(int(v), tz=timezone.utc).isoformat()
    return str(v)


def load(path: str) -> list[dict]:
    if path.endswith(".json") or path.endswith(".jsonl"):
        with open(path, encoding="utf-8") as fh:
            txt = fh.read().strip()
        return json.loads(txt) if txt.startswith("[") else [json.loads(x) for x in txt.splitlines() if x]
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("platform")
    ap.add_argument("out")
    ap.add_argument("--mapping", required=True, choices=sorted(MAPPINGS))
    ap.add_argument("--post-url", default="")
    ap.add_argument("--post-title", default="")
    ap.add_argument("--post-author", default="")
    ap.add_argument("--strate", default="")
    ap.add_argument("--requete", default="")
    a = ap.parse_args()
    m = MAPPINGS[a.mapping]
    rows = []
    for r in load(a.src):
        g = lambda key: r.get(m.get(key, ""), None)  # noqa: E731
        rows.append({
            "platform": a.platform, "source_type": "social",
            "post_id": g("post_id") or a.post_url, "post_url": g("post_url") or a.post_url,
            "post_title": a.post_title, "post_author": a.post_author, "post_published_at": None,
            "comment_id": g("comment_id"), "parent_comment_id": g("parent_comment_id"),
            "is_reply": bool(g("parent_comment_id")),
            "author_hash": pseudonymize(a.platform, g("author")),
            "author_created_at": _iso(g("author_created_at")),
            "text": g("text"), "published_at": _iso(g("published_at")), "published_at_approx": False,
            "like_count": g("like_count"), "query": a.requete, "sample_stratum": a.strate,
            "collected_at": now_iso(), "collector": f"import:{a.mapping}",
        })
    print(write_jsonl(rows, a.out), "lignes importées")


if __name__ == "__main__":
    main()
