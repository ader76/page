"""Dictionnaire des partis, du sentiment, du sarcasme et des codes de crédibilité.

Toutes les expressions sont écrites sous forme naturelle puis normalisées au
chargement avec common.normalize (alifs unifiés, ة->ه, ى->ي, minuscules, sans accents).
Les motifs arabes acceptent les proclitiques usuels (و ف ب ل ك د + article).

Poids : "fort" = suffisant seul ; "moyen" = compte si le commentaire contient aussi
un indice électoral (ELECTION_CONTEXT) ; "indirect" = référence indirecte au parti
(péjoratif, dirigeant historique, trope), comptée à part.
"""
from __future__ import annotations

import re

from common import normalize

AR_PREFIX = r"(?:وال|بال|فال|كال|دال|لل|ال|و|ب|ل|ف|د|ك)?"
# lettres arabes uniquement (la ponctuation arabe « ، ؛ ؟ » n'est pas une lettre)
AR_LETTERS = "\u0621-\u064A\u066E-\u06D3\u06FA-\u06FF"
AR_END = rf"(?![{AR_LETTERS}\w])"
AR_START = rf"(?<![{AR_LETTERS}\w])"


ARTICLE = r"(?:وال|بال|فال|كال|دال|لل|ال)"


def ar(stem: str, prefix: bool = True, suffix: str = "") -> str:
    """Motif arabe borné : proclitiques optionnels + radical + suffixe optionnel.

    Un radical commençant par l'article (ال...) est reconnu aussi sous ses formes
    liées : لل، وال، بال، فال، كال، دال (ex. « للعدالة والتنمية »).
    """
    stem = normalize(stem)
    lead = AR_PREFIX if prefix else ""
    if prefix and stem.startswith("ال"):
        lead, stem = ARTICLE, stem[2:]
    stem = r"\s*".join(re.escape(part) for part in stem.split(" "))
    return AR_START + lead + stem + (f"(?:{suffix})?" if suffix else "") + AR_END


def lat(pattern: str) -> str:
    """Motif latin borné (appliqué au texte normalisé : minuscules, sans accents)."""
    return r"(?<![a-z0-9])" + pattern + r"(?![a-z0-9])"


