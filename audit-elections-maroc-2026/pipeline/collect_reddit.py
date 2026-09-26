"""Collecte Reddit (publications + commentaires publics) via les points d'accès JSON publics.

Sous-forums par défaut : r/Morocco, r/morocco, r/Maroc, r/Casablanca, r/Rabat, r/Darija.
Reddit limite fortement l'accès non authentifié ; si REDDIT_TOKEN (OAuth, application
« script ») est défini, les appels passent par oauth.reddit.com.
Les branches « more » (commentaires repliés) ne sont pas dépliées : limite documentée.

Usage : python collect_reddit.py ../data/plan_requetes.csv data_work/raw/reddit.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from common import now_iso, pseudonymize, write_jsonl

SUBS = ["Morocco", "morocco", "Maroc", "Casablanca", "Rabat", "Darija"]
START = datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp()
UA = "audit-elections-maroc-2026/1.0 (recherche academique)"


def _get(path: str, params: dict) -> dict | list:
    token = os.environ.get("REDDIT_TOKEN")
    base = "https://oauth.reddit.com" if token else "https://www.reddit.com"
    headers = {"User-Agent": UA}
    if token:
        headers["Authorization"] = f"bearer {token}"
    r = requests.get(base + path, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def flatten(children: list, post: dict, query: str, stratum: str, parent: str | None = None) -> list[dict]:
    rows = []
    for ch in children:
        if ch.get("kind") != "t1":
            continue
        d = ch["data"]
        rows.append({
            "platform": "reddit", "source_type": "social",
            "post_id": post["id"], "post_url": "https://www.reddit.com" + post["permalink"],
            "post_title": post.get("title"), "post_author": f"r/{post.get('subreddit')}",
            "post_published_at": datetime.fromtimestamp(post["created_utc"], tz=timezone.utc).isoformat(),
            "comment_id": d.get("id"), "parent_comment_id": parent, "is_reply": parent is not None,
            "author_hash": pseudonymize("reddit", d.get("author")), "author_created_at": None,
            "text": d.get("body"),
            "published_at": datetime.fromtimestamp(d["created_utc"], tz=timezone.utc).isoformat(),
            "published_at_approx": False, "like_count": d.get("score"),
            "query": query, "sample_stratum": stratum,
            "collected_at": now_iso(), "collector": "reddit-json",
        })
        replies = d.get("replies")
        if isinstance(replies, dict):
            rows += flatten(replies["data"]["children"], post, query, stratum, parent=d.get("id"))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--pause", type=float, default=2.0)
    a = ap.parse_args()
    out = Path(a.out)
    done = {json.loads(line)["post_id"] for line in out.open(encoding="utf-8")} if out.exists() else set()
    with open(a.plan, encoding="utf-8") as fh:
        plan = list(csv.DictReader(fh))
    for item in plan:
        for sub in SUBS:
            try:
                res = _get(f"/r/{sub}/search.json", {"q": item["requete"], "restrict_sr": 1,
                                                      "sort": "new", "t": "year", "limit": 100})
            except requests.RequestException as exc:
                print("erreur recherche", sub, item["requete"], exc)
                continue
            for p in res.get("data", {}).get("children", []):
                post = p["data"]
                if post["id"] in done or post["created_utc"] < START:
                    continue
                done.add(post["id"])
                try:
                    listing = _get(f"/comments/{post['id']}.json", {"limit": 500, "depth": 10, "sort": "new"})
                except requests.RequestException as exc:
                    print("erreur commentaires", post["id"], exc)
                    continue
                write_jsonl(flatten(listing[1]["data"]["children"], post, item["requete"], item["strate"]), out)
                time.sleep(a.pause)
            time.sleep(a.pause)


if __name__ == "__main__":
    main()
