"""Verify the sealed materials and derive machine-readable files from them.

Derived files are produced only by this script, never edited by hand:
  data/derived/coder_inputs.jsonl  what a coder may see: code, list, details, passage
  data/derived/answer_key.jsonl    scorer-only: answer-key fields keyed by code
  data/derived/prepare_manifest.json  source hashes and the results of every check
"""
import hashlib
import json
import re
from pathlib import Path

from docx import Document

SEALED = Path("materials/sealed")
DERIVED = Path("data/derived")
MASTER = "segments_and_answer_key.docx"
LISTS = {"A": "coding_list_A.docx", "B": "coding_list_B.docx"}

HEADER_RE = re.compile(
    r"^\[(Experimental|Control) version (E|C) \| List (A|B) \| Code (\d{3}) \| (\d+) words\]$"
)
SEGMENT_RE = re.compile(r"^Segment (\d{3})$")
PASSAGE_PREFIXES = ("Interviewer:", "Interviewee:", "[Earlier in the interview]", "[Later in the interview]")
KEY_FIELDS = [
    "id", "pair_id", "layer", "level", "version", "list", "code",
    "surface_meaning", "intended_meaning", "key_cues",
    "surface_valence", "intended_valence", "author_confidence", "notes",
]
# Strings that must never appear in a coder-facing list.
LEAK_MARKERS = ["intended_meaning", "surface_meaning", "key_cues", "Experimental version",
                "Control version", "answer key"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sealed() -> dict:
    """Compare every file listed in SHA256SUMS.txt with its current hash. Raise on any mismatch."""
    sums_path = SEALED / "SHA256SUMS.txt"
    expected = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, name = line.split(maxsplit=1)
        expected[Path(name.lstrip("*")).name] = digest.lower()
    results = {}
    for name, digest in expected.items():
        actual = sha256(SEALED / name)
        results[name] = {"expected": digest, "actual": actual, "ok": actual == digest}
    bad = [n for n, r in results.items() if not r["ok"]]
    if bad:
        raise RuntimeError(f"Sealed files do not match SHA256SUMS.txt: {bad}")
    for required in [MASTER, *LISTS.values()]:
        if required not in expected:
            raise RuntimeError(f"{required} is not listed in SHA256SUMS.txt")
    return results


def _paragraphs(path: Path):
    return [p.text.strip() for p in Document(path).paragraphs]


def parse_list(path: Path) -> dict:
    segs, cur = {}, None
    for p in _paragraphs(path):
        m = SEGMENT_RE.match(p)
        if m:
            cur = m.group(1)
            segs[cur] = {"details": None, "lines": []}
        elif cur is None or not p:
            continue
        elif p.startswith("Interviewee details:"):
            segs[cur]["details"] = p.split(":", 1)[1].strip()
        else:
            segs[cur]["lines"].append(p)
    return segs


def parse_master(path: Path):
    doc = Document(path)
    blocks, cur = [], None
    for p in (x.text.strip() for x in doc.paragraphs):
        m = HEADER_RE.match(p)
        if m:
            cur = {"version": m.group(2), "list": m.group(3), "code": m.group(4),
                   "words_declared": int(m.group(5)), "lines": []}
            blocks.append(cur)
        elif cur is not None and p.startswith(PASSAGE_PREFIXES):
            cur["lines"].append(p)
        elif cur is not None and p:
            cur = None
    keys = []
    for t in doc.tables:
        row = {r.cells[0].text.strip(): r.cells[1].text for r in t.rows if len(r.cells) >= 2}
        if "id" in row:
            keys.append(row)
    return blocks, keys


def format_passage(lines) -> str:
    """Plain-text passage: one paragraph per line, separated by a blank line."""
    return "\n\n".join(lines)


def _clean_key(row: dict) -> dict:
    out = {}
    for f in KEY_FIELDS:
        v = row.get(f, "").strip()
        if f == "key_cues":
            v = [c.strip() for c in v.split("\n") if c.strip() and c.strip() != "—"]
        out[f] = v
    out["version"] = out["version"][0]  # "E (experimental version)" -> "E"
    return out


def prepare() -> dict:
    hashes = verify_sealed()
    lists = {L: parse_list(SEALED / fn) for L, fn in LISTS.items()}
    blocks, keys = parse_master(SEALED / MASTER)
    checks = {}

    checks["master_segments"] = len(blocks)
    checks["master_key_tables"] = len(keys)
    checks["list_sizes"] = {L: len(s) for L, s in lists.items()}
    assert len(blocks) == 48 and len(keys) == 48, "expected 48 segments and 48 answer-key tables"
    assert all(len(s) == 24 for s in lists.values()), "expected 24 segments per list"

    coder_inputs, answer_key, text_mismatch = [], [], []
    for b, row in zip(blocks, keys):
        k = _clean_key(row)
        assert (b["code"], b["version"], b["list"]) == (k["code"], k["version"], k["list"]), k["id"]
        seg = lists[b["list"]][b["code"]]
        if seg["lines"] != b["lines"]:
            text_mismatch.append(k["id"])
        passage = format_passage(seg["lines"])
        coder_inputs.append({"code": b["code"], "list": b["list"],
                             "details": seg["details"], "passage": passage})
        answer_key.append({**k, "details": seg["details"], "passage": passage,
                           "words_declared": b["words_declared"]})
    checks["list_text_equals_master_text"] = not text_mismatch
    assert not text_mismatch, f"list text differs from master text: {text_mismatch}"

    ids = [a["id"] for a in answer_key]
    assert len(set(ids)) == 48 and len({a["code"] for a in answer_key}) == 48
    pairs = {}
    for a in answer_key:
        pairs.setdefault(a["pair_id"], {})[a["version"]] = a
    assert len(pairs) == 24 and all(set(v) == {"E", "C"} for v in pairs.values())
    assert all(v["E"]["list"] != v["C"]["list"] for v in pairs.values()), "pair versions share a list"

    l3 = {}
    for pid, v in pairs.items():
        if "-L3-" in pid:
            tgt = [p.split("[Later in the interview]", 1)[1] for p in (v["E"]["passage"], v["C"]["passage"])]
            l3[pid] = tgt[0] == tgt[1]
    checks["l3_target_identical"] = l3
    assert all(l3.values()) and len(l3) == 8

    leaks = {}
    for L, fn in LISTS.items():
        text = "\n".join(_paragraphs(SEALED / fn))
        found = [m for m in LEAK_MARKERS if m in text]
        found += [i for i in ids if i in text]
        if found:
            leaks[L] = found
    checks["answer_fields_in_lists"] = leaks or "none"
    assert not leaks, f"answer-key content found in coding lists: {leaks}"

    DERIVED.mkdir(parents=True, exist_ok=True)
    coder_inputs.sort(key=lambda r: r["code"])
    answer_key.sort(key=lambda r: r["code"])
    with open(DERIVED / "coder_inputs.jsonl", "w", encoding="utf-8") as f:
        for r in coder_inputs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(DERIVED / "answer_key.jsonl", "w", encoding="utf-8") as f:
        for r in answer_key:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    manifest = {
        "source_sha256": {n: r["actual"] for n, r in hashes.items()},
        "checks": checks,
        "outputs_sha256": {n: sha256(DERIVED / n) for n in ["coder_inputs.jsonl", "answer_key.jsonl"]},
    }
    (DERIVED / "prepare_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                                   encoding="utf-8")
    return manifest


def load_coder_inputs() -> dict:
    with open(DERIVED / "coder_inputs.jsonl", encoding="utf-8") as f:
        return {r["code"]: r for r in map(json.loads, f)}