# ---------------------------------------------------------------------------
# PARTIS
# ---------------------------------------------------------------------------
PARTIES: dict[str, dict[str, list[str]]] = {
    "PAM": {
        "fort": [
            ar("الاصاله والمعاصره"), ar("الاصاله و المعاصره"),
            ar("بام", suffix="يين|يون|ي|اوي|اويين"),
            ar("جرار"), ar("تراكتور"), ar("طراكتور"), ar("تركتور"), ar("تراكطور"),
            ar("لقجع"), ar("فوزي لقجع"),
            lat(r"pam"), lat(r"p\.a\.m\.?"), lat(r"authenticite\s*(?:et|&)\s*modernite"),
            lat(r"l?bam"), lat(r"el\s?bam"), lat(r"tracteur"), lat(r"tractor"), lat(r"trakt(?:eu)?r"),
            lat(r"le?kjaa?"), lat(r"lqjaa?"), lat(r"fouzi\s+lekjaa"),
        ],
        "moyen": [
            ar("المنصوري"), ar("وهبي", prefix=False), ar("بنسعيد", prefix=False),
            lat(r"mansouri"), lat(r"ouahbi|wahbi"), lat(r"bensaid"),
        ],
        "indirect": [
            ar("حزب الدوله"), ar("حزب الاداره"), ar("الوافد الجديد"), ar("الهمه"),
            lat(r"parti\s+de\s+l'?(?:administration|etat)"), lat(r"el\s?himma"),
        ],
    },
    "RNI": {
        "fort": [
            ar("التجمع الوطني للاحرار"), ar("اخنوش"), ar("عزيز اخنوش"), ar("الطالبي العلمي"),
            lat(r"rni"), lat(r"r\.n\.i\.?"), lat(r"rassemblement\s+national\s+des\s+independants"),
            lat(r"akh?an+ouch"), lat(r"a5an+ouch"), lat(r"akhnouch"), lat(r"talbi\s+alami"),
        ],
        "moyen": [
            ar("احرار", suffix="يين|ي"), ar("حمامه"), lat(r"l?'?ahrar"), lat(r"colombe"),
            lat(r"l?7mama"), lat(r"l?hmama"),
        ],
        "indirect": [
            ar("افريقيا"), ar("مول المازوط"), ar("مول الغاز"), lat(r"afriquia"),
            ar("حكومه اخنوش", prefix=False),
        ],
    },
    "PI": {
        "fort": [
            ar("حزب الاستقلال"), ar("استقلاليين"), ar("نزار بركه"),
            lat(r"istiqlal\w*"), lat(r"istiklal\w*"), lat(r"nizar\s+baraka"),
        ],
        "moyen": [
            AR_START + AR_PREFIX + r"(?<!عيد ال)(?<!عيد )استقلال" + AR_END,
            ar("ميزان"), lat(r"l?mizane?"),
        ],
        "indirect": [],
    },
    "PJD": {
        "fort": [
            ar("العداله والتنميه"), ar("العداله و التنميه"),
            ar("بيجيدي"), ar("بجيدي"), ar("بيجدي"), ar("بي جي دي"),
            ar("بنكيران"), ar("ابن كيران"), ar("بن كيران"), ar("بووانو"),
            lat(r"pjd"), lat(r"p\.j\.d\.?"), lat(r"justice\s+et\s+developpement"),
            lat(r"l?bijidi"), lat(r"pijidi"), lat(r"bjidi"),
            lat(r"benkiran+e?"), lat(r"bnkiran+e?"), lat(r"bn\s?kiran+e?"), lat(r"bouanou"),
        ],
        "moyen": [
            ar("مصباح"), ar("لامبه"), ar("لامبا"), ar("العثماني"), ar("الخلفي"), ar("الازمي"),
            ar("الرميد"),
            lat(r"l?misbah"), lat(r"lamba"), lat(r"lampe"), lat(r"othmani"), lat(r"el\s?khalfi"),
        ],
        "indirect": [
            ar("اخوان"), ar("خوانجي", suffix="ه|يه|يين"), ar("اخوانجي", suffix="ه|يه|يين"),
            ar("تجار الدين"), ar("الاسلاميين"), ar("الاسلاميون"),
            lat(r"islamistes?"), lat(r"khwanji\w*"), lat(r"khouanji\w*"),
            lat(r"marchands?\s+de\s+(?:la\s+)?religion"),
        ],
    },
    "USFP": {
        "fort": [ar("الاتحاد الاشتراكي"), ar("لشكر"), lat(r"usfp"), lat(r"lachgar"),
                 lat(r"ittihad\s+ichtiraki")],
        "moyen": [ar("ورده")],
        "indirect": [],
    },
    "PPS": {
        "fort": [ar("التقدم والاشتراكيه"), ar("التقدم و الاشتراكيه"), ar("نبيل بنعبد الله"),
                 ar("بنعبدالله"), lat(r"pps"), lat(r"(?:nabil\s+)?benabdallah")],
        "moyen": [],
        "indirect": [],
    },
    "MP": {
        "fort": [ar("الحركه الشعبيه"), ar("اوزين"), lat(r"mouvement\s+populaire"),
                 lat(r"ouzz?ine")],
        "moyen": [ar("سنبله"), lat(r"sonbola|snbla")],
        "indirect": [],
    },
    "UC": {
        "fort": [ar("الاتحاد الدستوري"), lat(r"union\s+constitutionnelle")],
        "moyen": [ar("حصان")],
        "indirect": [],
    },
    "AUTRE": {
        "fort": [
            ar("فيدراليه اليسار"), ar("تحالف اليسار"), ar("الاشتراكي الموحد"), ar("منيب"),
            ar("الحركه الديمقراطيه الاجتماعيه"), ar("جبهه القوى الديمقراطيه"), ar("حزب الانصاف"),
            ar("العدل والاحسان"), ar("العدل و الاحسان"),
            lat(r"mounib"), lat(r"fgd"), lat(r"psu"), lat(r"adl\s+wa?l?\s*ihsan\w*"),
            lat(r"federation\s+de\s+la\s+gauche"), lat(r"alliance\s+de\s+(?:la\s+)?gauche"),
        ],
        "moyen": [],
        "indirect": [],
    },
}

# Cibles non partisanes (suivies séparément, jamais attribuées à un parti)
NON_PARTY_TARGETS = {
    "GOUVERNEMENT": [ar("حكومه"), ar("الاغلبيه الحكوميه"), ar("التحالف الحكومي"),
                     lat(r"l?[7h]okouma"), lat(r"gouvernement")],
}

