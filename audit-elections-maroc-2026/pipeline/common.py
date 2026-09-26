"""Schéma commun, normalisation, pseudonymisation, périodes et langue.

Toutes les sources (YouTube, Reddit, sites de médias, exports tiers) sont
converties vers le même schéma de colonnes (COLUMNS) avant nettoyage.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Maroc : UTC+1 hors Ramadan (Ramadan 2026 : février-mars, donc UTC+1 en août-septembre).
MAROC_TZ = timezone(timedelta(hours=1))

COLUMNS = [
    "platform",            # youtube, reddit, facebook, tiktok, instagram, x, hespress, ...
    "source_type",         # social | media_site
    "post_id",
    "post_url",
    "post_title",
    "post_author",         # éditeur de la publication (média, page, influenceur) : non pseudonymisé
    "post_published_at",   # ISO 8601 UTC
    "comment_id",
    "parent_comment_id",   # vide si commentaire de premier niveau
    "is_reply",
    "author_hash",         # identifiant de compte pseudonymisé (sel local non versionné)
    "author_created_at",   # date de création du compte si la plateforme la fournit
    "text",
    "published_at",        # ISO 8601 UTC
    "published_at_approx", # True si horodatage relatif/approximatif (ex. "il y a 2 jours")
    "like_count",
    "query",               # requête de recherche ayant mené à la publication
    "sample_stratum",      # strate d'échantillonnage (neutre, pro_PAM, critique_PAM, ...)
    "collected_at",
    "collector",           # outil + version
]

PERIODS = [
    # (code, début inclus, fin incluse) en heure marocaine
    ("P1", datetime(2026, 8, 1, tzinfo=MAROC_TZ), datetime(2026, 8, 31, 23, 59, 59, tzinfo=MAROC_TZ)),
    ("P2", datetime(2026, 9, 1, tzinfo=MAROC_TZ), datetime(2026, 9, 22, 23, 59, 59, tzinfo=MAROC_TZ)),
    ("P3", datetime(2026, 9, 23, tzinfo=MAROC_TZ), datetime(2026, 9, 23, 23, 59, 59, tzinfo=MAROC_TZ)),
    ("P4", datetime(2026, 9, 24, tzinfo=MAROC_TZ), datetime(2026, 9, 26, 23, 59, 59, tzinfo=MAROC_TZ)),
    ("P5", datetime(2026, 9, 27, tzinfo=MAROC_TZ), datetime(2100, 1, 1, tzinfo=MAROC_TZ)),
]


def assign_period(iso_ts: str | None) -> str:
    """Retourne P1..P5, 'HORS' (avant le 1er août) ou 'INCONNU'."""
    if not iso_ts:
        return "INCONNU"
    try:
        ts = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
    except ValueError:
        return "INCONNU"
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    ts = ts.astimezone(MAROC_TZ)
    for code, start, end in PERIODS:
        if start <= ts <= end:
            return code
    return "HORS"


# --------------------------------------------------------------------------
# Pseudonymisation
# --------------------------------------------------------------------------
_SALT_FILE = Path(os.environ.get("AUDIT_SALT_FILE", Path(__file__).resolve().parent.parent / ".salt"))


def _salt() -> str:
    env = os.environ.get("AUDIT_SALT")
    if env:
        return env
    if _SALT_FILE.exists():
        return _SALT_FILE.read_text().strip()
    value = secrets.token_hex(32)
    _SALT_FILE.write_text(value)
    return value


def pseudonymize(platform: str, author_id: str | None) -> str:
    """Hachage salé et tronqué : stable entre exécutions, non réversible sans le sel."""
    if not author_id:
        return ""
    digest = hashlib.sha256(f"{_salt()}|{platform}|{author_id}".encode("utf-8")).hexdigest()
    return digest[:16]


# --------------------------------------------------------------------------
# Normalisation du texte (arabe, darija, arabizi, français)
# --------------------------------------------------------------------------
_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TATWEEL = "ـ"
_URL = re.compile(r"https?://\S+|www\.\S+")
_MENTION = re.compile(r"@[\w.\-]+")
_REPEAT = re.compile(r"(.)\1{2,}")
_SPACES = re.compile(r"\s+")
_ARABIC_CHARS = re.compile("[\u0621-\u064A\u066E-\u06D3\u06FA-\u06FF]")
_LATIN_CHARS = re.compile(r"[A-Za-zÀ-ÿ]")
_TIFINAGH = re.compile(r"[ⴰ-⵿]")
# Emojis et pictogrammes : plages principales
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF]"
)

_AR_MAP = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
    "ى": "ي", "ئ": "ي", "ؤ": "و", "ة": "ه",
    "گ": "ك", "ڭ": "ك", "ڤ": "ف", "پ": "ب",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
})


def normalize(text: str, keep_emojis: bool = True) -> str:
    """Normalisation utilisée par le classifieur et la déduplication.

    - supprime diacritiques arabes et tatweel, unifie alifs/ya/ta marbuta ;
    - minuscules, suppression des accents latins ;
    - URL et @mentions remplacées par des jetons ;
    - répétitions de 3+ caractères réduites à 2 ("ههههه" -> "هه", "bravooo" -> "bravoo").
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", str(text))
    t = _URL.sub(" _url_ ", t)
    t = _MENTION.sub(" _mention_ ", t)
    t = _TASHKEEL.sub("", t).replace(_TATWEEL, "")
    t = t.translate(_AR_MAP).lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    if not keep_emojis:
        t = EMOJI_RE.sub(" ", t)
    t = _REPEAT.sub(r"\1\1", t)
    return _SPACES.sub(" ", t).strip()


