"""Workbench demo view.  python -m subtext build-demo [--out docs/workbench/index.html]

Builds one self-contained HTML page from repository files only: segments and answer key
(data/derived), the 480 main-run records (runs/main), the embedding cache, the published response
key and primary scores, the analysis results and the quote-audit review. Nothing is called and
nothing is estimated: every value on the page is read or computed here, with the same functions
as the analysis, and the page lists the SHA-256 of every input.

Two quantities exist only on the page:
  quote spans        where each quote sits in the passage, so it can be highlighted. Spans follow
                     the validator's tiers (verbatim, loose, elided, stitched); for near and absent
                     quotes the span is the closest passage window and is drawn as such.
  constellation      a two-dimensional classical MDS projection of the ten readings of a segment,
                     from their cosine distances. It is an approximate picture; the measures on the
                     page are computed from the full embeddings. All segments share one scale.
"""
from __future__ import annotations

import csv
import datetime as dt
import difflib
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import stats as S
from .embed import load_analysis_config, load_embeddings, valid_cells
from .validate import _EDGE_PUNCT, _SPEAKER, _TYPO, check_quote

TEMPLATE = Path(__file__).with_name("demo_template.html")
COMPRESSION = 30          # replay: 30 s of recorded run time are shown as 1 s
REPLAY = ["122", "106"]   # C-L3-01-E (main example), C-L1-02-E (second example)


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*args) -> str | None:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


# ---------------------------------------------------------------- quote spans

def norm_map(text: str):
    """Typographic normalisation as in validate.normalise, with a map back to original indices."""
    out, idx, prev_space = [], [], False
    for i, ch in enumerate(text):
        rep = _TYPO.get(ch, ch)
        if rep.isspace():
            if prev_space or not out:
                continue
            out.append(" "); idx.append(i); prev_space = True
            continue
        prev_space = False
        for c in rep:
            out.append(c); idx.append(i)
    while out and out[-1] == " ":
        out.pop(); idx.pop()
    return "".join(out), idx


def _span(idx, start, length):
    return [idx[start], idx[start + length - 1] + 1]


def _loose(s: str) -> str:
    from .validate import normalise
    return normalise(s).casefold().strip(_EDGE_PUNCT)


def quote_spans(quote: str, tier: str, passage: str) -> list:
    from .validate import normalise
    p_norm, idx = norm_map(passage)
    p_low = p_norm.casefold()
    q_norm = normalise(quote)
    if tier == "verbatim":
        q = _SPEAKER.sub("", q_norm) if p_norm.find(q_norm) < 0 else q_norm
        pos = p_norm.find(q)
        return [_span(idx, pos, len(q))] if pos >= 0 else []
    if tier == "loose":
        q = _loose(_SPEAKER.sub("", q_norm))
        pos = p_low.find(q)
        return [_span(idx, pos, len(q))] if pos >= 0 else []
    if tier == "elided":
        spans, cursor = [], 0
        for f in [_loose(x) for x in q_norm.split("...")]:
            if not f:
                continue
            pos = p_low.find(f, cursor)
            if pos < 0:
                break
            spans.append(_span(idx, pos, len(f))); cursor = pos + len(f)
        return spans
    if tier == "stitched":
        spans = []
        for s in [_loose(x) for x in re.split(r"(?<=[.!?])\s+", _SPEAKER.sub("", q_norm))]:
            pos = p_low.find(s) if s else -1
            if pos >= 0:
                spans.append(_span(idx, pos, len(s)))
        return spans
    # near / absent: closest word window, as in the validator
    toks = [(m.start(), m.end()) for m in re.finditer(r"\S+", p_low)]
    p_words = [p_low[a:b] for a, b in toks]
    q_words = _loose(_SPEAKER.sub("", q_norm)).split()
    n, best, where = len(q_words), 0.0, None
    for size in range(max(1, n - 2), n + 3):
        for i in range(0, max(1, len(p_words) - size + 1)):
            r = difflib.SequenceMatcher(None, q_words, p_words[i:i + size]).ratio()
            if r > best:
                best, where = r, (i, min(i + size, len(p_words)))
    if not where:
        return []
    a, b = where
    return [[idx[toks[a][0]], idx[toks[b - 1][1] - 1] + 1]]


