"""Classifieur à règles : parti, sentiment (5 niveaux), intention, crédibilité R1-R10, sarcasme.

C'est une première passe transparente et reproductible. Sa qualité doit être mesurée
par validate.py sur un échantillon aléatoire relu (>= 500) ; si l'erreur dépasse 10 %,
on enrichit le dictionnaire ou on remplace par classify_llm.py puis on revalide.

Usage : python classify.py data_work/dataset_nettoye.jsonl data_work/dataset_classe.jsonl
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import lexicon as L
from common import EMOJI_RE, guess_language, normalize, read_jsonl

LABELS = {2: "tres_favorable", 1: "favorable", 0: "neutre", -1: "defavorable", -2: "tres_defavorable"}
POS_EMOJIS = set("👏💪🌹👍✌🥳🎉❤💚")
NEG_EMOJIS = set("👎😡🤬💩🤮😤😠")
CLAUSE_SPLIT = re.compile(
    r"[.!?؟،,;؛\n]+|\s(?:لكن|ولكن|بصح|walakin|mais|but|par contre)\s"
)


def _label(score: int) -> str:
    return LABELS[max(-2, min(2, score))]


def detect_parties(norm: str) -> tuple[list[tuple[str, str, int]], bool]:
    """Liste de (parti, niveau, position) ; les termes 'moyen' exigent un contexte électoral."""
    has_context = any(p.search(norm) for p in L.COMPILED_CONTEXT)
    hits: list[tuple[str, str, int]] = []
    for party, levels in L.COMPILED_PARTIES.items():
        for level, pats in levels.items():
            for pat in pats:
                for m in pat.finditer(norm):
                    hits.append((party, level, m.start()))
    has_strong = any(level == "fort" for _, level, _ in hits)
    kept = [h for h in hits if h[1] != "moyen" or has_context or has_strong]
    return sorted(kept, key=lambda h: h[2]), has_context


def _negated(clause: str, start: int) -> bool:
    window = clause[max(0, start - 15):start]
    return any(p.search(window) for p in L.COMPILED_NEGATORS)


def clause_score(clause: str) -> tuple[int, list[str]]:
    score, terms = 0, []
    for term, pat in L.COMPILED_POS:
        for m in pat.finditer(clause):
            w = 2 if normalize(term) in L.STRONG_POSITIVE_N else 1
            score += -w if _negated(clause, m.start()) else w
            terms.append("+" + term)
    for term, pat in L.COMPILED_NEG:
        for m in pat.finditer(clause):
            w = 2 if normalize(term) in L.STRONG_NEGATIVE_N else 1
            score += w if _negated(clause, m.start()) else -w
            terms.append("-" + term)
    for term, pat in L.COMPILED_ACCUSATION:
        if pat.search(clause):
            score -= 1
            terms.append("!" + term)
    score += sum(1 for ch in clause if ch in POS_EMOJIS) - sum(1 for ch in clause if ch in NEG_EMOJIS)
    return score, terms


def sarcasm_cue(raw: str, norm: str) -> bool:
    """Rire (emoji ou onomatopée) ou ironie forte ; l'ironie faible seule ne suffit pas."""
    laugh = any(ch in raw for ch in L.LAUGH_EMOJIS) or any(p.search(norm) for p in L.COMPILED_LAUGH)
    return laugh or any(p.search(norm) for p in L.COMPILED_IRONY_STRONG)


def credibility(norm: str, sarcastic: bool) -> list[str]:
    codes = []
    for code, levels in L.COMPILED_CRED.items():
        strong = sum(1 for p in levels.get("fort", []) if p.search(norm))
        weak = sum(1 for p in levels.get("faible", []) if p.search(norm))
        if strong >= 1 or weak >= 2:
            codes.append(code)
    if "R1" in codes and (sarcastic or {"R4", "R5", "R6"} & set(codes)):
        codes.remove("R1")  # "démocratie 😂" n'est pas une acceptation
    return codes or ["R10"]


