"""Analyse électorale sur les données publiées du dossier data/ : JSON standard, tests cohérents, figures."""
import json
from pathlib import Path

import analyze_elections

DATA = Path(__file__).resolve().parents[2] / "data"


def _refuse(const):
    raise ValueError(f"valeur non JSON : {const}")


def test_main_on_published_data(tmp_path):
    res = analyze_elections.main(str(DATA), str(tmp_path))

    # JSON standard : les valeurs manquantes sont null, jamais NaN ni Infinity
    text = (tmp_path / "analyse_electorale.json").read_text(encoding="utf-8")
    json.loads(text, parse_constant=_refuse)

    t = res["tests_circonscriptions"]
    assert 0 <= t["p_fisher_pjd_premier"] <= 1 and 0 <= t["p_mann_whitney"] <= 1
    assert "non aléatoire" in t["avertissement"]

    # indice de conversion = part des sièges / part des voix ; 0 pour une liste sans siège
    for r in res["indices_conversion"]:
        expected = r["part_sieges"] / r["part_voix"] if r["part_sieges"] else 0.0
        assert abs(r["indice"] - expected) < 1e-9

    for r in res["bulletins_nuls"]:
        assert r["votants"] == r["suffrages_valides"] + r["bulletins_nuls"]

    figures = sorted(p.name for p in (tmp_path / "figures").glob("*.png"))
    assert len(figures) == 5 and all((tmp_path / "figures" / f).stat().st_size > 0 for f in figures)
