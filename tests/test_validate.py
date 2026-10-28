import json, sys
sys.path.insert(0, "src")
from subtext.materials import load_coder_inputs
from subtext.validate import check_quote, validate_content
P = load_coder_inputs()
schema = json.load(open("prompts/v1/output_schema.json"))
p124, p101 = P["124"]["passage"], P["101"]["passage"]
cases = [
    ("verbatim curly",   "He’s very good at getting a room going.", p124, "verbatim"),
    ("straight apos",    "He's very good at getting a room going.", p124, "verbatim"),
    ("passage ellipsis", "a raise... in knowledge", p124, "verbatim"),
    ("speaker label",    "Interviewee: He's very good at getting a room going.", p124, "verbatim"),
    ("label, no period", "Interviewee: He's very good at getting a room going", p124, "verbatim"),
    ("case + period",    "he's very good at getting a room going", p124, "loose"),
    ("elided",           "Our manager is a really nice person ... He’s always punctual", p101, "elided"),
    ("stitched (reordered)", "I hope we get a result this year. Next month is the peak wedding season. Every weekend we’ll have three events, and everyone’s bound to start talking about this again.", P["112"]["passage"], "stitched"),
    ("not stitched", "I hope we get a result this year. The manager promised to fix it by Friday.", P["112"]["passage"], "absent"),
    ("near (1 word off)","His clothes are always tidy, his leather shoes are polished to a shine", p101, "near"),
    ("fabricated",       "You speak English like a tourist", p101, "absent"),
    ("interviewer line", "How does your restaurant manager usually lead the team?", p101, "verbatim"),
]
ok = True
for name, q, p, want in cases:
    r = check_quote(q, p)
    flag = "OK " if r["tier"] == want else "BAD"; ok &= r["tier"] == want
    print(f"{flag} {name:<22} tier={r['tier']:<9} speaker={r['speaker']} sim={r['similarity']}")
good = {"codes": [{"label": "praise for punctuality", "quote": "He’s always punctual."}]*3,
        "interpretation": "x", "tone": "positive", "confidence": 70}
bad = [dict(good, codes=good["codes"][:2]), dict(good, tone="sad"), dict(good, confidence=120),
       dict(good, confidence=7.5), {k: v for k, v in good.items() if k != "tone"}, dict(good, extra=1)]
print("valid:", validate_content(json.dumps(good), schema, p101)["schema_ok"])
for b in bad:
    v = validate_content(json.dumps(b), schema, p101); ok &= not v["schema_ok"]; print("invalid:", v["schema_errors"])
print("fenced:", validate_content("```json\n"+json.dumps(good)+"\n```", schema, p101)["parse_note"])
print("ALL PASS" if ok else "FAILURES")