def label_spans(passage: str) -> list:
    out = []
    for m in re.finditer(r"(Interviewer|Interviewee):|\[[^\]\n]{3,60}\]", passage):
        out.append([m.start(), m.end(), "speaker" if m.group(0).endswith(":") else "note"])
    return out


# ---------------------------------------------------------------- constellation

def mds2(vecs: list) -> list:
    a = np.asarray(vecs, dtype=float)
    d2 = np.clip(1.0 - a @ a.T, 0, None) ** 2
    n = len(a)
    j = np.eye(n) - np.ones((n, n)) / n
    b = -0.5 * j @ d2 @ j
    w, v = np.linalg.eigh(b)
    order = np.argsort(w)[::-1][:2]
    coords = v[:, order] * np.sqrt(np.clip(w[order], 0, None))
    # fix orientation so that pictures are stable across rebuilds
    for k in range(2):
        if coords[np.argmax(np.abs(coords[:, k])), k] < 0:
            coords[:, k] *= -1
    return coords.tolist()


# ---------------------------------------------------------------- review file

def quote_review(path="docs/quote_audit_main_review.md") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    counts = defaultdict(int)
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|.*\|\s*([^|]+?)\s*\|\s*$", line)
        if m:
            counts[m.group(2)] += 1
    return dict(counts)


# ---------------------------------------------------------------- build

