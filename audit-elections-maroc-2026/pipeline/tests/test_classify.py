"""Tests du classifieur à règles.

ATTENTION : les phrases ci-dessous sont des cas de test SYNTHÉTIQUES écrits pour
vérifier la logique du code. Ce ne sont PAS des commentaires collectés et elles ne
doivent jamais entrer dans une analyse.
"""
import pytest

from classify import classify


def test_sarcasme_darija_flip():
    r = classify("واخا البام محبوب عند الشعب 😂😂")
    assert r["parties_direct"] == ["PAM"]
    assert r["sarcasm_flag"] is True
    assert r["sentiment_by_party"]["PAM"] in ("defavorable", "tres_defavorable")
    assert r["uncertain_flag"] is True


def test_felicitations_pjd():
    r = classify("مبروك للعدالة والتنمية، تستاهلو")
    assert r["parties_direct"] == ["PJD"]
    assert r["sentiment_by_party"]["PJD"] in ("favorable", "tres_favorable")
    assert r["sarcasm_flag"] is False


def test_accusation_fraude_achat():
    r = classify("الانتخابات مزورة والبام شرا الأصوات بالفلوس")
    assert "PAM" in r["parties_direct"]
    assert "R5" in r["cred_codes"] and "R6" in r["cred_codes"]
    assert r["cred_main"] == "R5"
    assert r["sentiment_by_party"]["PAM"] in ("defavorable", "tres_defavorable")


def test_incomprehension_fr():
    r = classify("Je ne comprends pas comment le PAM a gagné, c'est pas logique")
    assert r["parties_direct"] == ["PAM"]
    assert "R3" in r["cred_codes"]


def test_abstention():
    r = classify("ما صوتش هاد العام، كلهم بحال بحال")
    assert "R9" in r["cred_codes"]


def test_intention_vote_rni_moyen_avec_contexte():
    r = classify("غادي نصوت على الأحرار")
    assert ["VEUT_VOTER", "RNI"] in r["intentions"]


def test_rejet_apres_parti():
    r = classify("PAM dégage")
    assert ["REJETTE", "PAM"] in r["intentions"]
    assert r["sentiment_by_party"]["PAM"] == "tres_defavorable"


def test_positif_fr():
    r = classify("Bravo au RNI, victoire méritée")
    assert r["sentiment_by_party"]["RNI"] in ("favorable", "tres_favorable")


def test_negation_darija():
    r = classify("البيجيدي ماشي فاسدين")
    assert r["sentiment_by_party"]["PJD"] in ("favorable", "tres_favorable")


def test_reference_indirecte_pejorative():
    r = classify("تجار الدين رجعو للبرلمان")
    assert "PJD" in r["parties_indirect"]
    assert r["sentiment_global"] in ("defavorable", "tres_defavorable")


def test_acceptation():
    r = classify("النتيجة طبيعية، الشعب قال كلمته")
    assert r["cred_main"] == "R1"


def test_democratie_ironique_non_acceptation():
    r = classify("ديمقراطية حقيقية 😂😂 الشعب قال كلمته")
    assert "R1" not in r["cred_codes"]


def test_surprise():
    r = classify("مفاجأة كبيرة ولكن مبروك")
    assert "R2" in r["cred_codes"]


def test_mode_de_scrutin_et_notables():
    assert "R8" in classify("القاسم الانتخابي هو السبب")["cred_codes"]
    assert "R7" in classify("الأعيان هوما لي ربحو")["cred_codes"]


def test_spam():
    assert classify("تابعوني على انستغرام")["spam_flag"] is True


def test_aucun_parti_aucune_opinion():
    r = classify("الجو زوين اليوم فالرباط")
    assert r["party_main"] == "aucun"
    assert r["cred_main"] == "R10"


def test_independance_non_istiqlal():
    assert "PI" not in classify("عيد الاستقلال مبروك على المغاربة")["parties_direct"]


@pytest.mark.parametrize("txt,lang", [
    ("wach bzaf 3la lbam hadchi", "arabizi"),
    ("C'est une victoire pour le parti", "fr"),
    ("شنو هاد النتائج ديال الانتخابات", "ar-darija"),
    ("ⴰⵣⵓⵍ", "zgh"),
])
def test_langue(txt, lang):
    from common import guess_language
    assert guess_language(txt) == lang
