"""Unit tests for module 7 statistics.  Run from the repository root:  python tests/test_analysis.py"""
import math
import sys

sys.path.insert(0, "src")
from subtext import stats as S

ok = True


def check(name, got, want, tol=1e-6):
    global ok
    good = (math.isnan(got) and math.isnan(want)) if isinstance(want, float) and math.isnan(want) \
        else abs(got - want) <= tol
    ok &= good
    print(f"{'OK ' if good else 'BAD'} {name:<45} got={got!r} want={want!r}")


# Cohen's kappa: textbook 2x2 example (a=20, b=5, c=10, d=15; po=0.70, pe=0.50 -> 0.40)
a = ["y"] * 25 + ["n"] * 25
b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
check("kappa 2x2 textbook", S.cohen_kappa(a, b, ["y", "n"]), 0.4)
check("kappa perfect", S.cohen_kappa(list("FPNM"), list("FPNM"), list("FPNMX")), 1.0)
# linear weights: one full-scale disagreement (F vs N) costs more than F vs P
w1 = S.cohen_kappa(list("FFPPNN"), list("FPPPNN"), list("FPNM"), S.READ_SCORE)
w2 = S.cohen_kappa(list("FFPPNN"), list("NFPPNN"), list("FPNM"), S.READ_SCORE)
check("weighted kappa penalises distance", float(w1 > w2), 1.0)
check("weighted kappa: N vs M not penalised", S.cohen_kappa(list("FPNN"), list("FPNM"), list("FPNM"), S.READ_SCORE), 1.0)

# AUC
check("auc perfect", S.auc([3, 4, 1, 2], [1, 1, 0, 0]), 1.0)
check("auc ties", S.auc([1, 1], [1, 0]), 0.5)
check("auc one class -> nan", S.auc([1, 2], [1, 1]), float("nan"))
check("auc 0.75", S.auc([2, 4, 1, 3], [1, 1, 0, 0]), 0.75)

# McNemar exact: b=8, c=1 -> two-sided binomial p = 0.0390625
e = [1] * 8 + [0] * 1 + [1] * 5 + [0] * 10
c = [0] * 8 + [1] * 1 + [1] * 5 + [0] * 10
r = S.mcnemar_exact(e, c)
check("mcnemar b", r["E_error_only"], 8)
check("mcnemar p", r["p"], 0.0390625)
check("mcnemar no discordant -> p=1", S.mcnemar_exact([1, 0], [1, 0])["p"], 1.0)

# rank-biserial: all positive -> 1, symmetric -> 0
check("rank-biserial all positive", S.rank_biserial_paired([0.1, 0.2, 0.3]), 1.0)
check("rank-biserial symmetric", S.rank_biserial_paired([1, -1, 2, -2]), 0.0)
check("rank-biserial zeros dropped", S.rank_biserial_paired([0, 0, 1]), 1.0)

# d' log-linear: hits 10/10, FA 0/10 -> z(10.5/11) - z(0.5/11)
from scipy.stats import norm
check("d prime log-linear", S.d_prime(10, 10, 0, 10), norm.ppf(10.5 / 11) - norm.ppf(0.5 / 11))

# instability
check("tone disagreement 3/5 modal", S.tone_disagreement(["a", "a", "a", "b", "c"]), 0.4)
check("tone disagreement unanimous", S.tone_disagreement(["a"] * 5), 0.0)
check("dispersion identical", S.mean_pairwise_cosine_distance([[1, 0], [1, 0], [1, 0]]), 0.0)
check("dispersion orthogonal", S.mean_pairwise_cosine_distance([[1, 0], [0, 1]]), 1.0)
check("cross distance", S.mean_cross_cosine_distance([[1, 0]], [[0, 1], [1, 0]]), 0.5)
check("sample sd", S.sample_sd([90, 90, 95, 95, 90]), 2.7386127875258306)

# rubric metrics
m = S.rubric_metrics(["F", "P", "N", "M", "X"], ["A", "A", "O", "X"])
check("strict read", m["strict_read_rate"], 0.25)
check("lenient read", m["lenient_read_rate"], 0.5)
check("mean read score", m["mean_read_score"], 0.75)
check("misread", m["misread_rate"], 0.25)
check("over-interpretation", m["over_interpretation_rate"], 1 / 3)
check("discrimination", m["discrimination_index"], 0.5 - 1 / 3)

# bootstrap: constant statistic -> degenerate interval; nan resamples counted
ci = S.bootstrap_ci([1, 1, 1], lambda us: float(sum(us)), 50, 1)
check("bootstrap constant", ci["low"], 3.0)
ci = S.bootstrap_ci([0, 1], lambda us: float("nan") if len(set(us)) == 1 else 1.0, 200, 1)
check("bootstrap skipped counted", float(ci["skipped"] > 0), 1.0)

print("ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