def intentions(norm: str, party_hits: list[tuple[str, str, int]]) -> list[tuple[str, str | None]]:
    out = []
    positions = [(p, pos) for p, level, pos in party_hits if level in ("fort", "moyen", "indirect")]
    for kind, pats in L.COMPILED_INTENTIONS.items():
        for pat in pats:
            for m in pat.finditer(norm):
                after = [p for p, pos in positions if m.end() <= pos <= m.end() + 60]
                before = [p for p, pos in positions if m.start() - 40 <= pos < m.start()]
                target = after[0] if after else (before[-1] if kind == "REJETTE" and before else None)
                out.append((kind, target))
    return sorted(set(out), key=lambda x: (x[0], x[1] or ""))


def classify(text: str) -> dict:
    raw = text or ""
    norm = normalize(raw)
    party_hits, has_context = detect_parties(norm)
    direct = sorted({p for p, lvl, _ in party_hits if lvl != "indirect"})
    indirect = sorted({p for p, lvl, _ in party_hits if lvl == "indirect"} - set(direct))
    mentioned = direct + indirect
    non_party = sorted(k for k, pats in L.COMPILED_NON_PARTY.items() if any(p.search(norm) for p in pats))
    sarcastic_cue = sarcasm_cue(raw, norm)
    spam = any(p.search(norm) for p in L.COMPILED_SPAM)

    # Sentiment par proposition, attribué aux partis cités dans la proposition,
    # sinon au dernier parti cité avant elle, sinon au sentiment global.
    by_party: dict[str, int] = {}
    global_score, terms, offset = 0, [], 0
    sarcasm_flag = uncertain = False
    for clause in CLAUSE_SPLIT.split(norm):
        start = norm.find(clause, offset) if clause else offset
        offset = start + len(clause)
        if not clause.strip():
            continue
        score, t = clause_score(clause)
        terms += t
        ironic = any(p.search(clause) for p in L.COMPILED_IRONY)
        if sarcastic_cue and (score > 0 or ironic):
            score, sarcasm_flag, uncertain = -max(1, abs(score)), True, True
        global_score += score
        in_clause = sorted({p for p, lvl, pos in party_hits if start <= pos < start + len(clause)})
        if not in_clause:
            before = [p for p, lvl, pos in party_hits if pos < start]
            in_clause = [before[-1]] if before else (mentioned if len(mentioned) == 1 else [])
        for p in in_clause:
            by_party[p] = by_party.get(p, 0) + score
    if sarcastic_cue and global_score == 0 and any(p.search(norm) for p in L.COMPILED_IRONY):
        uncertain = True

    codes = credibility(norm, sarcastic_cue)
    main = next(c for c in L.CRED_PRIORITY if c in codes)
    return {
        "lang": guess_language(raw),
        "election_context": has_context,
        "parties_direct": direct,
        "parties_indirect": indirect,
        "party_main": (mentioned[0] if len(mentioned) == 1 else ("multiple" if mentioned else "aucun")),
        "non_party_targets": non_party,
        "sentiment_by_party": {p: _label(s) for p, s in sorted(by_party.items())},
        "sentiment_global": _label(global_score),
        "score_global": global_score,
        "intentions": [list(x) for x in intentions(norm, party_hits)],
        "cred_codes": codes,
        "cred_main": main,
        "cred_macro": L.CRED_MACRO[main],
        "sarcasm_flag": sarcasm_flag,
        "uncertain_flag": uncertain or (len(direct) > 1 and len(set(by_party.values())) > 1),
        "spam_flag": spam,
        "emoji_count": len(EMOJI_RE.findall(raw)),
        "matched_terms": terms[:20],
        "classifier": "rules-v1",
    }


def main(src: str, dst: str) -> None:
    rows = read_jsonl(src)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as fh:
        for row in rows:
            row.update(classify(row.get("text", "")))
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{len(rows)} commentaires classés -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
