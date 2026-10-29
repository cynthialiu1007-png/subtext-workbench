"""Command line entry point:  python -m subtext <command> [options]"""
import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="subtext")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare", help="verify sealed files and derive coder inputs and answer key")
    p = sub.add_parser("check-env", help="report Ollama version and model digests")
    p.add_argument("--config", required=True)
    p = sub.add_parser("run", help="run coding as specified in a config file (resumable)")
    p.add_argument("--config", required=True)
    p.add_argument("--model", help="run only this model")
    p = sub.add_parser("determinism", help="same model, segment and seed twice; compare outputs")
    p.add_argument("--config", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--code", required=True)
    p.add_argument("--seed", type=int, default=999)
    p = sub.add_parser("summarize", help="format, quote and length report for a phase")
    p.add_argument("--phase", required=True)
    p = sub.add_parser("make-sets", help="build blind scoring sets (once, after run 1 is complete)")
    p.add_argument("--seed", type=int, default=20261030, help="seed for the second-scorer sample")
    p.add_argument("--allow-missing", action="store_true")
    p = sub.add_parser("export-excel", help="write a scoring set as an Excel sheet")
    p.add_argument("--set", required=True, choices=["practice", "primary", "second"])
    p.add_argument("--out")
    p = sub.add_parser("import-excel", help="read a filled Excel sheet into a score file")
    p.add_argument("--file", required=True)
    p.add_argument("--set", required=True, choices=["practice", "primary", "second"])
    p.add_argument("--scorer", required=True)
    p = sub.add_parser("embed", help="embed interpretations once and cache them (needs Ollama)")
    p.add_argument("--config", default="config/analysis.yaml")
    p.add_argument("--force", action="store_true", help="rebuild an existing cache (record why)")
    p = sub.add_parser("analyze", help="module 7: instability, rubric metrics, RQ1-RQ3, agreement")
    p.add_argument("--config", default="config/analysis.yaml")
    p.add_argument("--deviation", help="committed deviation record allowing the key to be read "
                                       "before second scoring is complete")
    p = sub.add_parser("audit-quotes", help="read-only audit of quotes classified as absent")
    p.add_argument("--phase", default="main")
    p.add_argument("--out", help="also write the Markdown report to this file")
    p = sub.add_parser("verify", help="reproduction level 1: verify hashes, run records and Git timeline")
    p.add_argument("--timeline-out", help="write the audit timeline as Markdown (e.g. docs/audit_timeline.md)")
    a = ap.parse_args(argv)

    if a.cmd == "prepare":
        from .materials import prepare
        print(json.dumps(prepare()["checks"], indent=2, ensure_ascii=False))
        print("OK: data/derived/ written")
    elif a.cmd == "check-env":
        from .runner import Runner
        r = Runner(a.config)
        print("Ollama version:", r.adapter.backend_version())
        for m in r.cfg["models"]:
            ident = r.adapter.identity(m["name"])
            print(f"{m['name']:<12} digest {ident['digest']}  {ident.get('details', {})}")
    elif a.cmd == "run":
        from .runner import Runner
        Runner(a.config).run(only_model=a.model)
    elif a.cmd == "determinism":
        from .runner import Runner
        print(json.dumps(Runner(a.config).determinism(a.model, a.code, a.seed), indent=2))
    elif a.cmd == "summarize":
        from .summarize import print_report, summarize
        print_report(summarize(a.phase))
    elif a.cmd == "make-sets":
        from .scoring import make_sets
        print(json.dumps(make_sets(a.seed, allow_missing=a.allow_missing), indent=2))
    elif a.cmd == "export-excel":
        from .scoring import export_excel
        print("written:", export_excel(a.set, a.out))
    elif a.cmd == "import-excel":
        from .scoring import import_excel
        print(json.dumps(import_excel(a.file, a.set, a.scorer), indent=2))
    elif a.cmd == "embed":
        from .embed import run_embed
        print(json.dumps(run_embed(a.config, a.force), indent=2))
    elif a.cmd == "audit-quotes":
        from .audit_quotes import audit, to_markdown
        md = to_markdown(audit(a.phase), a.phase)
        print(md)
        if a.out:
            Path(a.out).write_text(md, encoding="utf-8")
    elif a.cmd == "verify":
        from .verify import run_verify
        sys.exit(0 if run_verify(a.timeline_out) else 1)
    elif a.cmd == "analyze":
        from .analysis import run_analysis
        print(json.dumps(run_analysis(a.config, a.deviation), indent=2))


if __name__ == "__main__":
    sys.exit(main())
