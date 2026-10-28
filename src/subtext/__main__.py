"""Command line entry point:  python -m subtext <command> [options]"""
import argparse
import json
import sys


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


if __name__ == "__main__":
    sys.exit(main())