# Indices de contexte électoral (valident les termes "moyen")
ELECTION_CONTEXT = [
    AR_START + r"(?:[وفبل]?(?:ال)?|[نيت]|ك[نيت]|غادي\s*[نيت])صوت",
    ar("انتخابات"), ar("الانتخابات"), ar("انتخاب"), ar("صوت", suffix="ت|نا|و|وا"), ar("التصويت"),
    ar("مقعد", suffix="ا"), ar("مقاعد"), ar("البرلمان"), ar("النتائج"), ar("نتائج"), ar("الصناديق"),
    ar("حزب"), ar("الاحزاب"), ar("المرشح"), ar("لائحه"), ar("اللوائح"), ar("الحمله"), ar("الدائره"),
    lat(r"elections?"), lat(r"vot\w*"), lat(r"sieges?"), lat(r"parti\w*"), lat(r"scrutin"),
    lat(r"parlement"), lat(r"resultats?"), lat(r"ntikhabat"), lat(r"sawt\w*"),
    lat(r"legislatives?"), lat(r"urnes?"), lat(r"candidat\w*"),
]

# ---------------------------------------------------------------------------
# SENTIMENT
# ---------------------------------------------------------------------------
POSITIVE = [
    # arabe / darija
    "مبروك", "مبرووك", "الف مبروك", "تهانينا", "هنيئا", "تستاهلو", "تستاهلوها", "تستاهل",
    "يستاهل", "يستاهلو", "مستحق", "عن جداره", "برافو", "احسن حزب", "افضل حزب", "الله يعاونكم",
    "الله يعاونك", "الله يوفقكم", "الله يوفقك", "الله ينصركم", "الله يحفظكم", "الله يحفظك",
    "فخور", "فخورين", "نفتخر", "عاش", "تحيا", "نثق", "ثقتنا", "نزيه", "نظيف", "نظيفه", "كفاءه",
    "معقول", "مزيان", "زوين", "رجل دوله", "ناجح", "نجاح", "نساند", "ندعم", "داعمين", "معاك",
    "معاكم", "الى الامام", "كنبغيوه", "نبغيوه", "بالتوفيق", "موفق", "صادق", "صادقين", "شريف",
    "شرفاء", "خدام", "الله ينجحكم", "فرحانين", "فرحان", "ممتاز", "محبوب", "محبوبين",
    "الشعب يحب",
    # français
    "bravo", "felicitations", "felicitation", "merite", "bonne chance", "fier", "fiers",
    "competent", "honnete", "confiance", "je soutiens", "vive", "excellent", "bien joue",
    "serieux", "integre", "victoire meritee", "le meilleur",
    # arabizi / anglais
    "mabrouk", "mabrok", "mbrouk", "mbrok", "tsahlo", "tsahel", "brafo", "zwin", "mzyan", "mzian",
    "lah y3awnkom", "allah y3awnkom", "lah ynsrkom", "lah yhfdkom", "congrats", "congratulations",
    "well deserved", "good job", "proud",
]
NEGATIVE = [
    # arabe / darija
    "فاسد", "فاسدين", "فساد", "الفساد", "المفسدين", "مفسدين", "شفاره", "شفار", "شفارين",
    "لصوص", "حرامي", "حراميه", "سراق", "سرقو", "سرقتو", "نهب", "نهبو", "كذاب", "كذابين", "كذبو",
    "الكذب", "خونه", "خاين", "باعو", "دمرو", "خربو", "فاشل", "فاشلين", "الفشل", "خايب", "خايبين",
    "ارحل", "ارحلو", "ديكاج", "الله يلعن", "الله ياخد فيكم الحق", "الله ياخذ فيكم الحق",
    "حسبي الله", "حسبنا الله", "تفو", "العار", "حشومه", "مسخره", "ضحكو علينا", "ضحك علينا",
    "مابغيناش", "مابغيناكمش", "مابغيناهمش", "تجار الدين", "منافقين", "نفاق", "كارثه", "مصيبه",
    "وسخ", "حكره", "الحكره", "الغلاء", "غلاء", "قهرتونا", "قهرونا", "جوعتونا", "فقرتونا",
    "مصاصي الدماء", "عصابه", "مافيا", "انتهازي", "انتهازيين", "زبل", "بزناسه", "فقدنا الثقه",
    "لا ثقه", "ماكاينش الثقه", "مكاينش الثقه", "نكسه", "هزيمه", "خيبه", "خيبتونا",
    # français
    "corrompu", "corrompus", "corruption", "voleur", "voleurs", "honte", "honteux", "mensonge",
    "menteur", "menteurs", "degage", "catastrophe", "catastrophique", "incompetent",
    "incompetents", "arnaque", "escroc", "escrocs", "hypocrite", "hypocrites", "echec", "mafia",
    "pourri", "pourris", "decu", "decevant", "trahison", "traitre", "traitres", "vendus",
    # arabizi / anglais
    "chfara", "chfarin", "chefara", "lsous", "7ramiya", "khawana", "khayen", "fasidin", "fasad",
    "lfasad", "lah yakhod fikom l7a9", "7asbia lah", "7asbi lah", "tfo", "hchouma", "mskhra",
    "maskhara", "7gra", "l7gra", "lghla", "fachlin", "kdab", "kdabin", "corrupt", "thieves",
    "liars", "shame", "disgrace", "failure",
]
ACCUSATION_TERMS = ["تزوير", "مزوره", "زوروا", "زورو", "شراء الاصوات", "شراو الاصوات",
                    "بالفلوس", "المال الانتخابي", "مطبوخه", "مسرحيه", "fraude", "truque",
                    "truquee", "achat de voix", "tazwir", "mzawra", "rigged"]
