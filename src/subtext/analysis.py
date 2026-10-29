"""Module 7: analysis.  python -m subtext analyze --config config/analysis.yaml [--deviation FILE]

Implements docs/analysis_plan_v1.md Sections 6-7 and the addendum on RQ3 within E segments.
Runs offline: model outputs come from runs/<phase>/, embeddings from the cache written by
`python -m subtext embed`.

Three groups of analyses, by what they need:
  1. neither scores nor the response key: instability measures, RQ1 on instability
  2. scores but not the key: rubric metrics pooled over models, inter-rater agreement
  3. the response key: rubric metrics by model, RQ1 on interpretive error, RQ2 by model, RQ3

The key (scoring/private/key.json) is read only if the second scorer's score files exist, or if
--deviation names a committed deviation record (protocol Section 2). In both cases the addendum
named in the config must be committed. The key's SHA-256 is checked against
scoring/sets_manifest.json.

Outputs in analysis/ are aggregates only. Segment x model detail goes to scoring/private/
(git-ignored), so no committed output links a response_id or a scored response to a model.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import platform
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import stats as S
from .embed import load_analysis_config, load_embeddings, valid_cells
from .scoring import KEY_PATH, MANIFEST, SCORES, SHEETS, load_answer_key, load_sheet

MEASURES = ["semantic_dispersion", "tone_disagreement", "confidence_sd", "confidence_mean"]
# For RQ3 every predictor is oriented so that a higher value should mean a higher error risk.
RQ3_PREDICTORS = {"semantic_dispersion": 1, "tone_disagreement": 1, "confidence_sd": 1,
                  "confidence_mean": -1, "cross_model_distance": 1}
RQ3_LABELS = {"semantic_dispersion": "semantic dispersion", "tone_disagreement": "tone disagreement",
              "confidence_sd": "confidence SD", "confidence_mean": "mean confidence (reversed)",
              "cross_model_distance": "cross-model distance"}
LAYERS = ["A", "B", "C", "D"]
LEVELS = ["L1", "L2", "L3"]


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*args) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True)
    except FileNotFoundError:
        return subprocess.CompletedProcess(args, 127, "", "git not found")


def committed(path: str) -> str | None:
    """Commit hash of the last commit touching `path`, if it is tracked and unchanged; else None.

    Outside a Git repository (e.g. an archived release) the commit cannot be checked; the file
    must still exist, and the manifest records that the check was not possible."""
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        return "unverified: not a Git repository" if Path(path).exists() else None
    if git("ls-files", "--error-unmatch", path).returncode != 0:
        return None
    if git("diff", "--quiet", "HEAD", "--", path).returncode != 0:
        return None
    h = git("log", "-1", "--format=%H", "--", path).stdout.strip()
    return h or None


def error_of(cat: str, version: str, p_as_error: bool = False):
    if cat == "X":
        return None
    if version == "E":
        return int(cat in ("N", "M") or (p_as_error and cat == "P"))
    return int(cat == "O")


def nanfree(x):
    """JSON-safe: nan -> None, numpy scalars -> python."""
    if isinstance(x, dict):
        return {k: nanfree(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [nanfree(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if math.isnan(float(x)) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    return x


# ---------------------------------------------------------------- inputs

def read_score_file(set_name: str, scorer: str, stage: str) -> dict | None:
    p = SCORES / f"{set_name}__{scorer}.csv"
    if not p.exists():
        return None
    with open(p, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f)]
    return {r["response_id"]: r for r in rows if r.get("stage", stage) == stage}


def check_sheets() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, digest in manifest["sheets_sha256"].items():
        if sha_file(SHEETS / f"{name}.jsonl") != digest:
            raise RuntimeError(f"scoring sheet {name}.jsonl does not match {MANIFEST}")
    return manifest


def open_key(cfg: dict, deviation: str | None, manifest: dict) -> tuple:
    second = cfg["scoring"]["second_scorer"]
    second_done = all((SCORES / f"{s}__{second}.csv").exists() for s in ("practice", "second"))
    status = {"second_scoring_complete": second_done, "deviation": None, "addendum": None}
    if not second_done:
        if not deviation:
            return None, {**status, "opened": False,
                          "reason": "second scoring incomplete and no --deviation given"}
        h = committed(deviation)
        if not h:
            raise RuntimeError(f"{deviation} must be committed (and unchanged) before the key is read")
        status["deviation"] = {"file": deviation, "commit": h, "sha256": sha_file(deviation)}
    addendum = cfg["analysis"]["addendum"]
    h = committed(addendum)
    if not h:
        raise RuntimeError(f"{addendum} must be committed (and unchanged) before the key is read")
    status["addendum"] = {"file": addendum, "commit": h, "sha256": sha_file(addendum)}
    if not KEY_PATH.exists():
        raise RuntimeError(f"{KEY_PATH} not found")
    if sha_file(KEY_PATH) != manifest["key_sha256"]:
        raise RuntimeError(f"{KEY_PATH} does not match key_sha256 in {MANIFEST}")
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    return key, {**status, "opened": True, "key_sha256_verified": True}


# ---------------------------------------------------------------- instability

def instability(cells: dict, vecs: dict, models: list, codes: list) -> tuple:
    inst = {}
    for m in models:
        for c in codes:
            ks = sorted(k for k in cells if k[0] == m and k[2] == c)
            objs = [cells[k]["_obj"] for k in ks]
            confs = [o["confidence"] for o in objs]
            inst[(m, c)] = {
                "n_runs": len(ks),
                "semantic_dispersion": S.mean_pairwise_cosine_distance([vecs[k] for k in ks]),
                "tone_disagreement": S.tone_disagreement([o["tone"] for o in objs]),
                "confidence_sd": S.sample_sd(confs),
                "confidence_mean": float(np.mean(confs)) if confs else float("nan"),
            }
    cross = {}
    if len(models) == 2:
        a, b = models
        for c in codes:
            va = [vecs[k] for k in sorted(vecs) if k[0] == a and k[2] == c]
            vb = [vecs[k] for k in sorted(vecs) if k[0] == b and k[2] == c]
            cross[c] = S.mean_cross_cosine_distance(va, vb)
    return inst, cross


def describe(xs: list) -> dict:
    xs = [x for x in xs if not math.isnan(x)]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": float(np.mean(xs)), "median": float(np.median(xs)),
            "min": float(np.min(xs)), "max": float(np.max(xs))}


def rq1_instability(inst, cross, models, pairs, medium, n_boot, seed) -> dict:
    out = {}
    series = {m: {meas: {c: inst[(m, c)][meas] for (mm, c) in inst if mm == m} for meas in MEASURES}
              for m in models}
    if cross:
        series["cross-model"] = {"cross_model_distance": cross}
    for variant in ("all_pairs", "excluding_medium_confidence"):
        res = {}
        for m, by_meas in series.items():
            res[m] = {}
            for meas, val in by_meas.items():
                units = [(val[p["E"]["code"]], val[p["C"]["code"]]) for p in pairs
                         if not (variant != "all_pairs" and p["E"]["id"] in medium)]
                units = [u for u in units if not any(math.isnan(x) for x in u)]
                x, y = [u[0] for u in units], [u[1] for u in units]
                r = S.wilcoxon_paired(x, y)
                r["mean_E"], r["mean_C"] = float(np.mean(x)), float(np.mean(y))
                r["median_difference_ci"] = S.bootstrap_ci(
                    units, lambda us: float(np.median([a - b for a, b in us])), n_boot, seed)
                r["rank_biserial_ci"] = S.bootstrap_ci(
                    units, lambda us: S.rank_biserial_paired([a - b for a, b in us]), n_boot, seed)
                res[m][meas] = r
        out[variant] = res
    return out


# ---------------------------------------------------------------- rubric metrics

def metrics_table(rows: list, medium: set) -> dict:
    """rows: dicts with version, layer, level, category, id. Returns overall, by layer, level, cell."""
    def m(sub):
        return S.rubric_metrics([r["category"] for r in sub if r["version"] == "E"],
                                [r["category"] for r in sub if r["version"] == "C"])
    out = {}
    for variant in ("all_segments", "excluding_medium_confidence"):
        rs = rows if variant == "all_segments" else [r for r in rows if r["id"] not in medium]
        out[variant] = {
            "overall": m(rs),
            "by_layer": {L: m([r for r in rs if r["layer"] == L]) for L in LAYERS},
            "by_level": {L: m([r for r in rs if r["level"] == L]) for L in LEVELS},
            "by_cell": {f"{a}-{b}": m([r for r in rs if r["layer"] == a and r["level"] == b])
                        for a in LAYERS for b in LEVELS},
        }
    e = [r for r in rows if r["version"] == "E"]
    c = [r for r in rows if r["version"] == "C"]
    out["shortcut_check"] = {
        "E_intended_negative": S.rubric_metrics([r["category"] for r in e if r["intended_valence"] == "negative"], []),
        "E_intended_positive_or_mixed": S.rubric_metrics([r["category"] for r in e if r["intended_valence"] != "negative"], []),
        "C_surface_negative": S.rubric_metrics([], [r["category"] for r in c if r["surface_valence"] == "negative"]),
        "C_surface_not_negative": S.rubric_metrics([], [r["category"] for r in c if r["surface_valence"] != "negative"]),
    }
    return out


# ---------------------------------------------------------------- RQ1 error, RQ3, calibration

def rq1_error(seg_rows: dict, models: list, pairs: list, medium: set, n_boot, seed) -> dict:
    out = {}
    for variant, p_err, excl in [("main", False, False), ("P_as_error", True, False),
                                 ("excluding_medium_confidence", False, True)]:
        out[variant] = {}
        for m in models:
            units = []
            for p in pairs:
                if excl and p["E"]["id"] in medium:
                    continue
                e, c = seg_rows[(m, p["E"]["code"])], seg_rows[(m, p["C"]["code"])]
                ee, ce = error_of(e["category"], "E", p_err), error_of(c["category"], "C", p_err)
                if ee is not None and ce is not None:
                    units.append((ee, ce))
            r = S.mcnemar_exact([u[0] for u in units], [u[1] for u in units])
            r["error_rate_E"] = float(np.mean([u[0] for u in units])) if units else float("nan")
            r["error_rate_C"] = float(np.mean([u[1] for u in units])) if units else float("nan")
            r["difference"] = r["error_rate_E"] - r["error_rate_C"]
            r["difference_ci"] = S.bootstrap_ci(
                units, lambda us: float(np.mean([a - b for a, b in us])), n_boot, seed)
            out[variant][m] = r
    return out


def rq3(seg_rows: dict, cross: dict, models: list, medium: set, n_boot, seed) -> dict:
    out = {}
    for scope in ("all_48", "within_E"):
        for err_def, p_err in (("main", False), ("P_as_error", True)):
            for excl in (False, True):
                name = f"{scope}__{err_def}" + ("__excluding_medium_confidence" if excl else "")
                block = {}
                for target in models + ["pooled"]:
                    ms = models if target == "pooled" else [target]
                    clusters = defaultdict(list)
                    for (m, code), r in seg_rows.items():
                        if m not in ms or (scope == "within_E" and r["version"] != "E"):
                            continue
                        if excl and r["id"] in medium:
                            continue
                        y = error_of(r["category"], r["version"], p_err)
                        if y is None:
                            continue
                        preds = {k: r.get(k) if k != "cross_model_distance" else cross.get(code)
                                 for k in RQ3_PREDICTORS}
                        clusters[code].append((y, preds))
                    units = list(clusters.values())
                    flat = [o for u in units for o in u]
                    res = {"n": len(flat), "n_errors": sum(o[0] for o in flat),
                           "n_segments": len(units), "predictors": {}}
                    for k, sign in RQ3_PREDICTORS.items():
                        if k == "cross_model_distance" and not cross:
                            continue

                        def stat(us, k=k, sign=sign):
                            obs = [o for u in us for o in u if o[1][k] is not None and not math.isnan(o[1][k])]
                            return S.auc([sign * o[1][k] for o in obs], [o[0] for o in obs])
                        res["predictors"][k] = {"auc": stat(units),
                                                "ci": S.bootstrap_ci(units, stat, n_boot, seed)}
                    block[target] = res
                out[name] = block
    return out


def calibration(seg_rows: dict, models: list) -> dict:
    out = {}
    for scope in ("all_48", "within_E"):
        out[scope] = {}
        for m in models:
            obs = []
            for (mm, code), r in seg_rows.items():
                if mm != m or (scope == "within_E" and r["version"] != "E"):
                    continue
                y = error_of(r["category"], r["version"])
                if y is not None:
                    obs.append((r["confidence_run1"], 1 - y))
            if not obs:
                continue
            lo = int(min(o[0] for o in obs) // 5 * 5)
            bins = []
            for b in range(lo, 100, 5):
                sub = [o for o in obs if b <= o[0] < b + 5 or (b == 95 and o[0] == 100)]
                if sub:
                    bins.append({"bin": f"{b}-{b + 5}", "n": len(sub),
                                 "mean_confidence": float(np.mean([o[0] for o in sub])),
                                 "accuracy": float(np.mean([o[1] for o in sub]))})
            mc, acc = float(np.mean([o[0] for o in obs])), float(np.mean([o[1] for o in obs]))
            out[scope][m] = {"n": len(obs), "mean_confidence": mc, "accuracy": acc,
                             "overconfidence": mc / 100 - acc, "bins": bins}
    return out


# ---------------------------------------------------------------- agreement

def agreement(cfg: dict, key_ans: dict) -> dict:
    a_id, b_id = cfg["scoring"]["primary_scorer"], cfg["scoring"]["second_scorer"]
    stage = cfg["scoring"]["stage"]
    out = {}
    for set_name in ("practice", "second"):
        # The second-scorer set is drawn from the primary set, so XL's scores for it are in primary.
        a = read_score_file("primary" if set_name == "second" else set_name, a_id, stage)
        b = read_score_file(set_name, b_id, stage)
        if not a or not b:
            out[set_name] = {"status": "pending", "available": {a_id: bool(a), b_id: bool(b)}}
            continue
        sheet = {e["response_id"]: e for e in load_sheet(set_name)}
        ids = sorted(set(a) & set(b) & set(sheet))
        e_ids = [i for i in ids if key_ans[sheet[i]["code"]]["version"] == "E"]
        c_ids = [i for i in ids if key_ans[sheet[i]["code"]]["version"] == "C"]
        ea, eb = [a[i]["category"] for i in e_ids], [b[i]["category"] for i in e_ids]
        ca, cb = [a[i]["category"] for i in c_ids], [b[i]["category"] for i in c_ids]
        nx = [(x, y) for x, y in zip(ea, eb) if x != "X" and y != "X"]
        out[set_name] = {
            "n": len(ids), "unscored_by_either": len(set(sheet) - set(ids)),
            "E": {"n": len(e_ids), "raw_agreement": S.raw_agreement(ea, eb),
                  "kappa_unweighted": S.cohen_kappa(ea, eb, ["F", "P", "N", "M", "X"]),
                  "kappa_linear_weighted_non_X": S.cohen_kappa([x for x, _ in nx], [y for _, y in nx],
                                                               ["F", "P", "N", "M"], S.READ_SCORE),
                  "n_non_X": len(nx)},
            "C": {"n": len(c_ids), "raw_agreement": S.raw_agreement(ca, cb),
                  "kappa": S.cohen_kappa(ca, cb, ["A", "O", "X"])},
        }
    return out


# ---------------------------------------------------------------- figures

def figures(out_dir: Path, results: dict, models: list):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans"})
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    for old in fig_dir.glob("fig*_rq*.*"):      # no stale figure survives a run that does not redraw it
        old.unlink()
    colors = {models[0]: "#1f77b4", models[-1]: "#d62728", "pooled": "#444444",
              "cross-model": "#2ca02c"} if models else {}
    written = []

    # Figure 1: RQ1
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1, 1.6]})
    err = results.get("rq1_error", {}).get("main")
    if err:
        w = 0.35
        for i, m in enumerate(models):
            r = err[m]
            ax1.bar([i - w / 2, i + w / 2], [r["error_rate_E"], r["error_rate_C"]], w,
                    color=[colors[m], "white"], edgecolor=colors[m], hatch=["", "//"])
            ax1.text(i, max(r["error_rate_E"], r["error_rate_C"]) + 0.04,
                     f"McNemar p = {r['p']:.3g}\nn = {r['n_pairs']} pairs", ha="center", fontsize=8)
        ax1.set_xticks(range(len(models)), models)
        ax1.set_ylim(0, 1.15)
        ax1.set_ylabel("interpretive error rate (run 1)")
        ax1.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="grey"),
                            plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="grey", hatch="//")],
                   labels=["E (subtext)", "C (control)"], loc="upper right", fontsize=8)
    else:
        ax1.text(0.5, 0.5, "requires the response key", ha="center", va="center", transform=ax1.transAxes)
        ax1.set_axis_off()
    ax1.set_title("a  Interpretive error, E vs C (paired)", loc="left")
    inst = results["rq1_instability"]["all_pairs"]
    labels, k = [], 0
    for m, by_meas in inst.items():
        for meas, r in by_meas.items():
            ci = r["rank_biserial_ci"]
            ax2.errorbar(r["rank_biserial"], k, xerr=[[r["rank_biserial"] - ci["low"]], [ci["high"] - r["rank_biserial"]]]
                         if ci["low"] is not None else None, fmt="o", color=colors.get(m, "k"), capsize=3)
            labels.append(f"{m}: {meas.replace('_', ' ')}")
            k += 1
    ax2.axvline(0, color="grey", lw=0.8)
    ax2.set_yticks(range(k), labels)
    ax2.invert_yaxis()
    ax2.set_xlim(-1.05, 1.05)
    ax2.set_xlabel("matched-pairs rank-biserial r (E − C), 95% bootstrap CI")
    ax2.set_title("b  Instability, E vs C (paired)", loc="left")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(fig_dir / f"fig1_rq1.{ext}", dpi=200)
        written.append(str(fig_dir / f"fig1_rq1.{ext}"))
    plt.close(fig)

    # Figure 2: RQ2 heat maps
    rows = results.get("rubric_by_model") or {"pooled": results["rubric_pooled"]}
    fig, axes = plt.subplots(len(rows), 2, figsize=(8.5, 3.0 * len(rows)), squeeze=False)
    for i, (name, tab) in enumerate(rows.items()):
        cells = tab["all_segments"]["by_cell"]
        for j, (metric, n_key, vmax, cmap, title) in enumerate([
                ("mean_read_score", "n_E", 2, "Blues", "E: mean read score (0–2)"),
                ("over_interpretation_rate", "n_C", 1, "Reds", "C: over-interpretation rate")]):
            ax = axes[i][j]
            grid = np.full((4, 3), np.nan)
            for a, L in enumerate(LAYERS):
                for b, V in enumerate(LEVELS):
                    v = cells[f"{L}-{V}"].get(metric)
                    grid[a, b] = np.nan if v is None else v
            ax.imshow(grid, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
            for a, L in enumerate(LAYERS):
                for b, V in enumerate(LEVELS):
                    c = cells[f"{L}-{V}"]
                    v = c.get(metric)
                    txt = "–" if v is None else f"{v:.2f}"
                    ax.text(b, a, f"{txt}\nn={c[n_key]}", ha="center", va="center", fontsize=8,
                            color="white" if v is not None and v > 0.6 * vmax else "black")
            ax.set_xticks(range(3), ["L1 explicit", "L2 subtle", "L3 context"])
            ax.set_yticks(range(4), ["A evaluation", "B emotion", "C irony/humour", "D silence"])
            ax.set_title(f"{name} — {title}", fontsize=9)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(fig_dir / f"fig2_rq2.{ext}", dpi=200)
        written.append(str(fig_dir / f"fig2_rq2.{ext}"))
    plt.close(fig)

    # Figure 3: RQ3
    if "rq3" in results:
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), gridspec_kw={"width_ratios": [1.3, 1.3, 1]})
        for ax, scope, title in [(axes[0], "all_48__main", "a  RQ3, all 48 segments (pre-specified)"),
                                 (axes[1], "within_E__main", "b  RQ3, within E segments (addendum)")]:
            block = results["rq3"][scope]
            targets = models + ["pooled"]
            preds = list(RQ3_PREDICTORS)
            for t_i, t in enumerate(targets):
                for p_i, p in enumerate(preds):
                    r = block[t]["predictors"].get(p)
                    if not r or r["auc"] is None:
                        continue
                    y = p_i + (t_i - 1) * 0.22
                    ci = r["ci"]
                    xerr = None if ci["low"] is None else [[r["auc"] - ci["low"]], [ci["high"] - r["auc"]]]
                    ax.errorbar(r["auc"], y, xerr=xerr, fmt="o", color=colors[t], capsize=3,
                                label=t if p_i == 0 else None)
            ax.axvline(0.5, color="grey", lw=0.8)
            ax.set_yticks(range(len(preds)), [RQ3_LABELS[p] for p in preds])
            ax.invert_yaxis()
            ax.set_xlim(0, 1)
            ax.set_xlabel("AUC for interpretive error, 95% bootstrap CI")
            ax.set_title(title, loc="left", fontsize=9)
            ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
        ax = axes[2]
        lowest = 1.0
        for k_m, m in enumerate(models):
            c = results["calibration"]["all_48"].get(m)
            if not c:
                continue
            xs = [b["mean_confidence"] / 100 for b in c["bins"]]
            ys = [b["accuracy"] for b in c["bins"]]
            lowest = min([lowest, *xs])
            ax.plot(xs, ys, "-o", color=colors[m], label=m)
            for x, y, b in zip(xs, ys, c["bins"]):
                ax.annotate(f"n={b['n']}", (x, y), textcoords="offset points",
                            xytext=(-6, 7 if k_m == 0 else -12), fontsize=7, color=colors[m])
        ax.plot([0, 1], [0, 1], ":", color="grey")
        ax.set_xlim(max(0.0, min(0.5, lowest - 0.05)), 1.02)
        ax.set_ylim(0, 1.02)
        ax.set_xlabel("self-rated confidence, run 1 (binned)")
        ax.set_ylabel("share correct (run 1)")
        ax.set_title("c  Confidence calibration, all 48", loc="left", fontsize=9)
        ax.legend(fontsize=7)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(fig_dir / f"fig3_rq3.{ext}", dpi=200)
            written.append(str(fig_dir / f"fig3_rq3.{ext}"))
        plt.close(fig)
    return written


# ---------------------------------------------------------------- tables (Markdown)

def f3(x):
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.3f}"


def ci(c):
    return "–" if not c or c.get("low") is None else f"[{c['low']:.3f}, {c['high']:.3f}]"


def tables_md(R: dict, models: list) -> str:
    L = [f"# Stage 1 analysis results", "",
         f"Generated {R['meta']['created_at']} by `python -m subtext analyze`. Aggregates only. "
         f"Primary scorer {R['meta']['primary_scorer']}, stage {R['meta']['stage']}. "
         f"Response key opened: {R['meta']['key']['opened']}.", ""]
    L += ["## Instability (all five runs)", "", "| model | version | measure | mean | median |", "|---|---|---|---|---|"]
    for m, by_v in R["instability_summary"].items():
        for v, by_meas in by_v.items():
            for meas, d in by_meas.items():
                L.append(f"| {m} | {v} | {meas} | {f3(d.get('mean'))} | {f3(d.get('median'))} |")
    L += ["", "## RQ1b: instability, E vs C (paired by pair_id)", "",
          "| model | measure | mean E | mean C | median diff [CI] | r_rb [CI] | Wilcoxon p | nonzero pairs |",
          "|---|---|---|---|---|---|---|---|"]
    for m, by_meas in R["rq1_instability"]["all_pairs"].items():
        for meas, r in by_meas.items():
            L.append(f"| {m} | {meas} | {f3(r['mean_E'])} | {f3(r['mean_C'])} | {f3(r['median_difference'])} "
                     f"{ci(r['median_difference_ci'])} | {f3(r['rank_biserial'])} {ci(r['rank_biserial_ci'])} | "
                     f"{f3(r['p'])} | {r['n_nonzero']}/{r['n_pairs']} |")
    def rub_rows(name, t):
        o = t["all_segments"]["overall"]
        return (f"| {name} | {o['n_E']} | {f3(o.get('strict_read_rate'))} | {f3(o.get('lenient_read_rate'))} | "
                f"{f3(o.get('mean_read_score'))} | {f3(o.get('misread_rate'))} | {o['n_C']} | "
                f"{f3(o.get('over_interpretation_rate'))} | {f3(o.get('discrimination_index'))} | "
                f"{f3(o.get('d_prime'))} | {o['X_E'] + o['X_C']} |")
    head = ["| | n E | strict | lenient | mean score | misread | n C | over-interp. | discrimination | d′ | X |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    L += ["", "## Rubric Section 8 metrics (run 1)", ""] + head + [rub_rows("pooled", R["rubric_pooled"])]
    for m, t in (R.get("rubric_by_model") or {}).items():
        L.append(rub_rows(m, t))
    targets = {"pooled": R["rubric_pooled"], **(R.get("rubric_by_model") or {})}

    def short_row(name, o):
        return (f"| {name} | {o['n_E']} | {f3(o.get('strict_read_rate'))} | {f3(o.get('lenient_read_rate'))} | "
                f"{f3(o.get('mean_read_score'))} | {f3(o.get('misread_rate'))} | {o['n_C']} | "
                f"{f3(o.get('over_interpretation_rate'))} |")
    sub_head = ["| {} | n E | strict | lenient | mean score | misread | n C | over-interp. |",
                "|---|---|---|---|---|---|---|---|"]
    L += ["", "Excluding the three medium-confidence segments:", "", sub_head[0].format("target"), sub_head[1]]
    for name, t in targets.items():
        L.append(short_row(name, t["excluding_medium_confidence"]["overall"]))
    for grp, keys, title in [("by_layer", LAYERS, "layer"), ("by_level", LEVELS, "level")]:
        L += ["", f"### By {title}", "", sub_head[0].format(f"target · {title}"), sub_head[1]]
        for name, t in targets.items():
            for k in keys:
                L.append(short_row(f"{name} · {k}", t["all_segments"][grp][k]))
    L += ["", "### Shortcut check (rubric Section 8)", "",
          "| target | group | n | strict | lenient | misread | over-interp. |", "|---|---|---|---|---|---|---|"]
    for name, t in targets.items():
        for g, o in t["shortcut_check"].items():
            n = o["n_E"] if g.startswith("E_") else o["n_C"]
            L.append(f"| {name} | {g} | {n} | {f3(o.get('strict_read_rate'))} | {f3(o.get('lenient_read_rate'))} | "
                     f"{f3(o.get('misread_rate'))} | {f3(o.get('over_interpretation_rate'))} |")
    if "rq1_error" in R:
        L += ["", "## RQ1a: interpretive error, E vs C (McNemar, exact)", "",
              "| variant | model | pairs | error E | error C | diff [CI] | E only | C only | p |",
              "|---|---|---|---|---|---|---|---|---|"]
        for var, block in R["rq1_error"].items():
            for m, r in block.items():
                L.append(f"| {var} | {m} | {r['n_pairs']} | {f3(r['error_rate_E'])} | {f3(r['error_rate_C'])} | "
                         f"{f3(r['difference'])} {ci(r['difference_ci'])} | {r['E_error_only']} | "
                         f"{r['C_error_only']} | {f3(r['p'])} |")
    if "rq3" in R:
        L += ["", "## RQ3: AUC for interpretive error (run 1)", "",
              "`all_48` is pre-specified; `within_E` is the addendum analysis (exploratory).", "",
              "| analysis | target | n (errors) | predictor | AUC [CI] | skipped resamples |", "|---|---|---|---|---|---|"]
        for name, block in R["rq3"].items():
            for t, r in block.items():
                for p, a in r["predictors"].items():
                    L.append(f"| {name} | {t} | {r['n']} ({r['n_errors']}) | {p} | {f3(a['auc'])} {ci(a['ci'])} | "
                             f"{a['ci']['skipped']} |")
        L += ["", "## Calibration (run-1 confidence vs share correct)", "",
              "| scope | model | n | mean confidence | accuracy | overconfidence |", "|---|---|---|---|---|---|"]
        for scope, block in R["calibration"].items():
            for m, c in block.items():
                L.append(f"| {scope} | {m} | {c['n']} | {f3(c['mean_confidence'])} | {f3(c['accuracy'])} | "
                         f"{f3(c['overconfidence'])} |")
    L += ["", "## Inter-rater agreement (pre-discussion)", ""]
    for s, a in R["agreement"].items():
        if a.get("status") == "pending":
            L.append(f"- {s}: pending")
        else:
            L.append(f"- {s}: n={a['n']}; E κ={f3(a['E']['kappa_unweighted'])}, weighted κ (non-X)="
                     f"{f3(a['E']['kappa_linear_weighted_non_X'])}, raw={f3(a['E']['raw_agreement'])}; "
                     f"C κ={f3(a['C']['kappa'])}, raw={f3(a['C']['raw_agreement'])}")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- main

def run_analysis(config_path: str, deviation: str | None = None) -> dict:
    cfg = load_analysis_config(config_path)
    acfg = cfg["analysis"]
    n_boot, seed = int(acfg["bootstrap"]), int(acfg["seed"])
    medium = set(acfg["medium_confidence_segments"])
    out_dir, private_dir = Path(cfg["outputs"]["dir"]), Path(cfg["outputs"]["private_dir"])

    ans = load_answer_key()
    codes = sorted(ans)
    by_id = {v["id"]: v for v in ans.values()}
    if not medium <= set(by_id):
        raise RuntimeError(f"unknown medium-confidence ids: {medium - set(by_id)}")
    pairs = []
    for pid in sorted({v["pair_id"] for v in ans.values()}):
        vs = {v["version"]: v for v in ans.values() if v["pair_id"] == pid}
        pairs.append({"pair_id": pid, "E": vs["E"], "C": vs["C"]})

    cells = valid_cells(cfg["phase"])
    models = sorted({k[0] for k in cells}, key=lambda m: (len(m), m))
    vecs, emeta = load_embeddings(cfg, cells)
    runs_per = {m: sorted({k[1] for k in cells if k[0] == m}) for m in models}
    expected = {(m, r, c) for m in models for r in runs_per[m] for c in codes}
    missing_cells = sorted(expected - set(cells))

    # 1. instability (no scores, no key)
    inst, cross = instability(cells, vecs, models, codes)
    R = {"meta": {}, "missing_cells": [list(x) for x in missing_cells]}
    R["instability_summary"] = {
        m: {v: {meas: describe([inst[(m, c)][meas] for c in codes if ans[c]["version"] == v]) for meas in MEASURES}
            for v in ("E", "C")} for m in models}
    if cross:
        R["instability_summary"]["cross-model"] = {
            v: {"cross_model_distance": describe([cross[c] for c in codes if ans[c]["version"] == v])}
            for v in ("E", "C")}
    R["rq1_instability"] = rq1_instability(inst, cross, models, pairs, medium, n_boot, seed)

    # 2. scores (no key)
    manifest = check_sheets()
    scorer, stage = cfg["scoring"]["primary_scorer"], cfg["scoring"]["stage"]
    scores = read_score_file("primary", scorer, stage)
    sheet = load_sheet("primary")
    if not scores:
        raise RuntimeError(f"no {stage} scores in scoring/scores/primary__{scorer}.csv")
    unscored = [e["response_id"] for e in sheet if e["response_id"] not in scores]
    if unscored:
        raise RuntimeError(f"{len(unscored)} primary responses unscored, e.g. {unscored[:3]}")
    resp = []
    for e in sheet:
        s, a = scores[e["response_id"]], ans[e["code"]]
        if s["code"] != e["code"]:
            raise RuntimeError(f"{e['response_id']}: score file code {s['code']} != sheet code {e['code']}")
        resp.append({"response_id": e["response_id"], "code": e["code"], "category": s["category"],
                     "id": a["id"], "version": a["version"], "layer": a["layer"][0], "level": a["level"][:2],
                     "intended_valence": a["intended_valence"], "surface_valence": a["surface_valence"]})
    R["rubric_pooled"] = metrics_table(resp, medium)
    R["agreement"] = agreement(cfg, ans)

    # 3. key-dependent
    key, key_status = open_key(cfg, deviation, manifest)
    seg_rows = {}
    if key:
        for r in resp:
            k = key.get(r["response_id"])
            if not k or k["set"] != "primary" or int(k["run"]) != 1 or k["code"] != r["code"]:
                raise RuntimeError(f"key entry for {r['response_id']} is inconsistent with the primary sheet")
            cell = cells.get((k["model"], 1, r["code"]))
            sheet_entry = next(e for e in sheet if e["response_id"] == r["response_id"])
            if cell is None or cell["_obj"]["interpretation"] != sheet_entry["interpretation"]:
                raise RuntimeError(f"{r['response_id']}: key does not point to the scored run-1 response")
            if (k["model"], r["code"]) in seg_rows:
                raise RuntimeError(f"two primary responses for {(k['model'], r['code'])}")
            seg_rows[(k["model"], r["code"])] = {
                **r, "model": k["model"], "pair_id": ans[r["code"]]["pair_id"],
                "confidence_run1": cell["_obj"]["confidence"], **inst[(k["model"], r["code"])],
                "cross_model_distance": cross.get(r["code"])}
        by_model = {m: [v for (mm, _), v in seg_rows.items() if mm == m] for m in models}
        R["rubric_by_model"] = {m: metrics_table(rows, medium) for m, rows in by_model.items()}
        R["rq1_error"] = rq1_error(seg_rows, models, pairs, medium, n_boot, seed)
        R["rq3"] = rq3(seg_rows, cross, models, medium, n_boot, seed)
        R["calibration"] = calibration(seg_rows, models)

    # outputs
    import matplotlib
    import scipy
    R["meta"] = {
        "created_at": now(), "config": config_path, "phase": cfg["phase"], "models": models,
        "runs_per_model": runs_per, "n_valid_cells": len(cells), "primary_scorer": scorer, "stage": stage,
        "bootstrap": {"n": n_boot, "seed": seed, "method": "percentile"},
        "medium_confidence_segments": sorted(medium), "key": key_status,
        "embedding": {k: emeta[k] for k in ("embedding_model", "ollama_version", "prefix", "repeat_check",
                                             "embeddings_sha256")},
        "conventions": {
            "interpretive_error": "E: N or M; C: O; X treated as missing. Sensitivity: P counted as error.",
            "auc_direction": "higher predictor value = higher error risk; mean confidence reversed",
            "pooled_bootstrap": "segments resampled as clusters (both models' observations together)",
            "rq1_bootstrap": "pairs resampled",
            "medium_confidence": "paired analyses drop the whole pair; unpaired analyses drop the E segment",
            "d_prime": "lenient read rate vs over-interpretation rate, log-linear correction in every cell",
            "confidence_sd": "sample SD (n-1)",
            "calibration": "run-1 confidence of the scored response, 5-point bins",
            "kappa": "E: unweighted on F/P/N/M/X; linear weights on read score (F2 P1 N0 M0) on items "
                     "neither scorer coded X. C: unweighted on A/O/X; raw agreement reported",
        },
        "software": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__,
                     "matplotlib": matplotlib.__version__, "platform": platform.platform()},
    }
    R = nanfree(R)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    (out_dir / "results.md").write_text(tables_md(R, models), encoding="utf-8")
    figs = figures(out_dir, R, models)

    if seg_rows:
        private_dir.mkdir(parents=True, exist_ok=True)
        fields = ["model", "code", "id", "pair_id", "version", "layer", "level", "category",
                  "confidence_run1", *MEASURES, "cross_model_distance"]
        with open(private_dir / "segment_level.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for k in sorted(seg_rows):
                w.writerow(seg_rows[k])

    run_files = sorted(str(p) for p in (Path("runs") / cfg["phase"]).glob("*/run*/code*_a*.json"))
    run_hash = hashlib.sha256("".join(f"{p}\n{sha_file(p)}\n" for p in run_files).encode()).hexdigest()
    inputs = {p: sha_file(p) for p in [config_path, "data/derived/answer_key.jsonl", str(MANIFEST),
                                       str(out_dir / "embeddings.jsonl"),
                                       *[str(SHEETS / f"{s}.jsonl") for s in ("practice", "primary", "second")]]}
    for p in sorted(SCORES.glob("*.csv")):
        inputs[str(p)] = sha_file(p)
    head = git("rev-parse", "HEAD").stdout.strip() or None
    dirty = git("status", "--porcelain", "src", "config", "prompts").stdout.strip()
    analysis_manifest = {
        "created_at": R["meta"]["created_at"], "git_head": head,
        "code_or_config_uncommitted": bool(dirty), "inputs_sha256": inputs,
        "run_records": {"n_files": len(run_files), "combined_sha256": run_hash},
        "key": key_status, "outputs": ["analysis/results.json", "analysis/results.md", *figs],
        "private_outputs": [str(private_dir / "segment_level.csv")] if seg_rows else [],
    }
    (out_dir / "analysis_manifest.json").write_text(json.dumps(analysis_manifest, indent=2), encoding="utf-8")
    return {"key_opened": key_status["opened"], "outputs": analysis_manifest["outputs"],
            "missing_cells": len(missing_cells), "code_or_config_uncommitted": bool(dirty)}
