"""Outils statistiques : IC de Wilson, kappa de Cohen, bootstrap par grappes, corrélations."""
from __future__ import annotations

import math
from collections import Counter

import numpy as np
from scipy import stats


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    """Proportion et intervalle de confiance de Wilson à 95 %."""
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def cohen_kappa(a: list, b: list) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def cluster_bootstrap_share(values: np.ndarray, clusters: np.ndarray, B: int = 1000,
                            seed: int = 20260923) -> tuple[float, float, float]:
    """Part moyenne de `values` (0/1) avec IC 95 % par bootstrap en rééchantillonnant les comptes.

    Un compte très actif pèse sur la part par commentaire ; rééchantillonner les comptes
    (et non les commentaires) donne un intervalle honnête face à cette dépendance.
    """
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return (float("nan"), float("nan"), float("nan"))
    uniq, inv = np.unique(np.asarray(clusters), return_inverse=True)
    sums = np.bincount(inv, weights=values)
    counts = np.bincount(inv)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(uniq), size=(B, len(uniq)))
    boot = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    return (float(values.mean()), float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975)))


def correlations(x, y) -> dict:
    """Pearson ET Spearman avec p-valeurs et effectif ; ne dit rien de la causalité."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    if len(x) < 5:
        return {"n": int(len(x)), "statut": "DONNEES_INSUFFISANTES"}
    pr, pp = stats.pearsonr(x, y)
    sr, sp = stats.spearmanr(x, y)
    return {"n": int(len(x)), "pearson_r": float(pr), "pearson_p": float(pp),
            "spearman_rho": float(sr), "spearman_p": float(sp)}


def fmt_pct(p: float, lo: float | None = None, hi: float | None = None) -> str:
    if p != p:  # NaN
        return "n.d."
    if lo is None:
        return f"{100 * p:.1f} %"
    return f"{100 * p:.1f} % [{100 * lo:.1f} ; {100 * hi:.1f}]"