STRONG_NEGATIVE = {"الله يلعن", "حسبي الله", "حسبنا الله", "الله ياخد فيكم الحق", "تفو", "عصابه",
                   "مافيا", "لصوص", "حراميه", "خونه", "degage", "ديكاج", "ارحل", "mafia"}
STRONG_POSITIVE = {"الف مبروك", "فخور", "فخورين", "نفتخر", "عاش", "تحيا", "victoire meritee",
                   "le meilleur", "احسن حزب"}

NEGATORS = [ar("ماشي", prefix=False), ar("مشي", prefix=False), ar("ليس", prefix=False),
            ar("لا", prefix=False), ar("غير", prefix=False), lat(r"pas"), lat(r"machi"),
            lat(r"mashi"), lat(r"not"), lat(r"jamais")]

# ---------------------------------------------------------------------------
# SARCASME
# ---------------------------------------------------------------------------
LAUGH_EMOJIS = "😂🤣😹🙃😏🙄🤡"
LAUGH_TOKENS = [ar("هه", prefix=False), ar("خخ", prefix=False), lat(r"(?:ha){2,}h?"), lat(r"hh+"),
                lat(r"lol"), lat(r"mdr"), lat(r"ptdr"), lat(r"xd")]
# fortes : suffisent à signaler une ironie probable ; faibles : seulement avec rire/emoji
IRONY_STRONG = ["الله يكثر من امثالكم", "زعما", "za3ma", "soi-disant", "soi disant"]
IRONY_WEAK = ["الشعب يحب", "محبوب", "محبوبين", "تبارك الله عليكم", "واخا", "انجازات",
              "الانجازات", "bien sur", "evidemment", "wakha", "ديمقراطيه", "نزيهه"]
IRONY_PHRASES = IRONY_STRONG + IRONY_WEAK

