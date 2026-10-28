"""Post-hoc checks on model output. Nothing here depends on whether Ollama enforced the schema.

Three kinds of check, kept separate because they are treated differently:
  schema   : JSON parses and satisfies output_schema.json  -> a failure triggers the retry rule
  form     : rules stated in the prompt but not in the schema (label 2-6 words, quote <= 30 words)
             -> recorded only, never retried
  quotes   : each quote is checked against the passage      -> recorded only, never retried
"""
import difflib
import json
import re
import unicodedata

QUOTE_MAX_WORDS = 30
LABEL_MIN_WORDS, LABEL_MAX_WORDS = 2, 6
NEAR_MATCH_THRESHOLD = 0.90

# ---------------------------------------------------------------- schema

def parse_json(text: str):
    """Return (obj, error). Tolerates markdown fences but records that they were present."""
    raw = text.strip()
    fenced = raw.startswith("```")
    if fenced:
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    try:
        return json.loads(raw), ("fenced" if fenced else None)
    except json.JSONDecodeError as e:
        return None, f"json_decode_error: {e}"


def schema_errors(obj, schema: dict) -> list:
    """Minimal validator for the constructs used in output_schema.json."""
    errs = []

    def check(value, sch, path):
        t = sch.get("type")
        if t == "object":
            if not isinstance(value, dict):
                errs.append(f"{path}: expected object"); return
            for req in sch.get("required", []):
                if req not in value:
                    errs.append(f"{path}.{req}: missing")
            for k, sub in sch.get("properties", {}).items():
                if k in value:
                    check(value[k], sub, f"{path}.{k}")
            extra = set(value) - set(sch.get("properties", {}))
            if extra:
                errs.append(f"{path}: unexpected keys {sorted(extra)}")
        elif t == "array":
            if not isinstance(value, list):
                errs.append(f"{path}: expected array"); return
            if "minItems" in sch and len(value) < sch["minItems"]:
                errs.append(f"{path}: {len(value)} items < minItems {sch['minItems']}")
            if "maxItems" in sch and len(value) > sch["maxItems"]:
                errs.append(f"{path}: {len(value)} items > maxItems {sch['maxItems']}")
            for i, item in enumerate(value):
                check(item, sch.get("items", {}), f"{path}[{i}]")
        elif t == "string":
            if not isinstance(value, str):
                errs.append(f"{path}: expected string"); return
            if "enum" in sch and value not in sch["enum"]:
                errs.append(f"{path}: {value!r} not in enum")
        elif t == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                errs.append(f"{path}: expected integer"); return
            if "minimum" in sch and value < sch["minimum"]:
                errs.append(f"{path}: {value} < minimum {sch['minimum']}")
            if "maximum" in sch and value > sch["maximum"]:
                errs.append(f"{path}: {value} > maximum {sch['maximum']}")

    check(obj, schema, "$")
    return errs


def form_issues(obj: dict) -> list:
    issues = []
    for i, c in enumerate(obj.get("codes", [])):
        n_label = len(str(c.get("label", "")).split())
        if not LABEL_MIN_WORDS <= n_label <= LABEL_MAX_WORDS:
            issues.append(f"codes[{i}].label: {n_label} words")
        n_quote = len(str(c.get("quote", "")).split())
        if n_quote > QUOTE_MAX_WORDS:
            issues.append(f"codes[{i}].quote: {n_quote} words > {QUOTE_MAX_WORDS}")
    if not str(obj.get("interpretation", "")).strip():
        issues.append("interpretation: empty")
    return issues

# ---------------------------------------------------------------- quotes

_TYPO = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u2032": "'", "`": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u2033": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
    "\u2026": "...", "\u00a0": " ",
}
_SPEAKER = re.compile(r"^\s*(interviewer|interviewee)\s*:\s*", re.I)
_EDGE_PUNCT = " \t\n\"'.,;:!?()[]-"


def normalise(text: str) -> str:
    """Typographic normalisation only: quotes, apostrophes, dashes, ellipsis, whitespace."""
    text = unicodedata.normalize("NFC", text)
    for k, v in _TYPO.items():
        text = text.replace(k, v)
    return re.sub(r"\s+", " ", text).strip()


def _loose(text: str) -> str:
    return normalise(text).casefold().strip(_EDGE_PUNCT)


def _speaker_of(passage_norm: str, start: int) -> str:
    before = passage_norm[:start]
    i, j = before.rfind("Interviewer:"), before.rfind("Interviewee:")
    return "interviewer" if i > j else "interviewee"


def check_quote(quote: str, passage: str) -> dict:
    """Classify a quote against its passage.

    verbatim : found after typographic normalisation (case-sensitive)
    loose    : found after also case-folding, trimming edge punctuation and a leading speaker label
    elided   : contains '...' and every fragment is found, in order, at loose level
    near     : best word-window similarity >= NEAR_MATCH_THRESHOLD
    absent   : none of the above (counted as fabricated evidence)
    """
    p_norm = normalise(passage)
    q_norm = normalise(quote)
    res = {"quote": quote, "tier": "absent", "similarity": None, "speaker": None}
    if not q_norm:
        res["tier"] = "empty"; return res

    label = _SPEAKER.match(q_norm)
    pos = p_norm.find(q_norm)
    if pos >= 0:
        speaker = label.group(1).lower() if label else _speaker_of(p_norm, pos)
        res.update(tier="verbatim", speaker=speaker); return res

    p_loose = p_norm.casefold()
    q_loose = _loose(_SPEAKER.sub("", q_norm))
    if q_loose:
        pos = p_loose.find(q_loose)
        if pos >= 0:
            res.update(tier="loose", speaker=_speaker_of(p_norm, pos)); return res

    if "..." in q_norm:
        frags = [_loose(f) for f in q_norm.split("...")]
        frags = [f for f in frags if f]
        cursor, first = 0, None
        for f in frags:
            pos = p_loose.find(f, cursor)
            if pos < 0:
                break
            first = pos if first is None else first
            cursor = pos + len(f)
        else:
            if frags:
                res.update(tier="elided", speaker=_speaker_of(p_norm, first)); return res

    q_words, p_words = q_loose.split(), p_loose.split()
    best = 0.0
    n = len(q_words)
    if n:
        for size in range(max(1, n - 2), n + 3):
            for i in range(0, max(1, len(p_words) - size + 1)):
                r = difflib.SequenceMatcher(None, q_words, p_words[i:i + size]).ratio()
                if r > best:
                    best = r
    res["similarity"] = round(best, 3)
    if best >= NEAR_MATCH_THRESHOLD:
        res["tier"] = "near"
    return res

# ---------------------------------------------------------------- one response

def validate_content(content: str, schema: dict, passage: str) -> dict:
    obj, note = parse_json(content)
    out = {"parsed": obj is not None, "parse_note": note, "schema_errors": [],
           "form_issues": [], "quotes": [], "schema_ok": False}
    if obj is None:
        out["schema_errors"] = [note]
        return out
    out["schema_errors"] = schema_errors(obj, schema)
    out["schema_ok"] = not out["schema_errors"]
    if isinstance(obj, dict):
        out["form_issues"] = form_issues(obj)
        for c in obj.get("codes", []) if isinstance(obj.get("codes"), list) else []:
            if isinstance(c, dict) and isinstance(c.get("quote"), str):
                out["quotes"].append(check_quote(c["quote"], passage))
    return out
