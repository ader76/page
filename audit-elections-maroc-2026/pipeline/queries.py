"""Plan de requêtes de recherche, avec la strate d'échantillonnage de chaque requête.

Les requêtes NEUTRES sont indispensables : chercher seulement « fraude » ou « تزوير »
fabriquerait un biais de sélection. Chaque publication collectée garde sa requête et sa
strate (colonnes query / sample_stratum) pour pouvoir pondérer ou exclure une strate.

Usage : python queries.py > requetes.csv
"""
from __future__ import annotations

import csv
import sys

NEUTRAL = [
    # arabe / darija / arabizi
    "نتائج الانتخابات", "نتائج الانتخابات 2026", "الانتخابات التشريعية 2026", "انتخابات 2026 المغرب",
    "نتائج انتخابات 23 شتنبر", "الانتخابات المغربية 2026", "مجلس النواب 2026", "نسبة المشاركة 2026",
    "الحملة الانتخابية 2026", "النتائج النهائية للانتخابات التشريعية", "وزير الداخلية نتائج الانتخابات",
    "شكون ربح الانتخابات", "نتيجة الانتخابات فالمغرب", "ntikhabat 2026", "ntikhabat lmaghrib",
    "natija dyal ntikhabat", "chkoun rbe7 ntikhabat",
    # français / anglais
    "résultats élections Maroc", "résultats législatives 2026", "législatives 2026 Maroc",
    "élections 23 septembre 2026", "Chambre des représentants 2026 résultats",
    "taux de participation législatives 2026", "Morocco election results 2026", "Morocco elections 2026",
]

PARTY_NAMES = {
    "PAM": ["البام", "الأصالة والمعاصرة", "الجرار", "التراكتور", "لقجع", "PAM", "lbam", "tracteur PAM"],
    "PJD": ["البيجيدي", "العدالة والتنمية", "المصباح", "بنكيران", "PJD", "Benkirane", "bijidi"],
    "RNI": ["الأحرار", "التجمع الوطني للأحرار", "الحمامة", "أخنوش", "RNI", "Akhannouch"],
    "PI": ["حزب الاستقلال", "الميزان", "نزار بركة", "Istiqlal"],
    "MP": ["الحركة الشعبية", "السنبلة", "أوزين", "Mouvement populaire"],
    "USFP": ["الاتحاد الاشتراكي", "لشكر", "USFP"],
    "PPS": ["التقدم والاشتراكية", "بنعبد الله", "PPS"],
    "UC": ["الاتحاد الدستوري", "Union constitutionnelle"],
}
NEUTRAL_PARTY_TEMPLATES = ["{p} الانتخابات 2026", "{p} 2026", "{p} مقاعد", "{p} élections 2026",
                           "{p} résultats législatives", "{p} sièges 2026"]
PRO_TEMPLATES = ["مبروك {p}", "فوز {p}", "انتصار {p}", "ندعم {p}", "félicitations {p}", "victoire {p}"]
CRITICAL_TEMPLATES = ["{p} فساد", "{p} تزوير", "{p} شراء الأصوات", "ضد {p}", "{p} fraude",
                      "{p} dégage"]
SPECIFIC = [
    ("critique_PAM", "كيفاش ربح البام"), ("neutre_PAM", "البام 97 مقعد"), ("neutre_PAM", "97 sièges PAM"),
    ("neutre_PJD", "عودة البيجيدي"), ("neutre_PJD", "retour du PJD"), ("critique_RNI", "ارحل أخنوش"),
    ("critique_RNI", "#ارحل_أخنوش"), ("neutre_RNI", "تراجع الأحرار"),
]
CREDIBILITY = [
    "تزوير الانتخابات", "شراء الأصوات", "شراء الذمم", "المال الانتخابي", "نتائج غير منطقية",
    "القاسم الانتخابي", "مقاطعة الانتخابات", "العزوف الانتخابي", "محاضر مكاتب التصويت",
    "fraude élections Maroc", "achat voix Maroc élections", "achat de voix législatives 2026",
    "boycott élections Maroc", "abstention Maroc 2026", "tazwir ntikhabat", "chraw l'aswat",
]
MEDIA = ["هسبريس", "Hespress", "شوف تيفي", "Chouf TV", "Le360", "2M", "Medi1TV", "SNRTnews", "أخبارنا",
         "Akhbarona", "كود", "Goud", "العمق", "Al3omk", "اليوم 24", "برلمان كوم", "هبة بريس", "LeSiteinfo",
         "TelQuel", "Médias24", "H24Info"]
MEDIA_TEMPLATES = ["{m} الانتخابات 2026", "{m} نتائج الانتخابات", "{m} élections 2026"]
CITIES = {  # grandes villes (urbain)
    "Casablanca": "الدار البيضاء", "Rabat": "الرباط", "Salé": "سلا", "Témara": "تمارة", "Tanger": "طنجة",
    "Fès": "فاس", "Meknès": "مكناس", "Marrakech": "مراكش", "Agadir": "أكادير", "Kénitra": "القنيطرة",
    "Oujda": "وجدة",
}
RURAL = {  # provinces majoritairement rurales (contrôle)
    "Taroudant": "تارودانت", "Azilal": "أزيلال", "Chichaoua": "شيشاوة", "Sidi Bennour": "سيدي بنور",
    "Taounate": "تاونات", "Zagora": "زاكورة", "Khénifra": "خنيفرة", "Al Haouz": "الحوز",
    "Errachidia": "الرشيدية", "Tata": "طاطا", "Guercif": "جرسيف", "Figuig": "فجيج",
}
PLACE_TEMPLATES = ["{ar} الانتخابات 2026", "{ar} نتائج الانتخابات", "{fr} législatives 2026",
                   "{fr} résultats élections"]


def build() -> list[dict]:
    q = [{"strate": "neutre", "requete": x} for x in NEUTRAL]
    for party, names in PARTY_NAMES.items():
        for n in names:
            q += [{"strate": f"neutre_{party}", "requete": t.format(p=n)} for t in NEUTRAL_PARTY_TEMPLATES]
            q += [{"strate": f"favorable_{party}", "requete": t.format(p=n)} for t in PRO_TEMPLATES]
            q += [{"strate": f"critique_{party}", "requete": t.format(p=n)} for t in CRITICAL_TEMPLATES]
    q += [{"strate": s, "requete": r} for s, r in SPECIFIC]
    q += [{"strate": "credibilite", "requete": x} for x in CREDIBILITY]
    q += [{"strate": "media", "requete": t.format(m=m)} for m in MEDIA for t in MEDIA_TEMPLATES]
    for strate, places in (("ville", CITIES), ("rural", RURAL)):
        for fr, arab in places.items():
            q += [{"strate": f"{strate}:{fr}", "requete": t.format(ar=arab, fr=fr)} for t in PLACE_TEMPLATES]
    seen, out = set(), []
    for item in q:
        if item["requete"] not in seen:
            seen.add(item["requete"])
            out.append(item)
    return out


if __name__ == "__main__":
    rows = build()
    w = csv.DictWriter(sys.stdout, fieldnames=["strate", "requete"])
    w.writeheader()
    w.writerows(rows)
    print(f"# {len(rows)} requêtes", file=sys.stderr)
