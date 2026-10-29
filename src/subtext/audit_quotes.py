"""Read-only audit of quotes classified as `absent` (analysis plan Section 4; handoff 20.2).

python -m subtext audit-quotes --phase main [--out docs/quote_audit_main.md]

For every quote that the validator classifies as `absent` in the outputs used for analysis, the
report shows the quote, the closest window of the passage, and diagnostics that bear on whether
the classification is right:

  in_prompt_outside_passage  the quote matches the "Interviewee details" line or another part of
                             the user message that is not the passage (the validator only checks
                             the passage)
  word_sequence_in_passage   the quote's words occur contiguously in the passage once punctuation
                             is ignored (a punctuation-only difference)
  clause_fragments           the quote split at clause punctuation; for each fragment of 3+ words,
                             whether its word sequence occurs in the passage
  word_coverage              share of the quote's words that occur in the passage, in order
  other_segment              the quote's word sequence occurs in a different segment's passage

`suggested` is a heuristic summary for the reviewer, not a classification. Nothing is written
unless --out is given, and no tier is changed: any change to the classification rules is a
deviation and is recorded separately (analysis plan Section 8).
"""
from __future__ import annotations

import difflib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .materials import load_coder_inputs
from .validate import normalise, parse_json, validate_content

WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
CLAUSE = re.compile(r"[,;:.!?()\"]|\s-\s|\.\.\.")


def words(text: str) -> list:
    return WORD.findall(normalise(text).casefold())


def seq_in(q: list, p: list) -> bool:
    if not q:
        return False
    return f" {' '.join(q)} " in f" {' '.join(p)} "


def best_window(q: list, passage: str) -> tuple:
    """Most similar word window of the passage, returned with its original text."""
    norm = normalise(passage)
    spans = [(m.start(), m.end(), m.group()) for m in WORD.finditer(norm.casefold())]
    p = [s[2] for s in spans]
    n, best, where = len(q), 0.0, (0, 0)
    for size in range(max(1, n - 3), n + 4):
        for i in range(0, max(1, len(p) - size + 1)):
            r = difflib.SequenceMatcher(None, q, p[i:i + size]).ratio()
            if r > best:
                best, where = r, (i, min(i + size, len(p)))
    if not spans:
        return 0.0, "", None
    a, b = where
    start, end = spans[a][0], spans[b - 1][1]
    before = norm[:start]
    speaker = "interviewer" if before.rfind("Interviewer:") > before.rfind("Interviewee:") else "interviewee"
    return round(best, 3), norm[start:end], speaker


def ordered_coverage(q: list, p: list) -> float:
    if not q:
        return 0.0
    blocks = difflib.SequenceMatcher(None, q, p, autojunk=False).get_matching_blocks()
    return round(sum(b.size for b in blocks) / len(q), 3)


def suggest(d: dict) -> str:
    if d["in_prompt_outside_passage"]:
        return "source outside the passage (prompt text)"
    if d["word_sequence_in_passage"]:
        return "punctuation-only difference"
    frags = d["clause_fragments"]
    if len(frags) >= 2 and all(f["found"] for f in frags):
        return "clause-level stitching of passage text"
    if d["other_segment"]:
        return "text from another segment"
    if d["best_similarity"] >= 0.80 or d["word_coverage"] >= 0.85:
        return "close wording variant"
    if d["word_coverage"] >= 0.6:
        return "partial paraphrase of passage text"
    return "not supported by the passage"


