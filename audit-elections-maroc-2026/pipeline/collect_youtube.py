"""Collecte YouTube (vidéos + commentaires publics) via yt-dlp, sans clé d'API.

- recherche par requête (plan de requêtes : queries.py), vidéos publiées depuis le 1er août 2026 ;
- plafond de vidéos par requête ET par strate, pour ne pas laisser une strate dominer ;
- commentaires triés du plus récent au plus ancien (pas seulement les « top ») ;
- auteurs pseudonymisés dès la collecte ; reprise possible (vidéos déjà collectées ignorées).

Limite connue : YouTube donne des dates relatives (« il y a 2 jours ») ; yt-dlp en déduit un
horodatage approximatif -> published_at_approx = True. La coordination « à la minute » n'est
donc pas mesurable sur YouTube.

Usage : python collect_youtube.py ../data/plan_requetes.csv data_work/raw/youtube.jsonl \
            --videos-par-requete 15 --max-commentaires 2000 --max-par-strate 150
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yt_dlp

from common import now_iso, pseudonymize, write_jsonl

START = "20260801"


def search(query: str, n: int) -> list[dict]:
    opts = {"quiet": True, "skip_download": True, "extract_flat": True, "ignoreerrors": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearchdate{n}:{query}", download=False) or {}
    return [e for e in info.get("entries") or [] if e and e.get("id")]


def video_with_comments(video_id: str, max_comments: int) -> dict | None:
    opts = {
        "quiet": True, "skip_download": True, "getcomments": True, "ignoreerrors": True,
        "extractor_args": {"youtube": {"max_comments": [str(max_comments), "all", "200", "50"],
                                       "comment_sort": ["new"]}},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)


def to_rows(info: dict, query: str, stratum: str) -> list[dict]:
    upload = info.get("upload_date") or ""
    post_ts = datetime.strptime(upload, "%Y%m%d").replace(tzinfo=timezone.utc).isoformat() if upload else None
    rows = []
    for c in info.get("comments") or []:
        ts = c.get("timestamp")
        rows.append({
            "platform": "youtube", "source_type": "social",
            "post_id": info.get("id"), "post_url": info.get("webpage_url"),
            "post_title": info.get("title"), "post_author": info.get("channel") or info.get("uploader"),
            "post_published_at": post_ts,
            "comment_id": c.get("id"),
            "parent_comment_id": None if c.get("parent") in (None, "root") else c.get("parent"),
            "is_reply": c.get("parent") not in (None, "root"),
            "author_hash": pseudonymize("youtube", c.get("author_id") or c.get("author")),
            "author_created_at": None,
            "text": c.get("text"),
            "published_at": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None,
            "published_at_approx": True,
            "like_count": c.get("like_count"),
            "query": query, "sample_stratum": stratum,
            "collected_at": now_iso(), "collector": f"yt-dlp {yt_dlp.version.__version__}",
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--videos-par-requete", type=int, default=15)
    ap.add_argument("--max-commentaires", type=int, default=2000)
    ap.add_argument("--max-par-strate", type=int, default=150)
    ap.add_argument("--pause", type=float, default=2.0)
    a = ap.parse_args()

    out = Path(a.out)
    done = set()
    if out.exists():
        done = {json.loads(line)["post_id"] for line in out.open(encoding="utf-8")}
    per_stratum = Counter()
    log = out.with_suffix(".log.jsonl")
    with open(a.plan, encoding="utf-8") as fh:
        plan = list(csv.DictReader(fh))
    for item in plan:
        stratum, query = item["strate"], item["requete"]
        for entry in search(query, a.videos_par_requete):
            if entry["id"] in done or per_stratum[stratum] >= a.max_par_strate:
                continue
            info = video_with_comments(entry["id"], a.max_commentaires)
            done.add(entry["id"])
            if not info or (info.get("upload_date") or "0") < START:
                continue
            n = write_jsonl(to_rows(info, query, stratum), out)
            per_stratum[stratum] += 1
            with log.open("a", encoding="utf-8") as lf:
                lf.write(json.dumps({"video": entry["id"], "query": query, "stratum": stratum,
                                     "n_comments": n, "at": now_iso()}, ensure_ascii=False) + "\n")
            time.sleep(a.pause)


if __name__ == "__main__":
    main()
