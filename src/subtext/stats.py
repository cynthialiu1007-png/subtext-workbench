"""Statistical helpers for module 7. Pure functions, unit-tested in tests/test_analysis.py."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats as sps

READ_SCORE = {"F": 2, "P": 1, "N": 0, "M": 0}


# ---------------------------------------------------------------- rubric Section 8

def rubric_metrics(e_cats: list, c_cats: list) -> dict:
    """Summary metrics of rubric Section 8. X is excluded from every denominator and reported."""
    e = [c for c in e_cats if c != "X"]
    c = [x for x in c_cats if x != "X"]
    n_e, n_c = len(e), len(c)
    cnt = {k: e.count(k) for k in "FPNM"}
    cnt.update({k: c.count(k) for k in "AO"})
    out = {"n_E": n_e, "n_C": n_c, "X_E": e_cats.count("X"), "X_C": c_cats.count("X"), "counts": cnt}
    if n_e:
        out["strict_read_rate"] = cnt["F"] / n_e
        out["lenient_read_rate"] = (cnt["F"] + cnt["P"]) / n_e
        out["mean_read_score"] = sum(READ_SCORE[k] for k in e) / n_e
        out["misread_rate"] = cnt["M"] / n_e
    if n_c:
        out["over_interpretation_rate"] = cnt["O"] / n_c
    if n_e and n_c:
        out["discrimination_index"] = out["lenient_read_rate"] - out["over_interpretation_rate"]
        out["d_prime"] = d_prime(cnt["F"] + cnt["P"], n_e, cnt["O"], n_c)
    return out


def d_prime(hits: int, n_signal: int, false_alarms: int, n_noise: int) -> float:
    """d' with the log-linear correction (Hautus, 1995), applied to every cell."""
    h = (hits + 0.5) / (n_signal + 1)
    f = (false_alarms + 0.5) / (n_noise + 1)
    return float(sps.norm.ppf(h) - sps.norm.ppf(f))


# ---------------------------------------------------------------- instability

def mean_pairwise_cosine_distance(vecs: list) -> float:
    """Vectors must be unit length. Returns nan for fewer than two vectors."""
    if len(vecs) < 2:
        return float("nan")
    a = np.asarray(vecs, dtype=float)
    sim = a @ a.T
    iu = np.triu_indices(len(a), k=1)
    return float(np.mean(1.0 - sim[iu]))


def mean_cross_cosine_distance(vecs_a: list, vecs_b: list) -> float:
    if not vecs_a or not vecs_b:
        return float("nan")
    a, b = np.asarray(vecs_a, dtype=float), np.asarray(vecs_b, dtype=float)
    return float(np.mean(1.0 - a @ b.T))


def tone_disagreement(tones: list) -> float:
    if not tones:
        return float("nan")
    return 1.0 - max(tones.count(t) for t in set(tones)) / len(tones)


def sample_sd(xs: list) -> float:
    return float(np.std(xs, ddof=1)) if len(xs) >= 2 else float("nan")


# ---------------------------------------------------------------- paired tests (RQ1)

def mcnemar_exact(e_err: list, c_err: list) -> dict:
    """Exact (binomial) McNemar test on paired binary outcomes."""
    b = sum(1 for x, y in zip(e_err, c_err) if x == 1 and y == 0)
    c = sum(1 for x, y in zip(e_err, c_err) if x == 0 and y == 1)
    p = 1.0 if b + c == 0 else float(sps.binomtest(min(b, c), b + c, 0.5).pvalue)
    return {"n_pairs": len(e_err), "E_error_only": b, "C_error_only": c, "p": p}


def rank_biserial_paired(d: list) -> float:
    """Matched-pairs rank-biserial correlation; zero differences dropped (as in Wilcoxon 'wilcox')."""
    d = np.asarray([x for x in d if x != 0], dtype=float)
    if len(d) == 0:
        return 0.0
    r = sps.rankdata(np.abs(d))
    return float((r[d > 0].sum() - r[d < 0].sum()) / r.sum())


def wilcoxon_paired(x: list, y: list) -> dict:
    d = [a - b for a, b in zip(x, y)]
    nz = [v for v in d if v != 0]
    if not nz:
        p = 1.0
    else:
        p = float(sps.wilcoxon(x, y, zero_method="wilcox", alternative="two-sided").pvalue)
    return {"n_pairs": len(d), "n_nonzero": len(nz), "median_difference": float(np.median(d)),
            "rank_biserial": rank_biserial_paired(d), "p": p}


# ---------------------------------------------------------------- AUC (RQ3)

def auc(scores: list, labels: list) -> float:
    """P(score of an error > score of a non-error), ties counted 1/2. nan if one class only."""
    s, y = np.asarray(scores, dtype=float), np.asarray(labels, dtype=int)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).sum()
    eq = (pos[:, None] == neg[None, :]).sum()
    return float((gt + 0.5 * eq) / (len(pos) * len(neg)))


# ---------------------------------------------------------------- bootstrap

def bootstrap_ci(units: list, stat, n_boot: int, seed: int, level: float = 0.95) -> dict:
    """Percentile bootstrap over units (pairs, segments or segment clusters).

    `stat` maps a list of units to a number. Resamples giving nan (e.g. one outcome class only)
    are skipped and counted.
    """
    rng = np.random.default_rng(seed)
    n = len(units)
    vals, skipped = [], 0
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        v = stat([units[i] for i in idx])
        if v is None or (isinstance(v, float) and math.isnan(v)):
            skipped += 1
        else:
            vals.append(v)
    if not vals:
        return {"low": None, "high": None, "n_boot": n_boot, "skipped": skipped}
    lo, hi = np.percentile(vals, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return {"low": float(lo), "high": float(hi), "n_boot": n_boot, "skipped": skipped}


# ---------------------------------------------------------------- agreement

def cohen_kappa(a: list, b: list, categories: list, score: dict | None = None) -> float:
    """Cohen's kappa. With `score` (category -> number), linearly weighted kappa:
    disagreement weight |s_i - s_j| / (max - min)."""
    k = len(categories)
    idx = {c: i for i, c in enumerate(categories)}
    obs = np.zeros((k, k))
    for x, y in zip(a, b):
        obs[idx[x], idx[y]] += 1
    n = obs.sum()
    if n == 0:
        return float("nan")
    obs /= n
    exp = np.outer(obs.sum(1), obs.sum(0))
    if score is None:
        w = 1 - np.eye(k)
    else:
        s = np.array([score[c] for c in categories], dtype=float)
        span = s.max() - s.min()
        w = np.abs(s[:, None] - s[None, :]) / (span if span else 1)
    denom = (w * exp).sum()
    if denom == 0:
        return float("nan")
    return float(1 - (w * obs).sum() / denom)


def raw_agreement(a: list, b: list) -> float:
    return float(np.mean([x == y for x, y in zip(a, b)])) if a else float("nan")