def audit(phase: str) -> dict:
    inputs = load_coder_inputs()
    cells = defaultdict(list)
    for p in sorted((Path("runs") / phase).glob("*/run*/code*_a*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        rec["_path"] = str(p)
        cells[(rec["model"], rec["run"], rec["code"])].append(rec)
    key_ids = {}
    ak = Path("data/derived/answer_key.jsonl")
    if ak.exists():
        for line in ak.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            key_ids[row["code"]] = row["id"]

    passages_words = {c: words(v["passage"]) for c, v in inputs.items()}
    tiers, items = defaultdict(Counter), []
    for (model, run, code), recs in sorted(cells.items()):
        rec = max(recs, key=lambda r: r["attempt"])
        v = validate_content(rec["response"]["content"], rec["request"]["format"], inputs[code]["passage"])
        if rec["response"]["done_reason"] not in (None, "stop") or not v["schema_ok"]:
            continue
        obj, _ = parse_json(rec["response"]["content"])
        user_words = words(rec["request"]["user"])
        pw = passages_words[code]
        for i, (qres, c) in enumerate(zip(v["quotes"], obj["codes"])):
            tiers[model][qres["tier"]] += 1
            if qres["tier"] != "absent":
                continue
            q = words(c["quote"])
            sim, window, speaker = best_window(q, inputs[code]["passage"])
            frags = []
            for f in CLAUSE.split(normalise(c["quote"])):
                fw = words(f)
                if len(fw) >= 3:
                    frags.append({"fragment": f.strip(), "found": seq_in(fw, pw)})
            d = {
                "model": model, "run": run, "code": code, "segment_id": key_ids.get(code),
                "quote_index": i, "label": c.get("label"), "quote": c["quote"], "n_words": len(q),
                "best_similarity": sim, "best_window": window, "best_window_speaker": speaker,
                "word_sequence_in_passage": seq_in(q, pw),
                "in_prompt_outside_passage": seq_in(q, user_words) and not seq_in(q, pw),
                "details_line": inputs[code]["details"],
                "word_coverage": ordered_coverage(q, pw),
                "clause_fragments": frags,
                "other_segment": [o for o, ow in passages_words.items() if o != code and seq_in(q, ow)],
                "file": rec["_path"],
            }
            d["suggested"] = suggest(d)
            items.append(d)
    return {"tiers": {m: dict(t) for m, t in tiers.items()}, "absent": items}


def to_markdown(res: dict, phase: str) -> str:
    L = [f"# Audit of absent quotes ({phase})", "",
         "Generated by `python -m subtext audit-quotes`. Read-only: no tier is changed here. "
         "`suggested` is a heuristic aid for the reviewer.", "", "## Tier counts (outputs used for analysis)", "",
         "| model | quotes | absent | " + " | ".join(["verbatim", "loose", "elided", "stitched", "near"]) + " |",
         "|---|---|---|---|---|---|---|---|"]
    for m, t in res["tiers"].items():
        L.append(f"| {m} | {sum(t.values())} | {t.get('absent', 0)} | " +
                 " | ".join(str(t.get(k, 0)) for k in ["verbatim", "loose", "elided", "stitched", "near"]) + " |")
    L += ["", "## Suggested categories", ""]
    for k, n in Counter(d["suggested"] for d in res["absent"]).most_common():
        L.append(f"- {k}: {n}")
    L += ["", "## Absent quotes", ""]
    for n, d in enumerate(res["absent"], 1):
        L += [f"### {n}. {d['model']} · run {d['run']} · code {d['code']} ({d['segment_id']}) · quote {d['quote_index'] + 1}",
              "", f"- label: {d['label']}", f"- quote ({d['n_words']} words): {d['quote']}",
              f"- closest passage window (similarity {d['best_similarity']}, {d['best_window_speaker']}): {d['best_window']}",
              f"- word sequence in passage (punctuation ignored): {d['word_sequence_in_passage']}",
              f"- in prompt outside passage: {d['in_prompt_outside_passage']} (details line: {d['details_line']})",
              f"- ordered word coverage: {d['word_coverage']}",
              f"- other segment: {', '.join(d['other_segment']) or 'none'}"]
        for f in d["clause_fragments"]:
            L.append(f"  - fragment {'FOUND' if f['found'] else 'not found'}: {f['fragment']}")
        L += [f"- suggested: **{d['suggested']}**", ""]
    return "\n".join(L) + "\n"