def build_demo(out: str = "docs/workbench/index.html", config_path: str = "config/analysis.yaml") -> dict:
    cfg = load_analysis_config(config_path)
    cells = valid_cells(cfg["phase"])
    vecs, emeta = load_embeddings(cfg, cells)
    answer = {json.loads(l)["code"]: json.loads(l)
              for l in Path("data/derived/answer_key.jsonl").read_text(encoding="utf-8").splitlines()}
    models = sorted({k[0] for k in cells}, key=lambda m: (len(m), m))
    runs = sorted({k[1] for k in cells})

    key = json.loads(Path("scoring/private/key.json").read_text(encoding="utf-8"))
    manifest = json.loads(Path("scoring/sets_manifest.json").read_text(encoding="utf-8"))
    if sha("scoring/private/key.json") != manifest["key_sha256"]:
        raise RuntimeError("scoring/private/key.json does not match scoring/sets_manifest.json")
    scores = {}
    with open("scoring/scores/primary__XL.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["stage"] == "pre-discussion":
                k = key[r["response_id"]]
                scores[(k["model"], r["code"])] = r["category"]

    segments, coords_all = [], []
    for code in sorted(answer, key=lambda c: answer[c]["id"]):
        a = answer[code]
        passage = a["passage"]
        readings = []
        for m in models:
            for r in runs:
                rec = cells[(m, r, code)]
                obj = rec["_obj"]
                quotes = []
                for c in obj["codes"]:
                    t = check_quote(c["quote"], passage)
                    quotes.append({"label": c["label"], "quote": c["quote"], "tier": t["tier"],
                                   "sim": t["similarity"], "spans": quote_spans(c["quote"], t["tier"], passage)})
                readings.append({
                    "model": m, "run": r, "interpretation": obj["interpretation"], "tone": obj["tone"],
                    "confidence": obj["confidence"], "codes": quotes, "thinking": rec["response"]["thinking"] or "",
                    "seconds": rec["response"]["wall_seconds"], "seed": rec["seed"], "attempt": rec["attempt"],
                    "tokens": rec["response"]["usage"].get("eval_count"), "file": rec["_path"],
                    "started": rec["started_at"],
                })
        order = [(x["model"], x["run"]) for x in readings]
        v = [vecs[(m, r, code)] for m, r in order]
        xy = mds2(v)
        coords_all.extend(xy)
        for x, p in zip(readings, xy):
            x["xy"] = p
        inst = {}
        for m in models:
            vv = [vecs[(m, r, code)] for r in runs]
            objs = [cells[(m, r, code)]["_obj"] for r in runs]
            confs = [o["confidence"] for o in objs]
            inst[m] = {"semantic_dispersion": S.mean_pairwise_cosine_distance(vv),
                       "tone_disagreement": S.tone_disagreement([o["tone"] for o in objs]),
                       "confidence_sd": S.sample_sd(confs), "confidence_mean": float(np.mean(confs))}
        cross = S.mean_cross_cosine_distance([vecs[(models[0], r, code)] for r in runs],
                                             [vecs[(models[-1], r, code)] for r in runs]) if len(models) == 2 else None
        segments.append({
            "code": code, "id": a["id"], "pair": a["pair_id"], "layer": a["layer"], "level": a["level"],
            "version": a["version"], "details": a["details"], "passage": passage, "labels": label_spans(passage),
            "key": {k: a[k] for k in ("surface_meaning", "intended_meaning", "key_cues", "surface_valence",
                                       "intended_valence", "author_confidence")},
            "scores": {m: scores.get((m, code)) for m in models},
            "instability": inst, "cross": cross, "readings": readings,
        })
    scale = float(np.max(np.abs(np.asarray(coords_all)))) if coords_all else 1.0

    results = json.loads(Path("analysis/results.json").read_text(encoding="utf-8"))
    tiers = defaultdict(lambda: defaultdict(int))
    for s in segments:
        for x in s["readings"]:
            for q in x["codes"]:
                tiers[x["model"]][q["tier"]] += 1
    pooled = results["rubric_pooled"]["all_segments"]["overall"]

    inputs = ["data/derived/answer_key.jsonl", "analysis/embeddings.jsonl", "analysis/results.json",
              "scoring/private/key.json", "scoring/scores/primary__XL.csv", "docs/quote_audit_main_review.md",
              "materials/sealed/SHA256SUMS.txt", config_path]
    run_files = sorted(str(p) for p in Path("runs/main").glob("*/run*/code*_a*.json"))
    remote = git("remote", "get-url", "origin") or ""
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote)
    repo_url = f"https://github.com/{m.group(1)}" if m else "https://github.com/cynthialiu1007-png/subtext-workbench"
    sealed = {}
    if Path("materials/sealed/SHA256SUMS.txt").exists():
        for line in Path("materials/sealed/SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            if line.strip():
                h, name = line.split(maxsplit=1)
                sealed[name.lstrip("*")] = h
    run_cfg = load_analysis_config("config/main.yaml")
    first = cells[(models[0], 1, segments[0]["code"])]
    data = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "repo": repo_url, "commit": git("rev-parse", "HEAD"), "models": models, "runs": runs,
        "compression": COMPRESSION, "replay": REPLAY, "scale": scale, "segments": segments,
        "results": {
            "pooled": pooled,
            "by_model": {mm: results["rubric_by_model"][mm]["all_segments"] for mm in models},
            "rq1_error": results["rq1_error"]["main"],
            "rq1_instability": results["rq1_instability"]["all_pairs"],
            "rq3_all": results["rq3"]["all_48__main"], "rq3_within_E": results["rq3"]["within_E__main"],
            "calibration": results["calibration"],
        },
        "quotes": {"tiers": {k: dict(v) for k, v in tiers.items()}, "review": quote_review()},
        "provenance": {
            "inputs": {p: sha(p) for p in inputs if Path(p).exists()},
            "run_records": {"n": len(run_files), "combined_sha256": hashlib.sha256(
                "".join(f"{p}\n{sha(p)}\n" for p in run_files).encode()).hexdigest()},
            "sealed": sealed,
            "models": {mm: {"digest": cells[(mm, 1, segments[0]["code"])]["model_identity"]["digest"],
                            "quantization": cells[(mm, 1, segments[0]["code"])]["model_identity"]["details"].get("quantization_level"),
                            "parameters": cells[(mm, 1, segments[0]["code"])]["model_identity"]["details"].get("parameter_size")}
                       for mm in models},
            "ollama": first.get("backend_version"), "options": run_cfg["options"], "seeds": run_cfg["seeds"],
            "prompt_version": run_cfg["prompt_version"],
            "embedding": {"model": emeta["embedding_model"]["name"], "digest": emeta["embedding_model"]["digest"],
                          "prefix": emeta["prefix"]},
        },
    }
    html = TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = html.replace("/*__DATA__*/null", payload)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(html, encoding="utf-8")
    return {"out": out, "bytes": len(html.encode("utf-8")), "segments": len(segments),
            "readings": sum(len(s["readings"]) for s in segments)}