# ---------------------------------------------------------------------------
# CRÉDIBILITÉ DU SCRUTIN : R1..R9 (R10 = aucune opinion, par défaut)
# ---------------------------------------------------------------------------
CREDIBILITY: dict[str, dict[str, list[str]]] = {
    "R1": {  # accepte / considère le résultat normal
        "fort": ["نتيجه طبيعيه", "نتائج طبيعيه", "كان متوقع", "الشعب قال كلمته", "اختيار الشعب",
                 "الصناديق قالت كلمتها", "انتخابات نزيهه", "عرس ديمقراطي", "مبروك للفائزين",
                 "le peuple a choisi", "la democratie a parle", "resultat logique",
                 "elections transparentes", "resultat normal", "normal et logique"],
        "faible": ["منطقي", "متوقع", "نزيهه", "شفافه", "الشفافيه", "الديمقراطيه", "normal",
                   "logique", "previsible", "attendu", "transparent", "3adi", "mantiki"],
    },
    "R2": {  # surpris mais ne conteste pas
        "fort": ["ما توقعتش", "ماتوقعتش", "ما كنتش متوقع", "je ne m'attendais pas",
                 "ma tw9e3tch", "ma twq3tch", "مفاجاه", "مفاجئ", "مفاجئه", "surprise",
                 "surpris", "surprenant", "inattendu"],
        "faible": ["صدمه", "غريب", "etonnant", "ghrib"],
    },
    "R3": {  # résultat jugé difficile à comprendre
        "fort": ["كيفاش ربح", "كيفاش فاز", "كيفاش جا", "مفهمتش", "ما فهمتش", "مافهمتش",
                 "غير منطقي", "غير منطقيه", "لا يعقل", "منين جابو", "شكون صوت", "واش معقول",
                 "comment est-ce possible", "incomprehensible", "pas logique", "illogique",
                 "qui a vote pour", "ma fhmtch", "mafhmtch", "chkoun sawt", "wach m3qoul"],
        "faible": ["كيفاش", "مستحيل", "kifach", "kifash", "impossible"],
    },
    "R4": {  # soupçonne des irrégularités
        "fort": ["مشكوك", "مريب", "مشبوه", "مشبوهه", "خروقات", "تلاعب", "التلاعب", "تجاوزات",
                 "المحاضر", "رفض تسليم", "irregularites", "irregularite", "douteux", "louche"],
        "faible": ["شكوك", "خرق", "المقدم", "الشيخ", "القايد", "المحضر", "suspect", "pas clair",
                   "proces-verbal", "pv"],
    },
    "R5": {  # affirme fraude / manipulation
        "fort": ["تزوير", "التزوير", "مزوره", "زوروا", "زورو", "مطبوخه", "طبخو", "الطبخه",
                 "مفبركه", "مسرحيه", "المسرحيه", "مخدومه", "مصنوعه", "محسومه مسبقا",
                 "معروفه مسبقا", "الدوله اختارت", "المخزن اختار", "الداخليه اختارت", "خريطه مرسومه",
                 "fraude", "frauduleux", "truque", "truquee", "truquees", "mascarade",
                 "piece de theatre", "deja decide", "tbikh", "mtboukha", "mkhdouma", "mkhdoum",
                 "makhdoum", "mzawra",
                 "tazwir", "rigged", "fraud"],
        "faible": ["مزور", "طبخه", "مرسومه", "المخزن", "هندسه", "manipulation", "manipule",
                   "theatre", "makhzen"],
    },
    "R6": {  # évoque l'achat de voix
        "fort": ["شراء الاصوات", "شراء الذمم", "المال الانتخابي", "المال الحرام", "بالفلوس",
                 "باعو اصواتهم", "باعو صوتهم", "بيع الاصوات", "شراو الاصوات", "200 درهم",
                 "100 درهم", "achat de voix", "achat des voix", "vote achete", "votes achetes",
                 "vote buying", "chraw l'aswat"],
        "faible": ["الفلوس", "فلوس", "درهم", "الدراهم", "القفه", "القفف", "قفه", "الرشوه", "رشوه",
                   "رشاوي", "شراو", "خلصوهم", "argent", "billets", "dirhams", "lflous", "flous",
                   "chraw", "9ffa", "l9ffa"],
    },
    "R7": {  # clientélisme / notables
        "fort": ["الاعيان", "الزبونيه", "المحسوبيه", "مول الشكاره", "اصحاب الشكاره",
                 "العائلات النافذه", "notables", "clientelisme", "moul chkara"],
        "faible": ["اعيان", "زبونيه", "القبيله", "القبليه", "النفوذ", "الشكاره", "reseaux",
                   "3ayan", "chkara"],
    },
    "R8": {  # découpage / mode de scrutin
        "fort": ["القاسم الانتخابي", "التقطيع الانتخابي", "نمط الاقتراع", "quotient electoral",
                 "mode de scrutin", "systeme electoral", "loi electorale", "decoupage electoral"],
        "faible": ["القاسم", "التقطيع", "العتبه", "quotient", "decoupage", "seuil", "l9asim"],
    },
    "R9": {  # évoque l'abstention
        "fort": ["المقاطعه", "مقاطعين", "قاطعت", "قاطعنا", "ما صوتش", "ماصوتش", "ماصوتتش",
                 "ما مشيتش نصوت", "ما غاديش نصوت", "ماغاديش نصوت", "العزوف", "نسبه المشاركه",
                 "abstention", "boycott", "je n'ai pas vote", "taux de participation",
                 "ma sawtch", "ma mchitch", "boycotti", "mqat3in"],
        "faible": ["مقاطعه", "عزوف", "المشاركه ضعيفه", "participation", "pas vote"],
    },
}
CRED_MACRO = {
    "R1": "ACCEPTE", "R2": "SURPRISE", "R3": "INCOMPREHENSION", "R4": "DOUTE",
    "R5": "ACCUSATION", "R6": "ACCUSATION", "R7": "ACCUSATION", "R8": "STRUCTUREL",
    "R9": "STRUCTUREL", "R10": "AUCUNE",
}
# priorité pour un code principal unique (du plus grave au plus neutre)
CRED_PRIORITY = ["R5", "R6", "R4", "R7", "R3", "R2", "R8", "R9", "R1", "R10"]

