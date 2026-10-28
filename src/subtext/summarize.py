"""Summarise archived runs. Validation is recomputed from the stored content, so the report
always reflects the current validator, not the one in force when the call was made."""
from __future__ import annotations

import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

from .materials import load_coder_inputs
from .validate import parse_json, validate_content


def _records(phase: str):
    root = Path("runs") / phase
    for p in sorted(root.glob("*/run*/code*_a*.json")):
        yield p, json.loads(p.read_text(encoding="utf-8"))


def _m(xs):
    xs = [x for x in xs if x is not None]
    return (round(st.mean(xs), 1), max(xs)) if xs else (None, None)


def summarize(phase: str, n_segments_full: int = 48) -> dict:
    inputs = load_coder_inputs()
    by_model = defaultdict(list)
    for p, rec in _records(phase):
        v = validate_content(rec["response"]["content"], rec["request"]["format"],
                             inputs[rec["code"]]["passage"])
        if rec["response"]["done_reason"] not in (None, "stop"):
            v["schema_ok"] = False
        rec["_v"] = v
        by_model[rec["model"]].append(rec)

    report = {}
    for model, recs in by_model.items():
        first = [r for r in recs if r["attempt"] == 0]
        cells = defaultdict(list)
        for r in recs:
            cells[(r["run"], r["code"])].append(r)
        final_ok = [max(rs, key=lambda r: r["attempt"]) for rs in cells.values()]
        final_ok = [r for r in final_ok if r["_v"]["schema_ok"]]
        tiers = Counter(q["tier"] for r in final_ok for q in r["_v"]["quotes"])
        speakers = Counter(q["speaker"] for r in final_ok for q in r["_v"]["quotes"] if q["speaker"])
        n_quotes = sum(tiers.values())
        out_tok = [r["response"]["usage"].get("eval_count") for r in recs]
        think_chars = [len(r["response"]["thinking"] or "") for r in recs]
        wall = [r["response"]["wall_seconds"] for r in recs]
        mean_wall = st.mean(wall) if wall else 0
        tones = Counter()
        confs = []
        for r in final_ok:
            obj, _ = parse_json(r["response"]["content"])
            tones[obj["tone"]] += 1
            confs.append(obj["confidence"])
        report[model] = {
            "digest": recs[0]["model_identity"]["digest"],
            "calls_total": len(recs),
            "cells (run x segment)": len(cells),
            "cells_with_valid_output": len(final_ok),
            "schema_violation_rate_first_attempt": round(
                sum(not r["_v"]["schema_ok"] for r in first) / len(first), 3) if first else None,
            "schema_errors_seen": Counter(e.split(":")[0] if e.startswith("json") else e
                                          for r in recs for e in r["_v"]["schema_errors"]).most_common(8),
            "done_reasons": Counter(r["response"]["done_reason"] for r in recs),
            "form_issues": Counter(("quote_over_30_words" if ".quote" in i else
                                    "label_word_count" if ".label" in i else i)
                                   for r in final_ok for i in r["_v"]["form_issues"]),
            "quote_tiers": dict(tiers),
            "fabricated_rate (absent / quotes)": round(tiers["absent"] / n_quotes, 3) if n_quotes else None,
            "quote_speaker": dict(speakers),
            "output_tokens mean/max": _m(out_tok),
            "thinking_chars mean/max": _m(think_chars),
            "wall_seconds mean/max": _m(wall),
            "est_hours per run of 48 segments": round(mean_wall * n_segments_full / 3600, 2),
            "tone": dict(tones),
            "confidence mean/min/max": (round(st.mean(confs), 1), min(confs), max(confs)) if confs else None,
        }
    return report


def print_report(report: dict):
    for model, r in report.items():
        print(f"\n=== {model}")
        for k, v in r.items():
            print(f"  {k:<40} {v}")