# --------------------------------------------------------------------------
# Détection de langue (heuristique, documentée comme telle)
# --------------------------------------------------------------------------
DARIJA_AR_MARKERS = {
    "ديال", "ديالهم", "ديالنا", "ماشي", "بزاف", "واش", "كيفاش", "علاش", "دابا", "غادي",
    "كاين", "كاينه", "ماكاينش", "مكاينش", "هادشي", "هاد", "هادو", "شنو", "اشنو", "فين", "خاص",
    "بغيت", "بغينا", "مابغيناش", "كيقول", "راه", "والو", "زعما", "حيت", "مزيان", "خايب",
    "صافي", "واخا", "كنصوتو", "صوتو", "شي", "ولا", "داك", "ديك", "هادي", "ليهم", "عليهم",
    "كيبغيو", "كيدير", "دار", "دارو", "غير", "باش", "مع", "حنا", "نتوما", "هوما",
}
ARABIZI_MARKERS = {
    "wach", "wech", "bzaf", "bzzaf", "dyal", "dial", "hadchi", "hadshi", "makaynch", "makaynsh",
    "mabghinach", "khasna", "ghadi", "kayn", "kayna", "3lach", "3lash", "kifach", "kifash",
    "nta", "nti", "howa", "hiya", "dima", "safi", "wallah", "khouya", "lhokouma", "l7okouma",
    "ana", "7na", "hna", "chno", "achno", "fin", "daba", "wakha", "zwin", "mzyan", "mzian",
    "machi", "walou", "walo", "bghit", "bghina", "sawt", "sawtt", "sawtna", "ntikhabat",
    "l3adala", "lbam", "l7amama", "hmama", "7mama", "chfara", "7ramiya", "3ayan", "tbikh",
}
FR_STOP = {"le", "la", "les", "des", "est", "pas", "que", "qui", "pour", "une", "dans", "sur",
           "avec", "ce", "sont", "c'est", "je", "vous", "nous", "ils", "mais", "du", "au", "aux"}
EN_STOP = {"the", "is", "and", "of", "to", "in", "that", "for", "this", "are", "was", "with",
           "they", "have", "not", "it", "you", "we"}
AMAZIGH_LATIN_MARKERS = {"azul", "tanmmirt", "tamazight", "imazighen", "tamurt", "ayyur"}

_ARABIZI_DIGIT = re.compile(r"[a-z][23579][a-z]|^[23579][a-z]|[a-z][23579]$")


def guess_language(text: str) -> str:
    """Retourne : ar-darija, ar-msa, arabizi, fr, en, zgh, mixte, indetermine."""
    if not text:
        return "indetermine"
    raw = str(text)
    if _TIFINAGH.search(raw):
        return "zgh"
    n_ar = len(_ARABIC_CHARS.findall(raw))
    n_lat = len(_LATIN_CHARS.findall(raw))
    norm = normalize(raw, keep_emojis=False)
    tokens = set(re.findall(r"[\w']+", norm))
    if n_ar == 0 and n_lat == 0:
        return "indetermine"
    if n_ar > 0 and n_lat > 0 and min(n_ar, n_lat) / max(n_ar, n_lat) > 0.3:
        return "mixte"
    if n_ar >= n_lat:
        return "ar-darija" if tokens & {normalize(m) for m in DARIJA_AR_MARKERS} else "ar-msa"
    if tokens & AMAZIGH_LATIN_MARKERS:
        return "zgh"
    arabizi_score = len(tokens & ARABIZI_MARKERS) + sum(1 for tok in tokens if _ARABIZI_DIGIT.search(tok))
    fr_score = len(tokens & FR_STOP)
    en_score = len(tokens & EN_STOP)
    best = max(("arabizi", arabizi_score), ("fr", fr_score), ("en", en_score), key=lambda x: x[1])
    return best[0] if best[1] > 0 else "indetermine"


# --------------------------------------------------------------------------
# Entrées / sorties JSONL
# --------------------------------------------------------------------------
def write_jsonl(rows, path: str | Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps({c: row.get(c) for c in COLUMNS}, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
