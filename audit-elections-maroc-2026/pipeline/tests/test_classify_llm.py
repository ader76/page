"""Tests hors réseau de classify_llm.py (aucun appel API ; réponses simulées)."""
import json
from types import SimpleNamespace

import classify_llm as C


def _msg(payload, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=json.dumps(payload))])


def test_parametres_et_schema():
    p = C._params([{"row_id": 1, "text": "TEST", "post_title": "TEST"}])
    assert p["model"] == "claude-opus-5"
    assert p["output_config"]["format"]["type"] == "json_schema"
    assert p["system"][0]["cache_control"] == {"type": "ephemeral"}
    item = C.SCHEMA["properties"]["items"]["items"]
    assert item["additionalProperties"] is False and set(item["required"]) == set(item["properties"])


def test_analyse_reponse_simulee():
    chunk = [{"row_id": 7, "text": "TEST واخا البام محبوب 😂"}]
    payload = {"items": [{"id": "7", "parties": [{"party": "PAM", "reference": "directe", "sentiment": "defavorable"}],
                          "sentiment_global": "defavorable", "intentions": [{"type": "REJETTE", "party": "PAM"}],
                          "cred_codes": ["R10"], "sarcasm": True, "uncertain": False, "spam": False,
                          "rationale": "ironie"}]}
    out, issue = C.parse_message(_msg(payload), chunk)
    assert issue is None
    r = out["7"]
    assert r["party_main"] == "PAM" and r["sentiment_by_party"] == {"PAM": "defavorable"}
    assert r["intentions"] == [["REJETTE", "PAM"]] and r["sarcasm_flag"] is True
    assert r["classifier"].startswith("llm:claude-opus-5")


def test_refus_et_ids_manquants():
    chunk = [{"row_id": 1, "text": "a"}, {"row_id": 2, "text": "b"}]
    assert C.parse_message(_msg({}, stop="refusal"), chunk) == ({}, "refus")
    out, issue = C.parse_message(_msg({"items": []}), chunk)
    assert out == {} and issue == "ids_manquants:2"
