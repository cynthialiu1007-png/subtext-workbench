"""Reproduction level 1: verify the record without running any model.

python -m subtext verify [--timeline-out docs/audit_timeline.md]

Checks (each PASS, FAIL or SKIP):
  sealed      materials/sealed/ matches SHA256SUMS.txt (seal-v1)
  derived     data/derived/ matches prepare_manifest.json, which records the sealed sources' hashes
  prompts     every run record was made with the committed prompt v1 (SHA-256 per file)
  runs        runs/main: 2 models x 5 runs x 48 segments, one schema-valid output per cell,
              one model digest per model, seeds as in config/main.yaml
  sheets      blind scoring sheets match scoring/sets_manifest.json
  key         the published response key matches the SHA-256 recorded before scoring began
  embeddings  analysis/embeddings.jsonl matches its meta file and the current interpretations
  analysis    the inputs recorded in analysis/analysis_manifest.json are unchanged
  timeline    the order of the key commits in the Git history (see below)

Commit times come from the committer's clock. GitHub push records and the archived release
(Zenodo DOI) are independent timestamps.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import yaml

RESULTS = []


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def record(name: str, status: str, detail: str = ""):
    RESULTS.append((name, status, detail))


def git(*args) -> str | None:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


# ---------------------------------------------------------------- checks

def check_sealed():
    if not Path("materials/sealed/SHA256SUMS.txt").exists():
        return record("sealed", "SKIP", "materials/sealed/ not present")
    from .materials import verify_sealed
    try:
        out = verify_sealed()
        record("sealed", "PASS", f"{len(out) if hasattr(out, '__len__') else ''} files match SHA256SUMS.txt")
    except Exception as e:
        record("sealed", "FAIL", str(e))


def check_derived():
    m = Path("data/derived/prepare_manifest.json")
    if not m.exists():
        return record("derived", "SKIP", "no prepare_manifest.json")
    man = json.loads(m.read_text(encoding="utf-8"))
    bad = [f for f, h in man["outputs_sha256"].items() if sha(Path("data/derived") / f) != h]
    sums = Path("materials/sealed/SHA256SUMS.txt")
    if sums.exists():
        listed = {}
        for line in sums.read_text(encoding="utf-8").splitlines():
            if line.strip():
                h, name = line.split(maxsplit=1)
                listed[Path(name.lstrip("*")).name] = h.lower()
        bad += [f"source {f}" for f, h in man["source_sha256"].items() if listed.get(f) != h]
    record("derived", "FAIL" if bad else "PASS",
           f"mismatch: {bad}" if bad else "coder inputs and answer key derive from the sealed files")


def check_runs():
    root = Path("runs/main")
    if not root.exists():
        return record("runs", "SKIP", "runs/main not present")
    prompt_files = {"system": "prompts/v1/system_prompt.txt", "template": "prompts/v1/user_template.txt",
                    "schema": "prompts/v1/output_schema.json"}
    prompt_sha = {k: sha(p) for k, p in prompt_files.items()}
    cfg = yaml.safe_load(Path("config/main.yaml").read_text(encoding="utf-8"))
    seeds = cfg["seeds"]
    from .validate import parse_json
    cells, digests, prompt_bad, seed_bad = defaultdict(list), defaultdict(set), 0, 0
    for p in root.glob("*/run*/code*_a*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        cells[(rec["model"], rec["run"], rec["code"])].append(rec)
        digests[rec["model"]].add((rec.get("model_identity") or {}).get("digest"))
        if rec.get("prompt_sha256") and any(rec["prompt_sha256"].get(k) not in (None, v) for k, v in prompt_sha.items()):
            prompt_bad += 1
        base = seeds[int(rec["run"]) - 1]
        if rec["seed"] not in [base] + [base + o for o in cfg.get("retry_seed_offsets", [])]:
            seed_bad += 1
    valid = Counter()
    for (m, r, c), recs in cells.items():
        ok = [x for x in recs if x["validation"]["schema_ok"]]
        if len(ok) == 1 and parse_json(ok[0]["response"]["content"])[0] is not None:
            valid[m] += 1
    expected = {m["name"]: m["runs"] * 48 for m in cfg["models"]}
    problems = []
    for m, n in expected.items():
        if valid[m] != n:
            problems.append(f"{m}: {valid[m]}/{n} valid cells")
        if len(digests[m]) != 1:
            problems.append(f"{m}: {len(digests[m])} digests")
    if prompt_bad:
        problems.append(f"{prompt_bad} records with a different prompt hash")
    if seed_bad:
        problems.append(f"{seed_bad} records with an unexpected seed")
    record("prompts", "FAIL" if prompt_bad else "PASS", "all records made with prompts/v1 as committed")
    record("runs", "FAIL" if problems else "PASS",
           "; ".join(problems) or ", ".join(f"{m} {valid[m]} cells, digest {next(iter(digests[m]))[:12]}"
                                         for m in expected))


def check_scoring():
    m = Path("scoring/sets_manifest.json")
    if not m.exists():
        return record("sheets", "SKIP", "no sets_manifest.json")
    man = json.loads(m.read_text(encoding="utf-8"))
    bad = [n for n, h in man["sheets_sha256"].items() if sha(Path("scoring/sheets") / f"{n}.jsonl") != h]
    record("sheets", "FAIL" if bad else "PASS", f"mismatch: {bad}" if bad else "practice, primary, second")
    key = Path(man.get("key_file", "scoring/private/key.json"))
    if not key.exists():
        record("key", "SKIP", f"{key} not present")
    else:
        ok = sha(key) == man["key_sha256"]
        record("key", "PASS" if ok else "FAIL",
               "matches the SHA-256 recorded when the sets were made" if ok else "SHA-256 differs from manifest")


def check_embeddings():
    meta = Path("analysis/embeddings_meta.json")
    if not meta.exists():
        return record("embeddings", "SKIP", "no embedding cache")
    from .embed import load_analysis_config, load_embeddings, valid_cells
    cfg = load_analysis_config("config/analysis.yaml")
    try:
        vecs, m = load_embeddings(cfg, valid_cells(cfg["phase"]))
        record("embeddings", "PASS", f"{len(vecs)} vectors, {m['embedding_model']['name']} "
                                      f"{m['embedding_model']['digest'][:12]}, prefix {m['prefix']!r}")
    except Exception as e:
        record("embeddings", "FAIL", str(e))


def check_analysis():
    m = Path("analysis/analysis_manifest.json")
    if not m.exists():
        return record("analysis", "SKIP", "no analysis manifest")
    man = json.loads(m.read_text(encoding="utf-8"))
    changed = [p for p, h in man["inputs_sha256"].items() if not Path(p).exists() or sha(p) != h]
    record("analysis", "FAIL" if changed else "PASS",
           f"inputs changed since the committed analysis: {changed}" if changed
           else f"{len(man['inputs_sha256'])} inputs unchanged since the committed analysis")


# ---------------------------------------------------------------- timeline

EVENTS = [
    ("seal", "Sealed segments, answer key, coding lists, rubric and scoring protocol", "tag:seal-v1"),
    ("prompt", "Coding prompt v1 committed", "prompts/v1/system_prompt.txt"),
    ("pilot", "Pilot outputs (calibration practice only)", "runs/pilot"),
    ("plan", "Analysis plan v1 committed", "docs/analysis_plan_v1.md"),
    ("main_runs", "Main-run outputs committed", "runs/main"),
    ("sets", "Blind scoring sets; response-key SHA-256 recorded", "scoring/sets_manifest.json"),
    ("calibration", "Calibration-order deviation recorded", "docs/deviation_2026-10-28_calibration_order.md"),
    ("primary_scores", "Primary scores (XL, pre-discussion)", "scoring/scores/primary__XL.csv"),
    ("module7", "Analysis code, unblinding deviation and RQ3 addendum", "docs/addendum_2026-10-29_rq3_within_E.md"),
    ("embeddings", "Interpretation embeddings cached", "analysis/embeddings.jsonl"),
    ("results", "Stage 1 analysis results", "analysis/results.json"),
    ("key_published", "Response key published", "scoring/private/key.json"),
]
ORDER = [("seal", "prompt"), ("seal", "pilot"), ("seal", "main_runs"), ("plan", "main_runs"),
         ("main_runs", "sets"), ("sets", "primary_scores"), ("calibration", "primary_scores"),
         ("primary_scores", "module7"), ("module7", "embeddings"), ("embeddings", "results"),
         ("module7", "results"), ("results", "key_published")]


def first_commit(target: str):
    if target.startswith("tag:"):
        h = git("rev-list", "-n", "1", target[4:])
    else:
        out = git("log", "--diff-filter=A", "--format=%H", "--reverse", "--", target)
        h = out.splitlines()[0] if out else None
    if not h:
        return None
    line = git("show", "-s", "--format=%h|%cI|%s", h)
    short, date, subject = line.split("|", 2)
    return {"hash": h, "short": short, "date": date, "subject": subject,
            "pos": int(git("rev-list", "--count", h))}


def timeline() -> list:
    if git("rev-parse", "--is-inside-work-tree") != "true":
        record("timeline", "SKIP", "not a Git repository (e.g. an archive download)")
        return []
    rows = {name: (desc, first_commit(t)) for name, desc, t in EVENTS}
    bad = []
    for a, b in ORDER:
        ca, cb = rows[a][1], rows[b][1]
        if ca and cb and not ca["pos"] < cb["pos"]:
            bad.append(f"{a} is not before {b}")
    # the key hash recorded when the sets were made has never changed
    s = rows["sets"][1]
    if s:
        first = json.loads(git("show", f"{s['hash']}:scoring/sets_manifest.json") or "{}").get("key_sha256")
        now = json.loads(Path("scoring/sets_manifest.json").read_text(encoding="utf-8"))["key_sha256"]
        if first != now:
            bad.append("key SHA-256 in sets_manifest.json changed after it was first committed")
    missing = [n for n, (_, c) in rows.items() if c is None]
    record("timeline", "FAIL" if bad else "PASS",
           "; ".join(bad) or f"{len(ORDER)} ordering checks hold"
           + (f"; not yet in history: {', '.join(missing)}" if missing else ""))
    return [(n, d, c) for n, (d, c) in rows.items()]


def timeline_md(rows: list) -> str:
    L = ["# Audit timeline", "",
         "Generated by `python -m subtext verify --timeline-out docs/audit_timeline.md`. Each row is the first "
         "commit that added the listed file (or the tagged commit). Times are committer times in the committer's "
         "time zone; GitHub push records and the archived release provide independent timestamps.", "",
         "| # | event | commit | committed | commit message |", "|---|---|---|---|---|"]
    for i, (n, d, c) in enumerate(rows, 1):
        if c:
            L.append(f"| {i} | {d} | `{c['short']}` | {c['date']} | {c['subject']} |")
        else:
            L.append(f"| {i} | {d} | – | – | not yet committed |")
    L += ["", "Ordering checks: " + ", ".join(f"{a} before {b}" for a, b in ORDER) + "."]
    return "\n".join(L) + "\n"


def run_verify(timeline_out: str | None = None) -> bool:
    RESULTS.clear()
    for f in (check_sealed, check_derived, check_runs, check_scoring, check_embeddings, check_analysis):
        try:
            f()
        except Exception as e:
            record(f.__name__.replace("check_", ""), "FAIL", f"{type(e).__name__}: {e}")
    rows = timeline()
    for name, status, detail in RESULTS:
        print(f"  {status:<5} {name:<11} {detail}")
    if rows:
        print()
        for n, d, c in rows:
            print(f"  {c['short'] if c else '-------':<8} {c['date'][:19] if c else '':<20} {d}")
        if timeline_out:
            Path(timeline_out).write_text(timeline_md(rows), encoding="utf-8")
            print(f"\n  timeline written to {timeline_out}")
    ok = not any(s == "FAIL" for _, s, _ in RESULTS)
    print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
    return ok
