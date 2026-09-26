"""Collecte des commentaires publics sur les sites de médias marocains.

ATTENTION : les sélecteurs CSS ci-dessous n'ont PAS pu être vérifiés pendant la
préparation de cet audit (accès réseau bloqué par la politique de l'environnement).
Avant toute collecte, lancer le mode --decouvrir sur 2-3 articles de chaque site,
corriger PROFILES, puis vérifier à la main que le nombre de commentaires extraits
correspond à celui affiché sur la page.

Usage :
  python collect_web_comments.py --decouvrir URL
  python collect_web_comments.py urls.csv data_work/raw/medias.jsonl
      (urls.csv : colonnes site,url,strate,requete)
"""
from __future__ import annotations

import argparse
import csv
import re
import time
from collections import Counter

import requests
from bs4 import BeautifulSoup

from common import now_iso, pseudonymize, write_jsonl

UA = "Mozilla/5.0 (audit-elections-maroc-2026; recherche academique)"
# Profils À VALIDER (hypothèses de structure) : block = un commentaire ; champs relatifs au bloc.
PROFILES = {
    "hespress": {"block": "li.comment, div.comment", "author": ".comment-author, .fn",
                 "date": "time, .comment-date", "text": ".comment-text, .comment-content, p",
                 "id_attr": "id"},
    "akhbarona": {"block": ".comment, .comment-item", "author": ".comment-author, .name",
                  "date": ".comment-date, time", "text": ".comment-text, .comment-body, p", "id_attr": "id"},
    "generique": {"block": "[class*=comment]", "author": "[class*=author], [class*=name]",
                  "date": "time, [class*=date]", "text": "p", "id_attr": "id"},
}
ARABIC = re.compile("[ء-ي]")


def fetch(url: str) -> BeautifulSoup:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def discover(url: str) -> None:
    """Affiche les classes CSS répétées qui contiennent du texte : aide à écrire un profil."""
    soup = fetch(url)
    counter = Counter()
    for tag in soup.find_all(True):
        cls = " ".join(tag.get("class") or [])
        if cls and len(tag.get_text(strip=True)) > 20:
            counter[f"{tag.name}.{cls}"] += 1
    for k, v in counter.most_common(40):
        print(f"{v:4d}  {k}")


def extract(url: str, site: str, query: str, stratum: str) -> list[dict]:
    prof = PROFILES.get(site, PROFILES["generique"])
    soup = fetch(url)
    title = soup.title.get_text(strip=True) if soup.title else None
    pub = soup.find("meta", {"property": "article:published_time"})
    rows = []
    for i, block in enumerate(soup.select(prof["block"])):
        text_el = block.select_one(prof["text"])
        text = text_el.get_text(" ", strip=True) if text_el else ""
        if not text:
            continue
        author_el = block.select_one(prof["author"])
        date_el = block.select_one(prof["date"])
        author = author_el.get_text(strip=True) if author_el else ""
        rows.append({
            "platform": site, "source_type": "media_site",
            "post_id": url, "post_url": url, "post_title": title, "post_author": site,
            "post_published_at": pub.get("content") if pub else None,
            "comment_id": block.get(prof["id_attr"]) or f"{url}#{i}",
            "parent_comment_id": None, "is_reply": False,
            # sur les sites de médias, seul le pseudonyme affiché est disponible
            "author_hash": pseudonymize(site, author) if author else "",
            "author_created_at": None, "text": text,
            "published_at": (date_el.get("datetime") if date_el and date_el.get("datetime") else None),
            "published_at_approx": not (date_el and date_el.get("datetime")),
            "like_count": None, "query": query, "sample_stratum": stratum,
            "collected_at": now_iso(), "collector": f"bs4-profile:{site}",
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--decouvrir")
    ap.add_argument("--pause", type=float, default=3.0)
    a = ap.parse_args()
    if a.decouvrir:
        discover(a.decouvrir)
        return
    with open(a.urls, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                n = write_jsonl(extract(row["url"], row["site"], row.get("requete", ""), row.get("strate", "")), a.out)
                print(n, row["url"])
            except requests.RequestException as exc:
                print("erreur", row["url"], exc)
            time.sleep(a.pause)


if __name__ == "__main__":
    main()