# ---------------------------------------------------------------------------
# INTENTIONS EXPLICITES (reliées au parti mentionné dans la fenêtre qui suit)
# ---------------------------------------------------------------------------
INTENTIONS = {
    "A_VOTE": [r"صوتت", r"صوتنا", r"عطيت\s*صوتي", r"منحت\s*صوتي", r"صوتي\s*مشى",
               r"j'?ai\s+vote", r"on\s+a\s+vote", r"nous\s+avons\s+vote", r"i\s+voted",
               r"sawtt", r"sawtna", r"3tit\s+sawti"],
    "VEUT_VOTER": [r"غادي\s*نصوت\w*", r"سانصوت", r"ساصوت", r"سنصوت", r"صوتي\s*غادي",
                   r"je\s+vais\s+voter", r"je\s+voterai", r"nous\s+voterons", r"i\s+will\s+vote",
                   r"ghadi\s+nsawt\w*"],
    "SOUTIENT": [r"كنساند", r"نساند", r"كندعم", r"ندعم", r"داعم\w*", r"مساند\w*",
                 r"je\s+soutiens", r"kansand", r"nda3m"],
    "REJETTE": [r"مابغيناش", r"ما\s*بغيناش", r"لن\s*اصوت", r"ماغاديش\s*نصوت", r"ما\s*غاديش\s*نصوت",
                r"(?<![؀-ۿ])لا\s*ل", r"ارحل\w*", r"ديكاج", r"degage", r"plus\s+jamais",
                r"mabghinach", r"never\s+again"],
}

# ---------------------------------------------------------------------------
# SPAM
# ---------------------------------------------------------------------------
SPAM = ["واتساب", "واتس اب", "للبيع", "اتصل على", "تابعوني", "اشترك", "whatsapp", "promo",
        "gagner de l'argent", "crypto", "bitcoin", "abonne-toi", "abonnez-vous", "subscribe",
        "follow me", "check my", "lien en bio", "link in bio", "telegram", "تليجرام"]


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------
def _phrase(p: str) -> str:
    """Phrase simple -> motif borné (arabe ou latin selon l'écriture)."""
    n = normalize(p)
    if re.search(r"[؀-ۿ]", n):
        return ar(n, prefix=True)
    return lat(r"\s+".join(re.escape(w) for w in n.split(" ")))


def compile_list(items: list[str], raw: bool = False) -> list[re.Pattern]:
    return [re.compile(i if raw else _phrase(i)) for i in items]


COMPILED_PARTIES = {
    party: {level: [re.compile(p) for p in pats] for level, pats in levels.items()}
    for party, levels in PARTIES.items()
}
COMPILED_NON_PARTY = {k: [re.compile(p) for p in v] for k, v in NON_PARTY_TARGETS.items()}
COMPILED_CONTEXT = [re.compile(p) for p in ELECTION_CONTEXT]
COMPILED_POS = [(p, re.compile(_phrase(p))) for p in POSITIVE]
COMPILED_NEG = [(p, re.compile(_phrase(p))) for p in NEGATIVE]
COMPILED_NEGATORS = [re.compile(p) for p in NEGATORS]
COMPILED_LAUGH = [re.compile(p) for p in LAUGH_TOKENS]
COMPILED_IRONY = compile_list(IRONY_PHRASES)
COMPILED_IRONY_STRONG = compile_list(IRONY_STRONG)
COMPILED_ACCUSATION = [(p, re.compile(_phrase(p))) for p in ACCUSATION_TERMS]
COMPILED_CRED = {
    code: {level: compile_list(pats) for level, pats in levels.items()}
    for code, levels in CREDIBILITY.items()
}
COMPILED_INTENTIONS = {k: [re.compile(p) for p in v] for k, v in INTENTIONS.items()}
COMPILED_SPAM = compile_list(SPAM)
STRONG_NEGATIVE_N = {normalize(x) for x in STRONG_NEGATIVE}
STRONG_POSITIVE_N = {normalize(x) for x in STRONG_POSITIVE}
