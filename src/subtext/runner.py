"""Coding runs.

Loop order is run-major: run 1 for every segment, then run 2, and so on. If a long run is
interrupted, the primary outcome (run 1) is complete first. Re-running the same command resumes:
a (model, run, segment) that already has a schema-valid attempt is skipped.

Each attempt is archived as one JSON file:
  runs/<phase>/<model>/run<k>/code<code>_a<attempt>.json
and every event is appended to runs/<phase>/run_log.jsonl.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

import yaml

from .adapters import make_adapter
from .materials import load_coder_inputs, sha256, verify_sealed
from .validate import validate_content

RECORD_VERSION = 1


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def slug(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for m in cfg["models"]:
        if m["runs"] > len(cfg["seeds"]):
            raise ValueError(f"{m['name']}: runs={m['runs']} but only {len(cfg['seeds'])} seeds listed")
    return cfg


def load_prompt(version: str) -> dict:
    d = Path("prompts") / version
    files = {"system": d / "system_prompt.txt", "template": d / "user_template.txt",
             "schema": d / "output_schema.json"}
    return {
        "version": version,
        "system": files["system"].read_text(encoding="utf-8"),
        "template": files["template"].read_text(encoding="utf-8"),
        "schema": json.loads(files["schema"].read_text(encoding="utf-8")),
        "sha256": {k: sha256(p) for k, p in files.items()},
    }


def build_user_message(template: str, seg: dict) -> str:
    # str.replace rather than str.format, so braces in a passage can never break substitution
    return template.replace("{details}", seg["details"]).replace("{passage}", seg["passage"])


def _write_atomic(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


class Runner:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.cfg = load_config(config_path)
        self.prompt = load_prompt(self.cfg["prompt_version"])
        self.adapter = make_adapter(self.cfg["backend"])
        self.out = Path("runs") / self.cfg["phase"]
        self.log_path = self.out / "run_log.jsonl"
        inputs = load_coder_inputs()
        codes = self.cfg["segments"]
        self.codes = sorted(inputs) if codes == "all" else [str(c) for c in codes]
        missing = [c for c in self.codes if c not in inputs]
        if missing:
            raise ValueError(f"unknown segment codes: {missing}")
        self.inputs = inputs

    def log(self, event: str, **kw):
        self.out.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": now(), "event": event, **kw}, ensure_ascii=False) + "\n")

    def seeds_for(self, run_idx: int) -> list:
        base = self.cfg["seeds"][run_idx]
        return [base] + [base + off for off in self.cfg.get("retry_seed_offsets", [])]

    def call(self, model: str, ident: dict, seg: dict, seed: int) -> dict:
        options = {**self.cfg["options"], "seed": seed}
        user = build_user_message(self.prompt["template"], seg)
        started = now()
        res = self.adapter.generate(model, self.prompt["system"], user, self.prompt["schema"],
                                    options, self.cfg.get("think", True))
        validation = validate_content(res.content, self.prompt["schema"], seg["passage"])
        if res.done_reason not in (None, "stop"):
            validation["schema_ok"] = False
            validation["schema_errors"].append(f"done_reason={res.done_reason}")
        return {
            "record_version": RECORD_VERSION,
            "phase": self.cfg["phase"], "config_file": self.config_path,
            "model": model, "model_identity": ident,
            "backend_version": self.adapter.backend_version(),
            "code": seg["code"], "list": seg["list"], "seed": seed,
            "prompt_version": self.prompt["version"], "prompt_sha256": self.prompt["sha256"],
            "request": {"system": self.prompt["system"], "user": user, "options": options,
                        "think": self.cfg.get("think", True), "format": self.prompt["schema"]},
            "response": {"content": res.content, "thinking": res.thinking,
                         "done_reason": res.done_reason, "usage": res.usage,
                         "wall_seconds": round(res.wall_seconds, 2)},
            "raw_response": res.raw,
            "validation": validation,
            "started_at": started, "finished_at": now(),
            "host": {"platform": platform.platform(), "python": sys.version.split()[0]},
        }

    def run_one(self, model: str, ident: dict, run_idx: int, code: str) -> str:
        run_dir = self.out / slug(model) / f"run{run_idx + 1}"
        existing = sorted(run_dir.glob(f"code{code}_a*.json"))
        for p in existing:
            if json.loads(p.read_text(encoding="utf-8"))["validation"]["schema_ok"]:
                return "skipped"
        seeds = self.seeds_for(run_idx)
        for attempt in range(len(existing), len(seeds)):
            current = self.adapter.identity(model)
            if current["digest"] != ident["digest"]:
                raise RuntimeError(f"{model} digest changed during the run: "
                                   f"{ident['digest']} -> {current['digest']}")
            try:
                rec = self.call(model, ident, self.inputs[code], seeds[attempt])
            except Exception as e:  # transport errors are not model output: log, leave no file
                self.log("call_error", model=model, run=run_idx + 1, code=code,
                         attempt=attempt, error=repr(e))
                return "error"
            rec["run"], rec["attempt"] = run_idx + 1, attempt
            _write_atomic(run_dir / f"code{code}_a{attempt}.json", rec)
            v = rec["validation"]
            self.log("attempt", model=model, run=run_idx + 1, code=code, attempt=attempt,
                     seed=seeds[attempt], schema_ok=v["schema_ok"], errors=v["schema_errors"][:3],
                     eval_count=rec["response"]["usage"].get("eval_count"),
                     wall_seconds=rec["response"]["wall_seconds"])
            if v["schema_ok"]:
                return "ok" if attempt == 0 else "ok_after_retry"
        self.log("exhausted", model=model, run=run_idx + 1, code=code)
        return "exhausted"

    def run(self, only_model: str | None = None):
        verify_sealed()
        self.log("start", config=self.cfg, prompt_sha256=self.prompt["sha256"])
        for m in self.cfg["models"]:
            model = m["name"]
            if only_model and model != only_model:
                continue
            ident = self.adapter.identity(model)
            self.log("model_identity", model=model, identity=ident,
                     backend_version=self.adapter.backend_version())
            print(f"== {model}  digest {ident['digest'][:12]}  runs={m['runs']}")
            for run_idx in range(m["runs"]):
                for i, code in enumerate(self.codes, 1):
                    status = self.run_one(model, ident, run_idx, code)
                    print(f"  run{run_idx + 1}  [{i:>2}/{len(self.codes)}]  code {code}  {status}",
                          flush=True)
        self.log("end")

    def determinism(self, model: str, code: str, seed: int, repeats: int = 2) -> dict:
        """Call the same model, segment and seed several times and compare the outputs."""
        ident = self.adapter.identity(model)
        outs = []
        for r in range(repeats):
            rec = self.call(model, ident, self.inputs[code], seed)
            rec["run"], rec["attempt"] = f"det{r + 1}", 0
            _write_atomic(self.out / "determinism" / slug(model) / f"code{code}_seed{seed}_r{r + 1}.json",
                          rec)
            outs.append(rec["response"])
        same_content = all(o["content"] == outs[0]["content"] for o in outs)
        same_thinking = all(o["thinking"] == outs[0]["thinking"] for o in outs)
        result = {"model": model, "digest": ident["digest"], "code": code, "seed": seed,
                  "repeats": repeats, "identical_content": same_content,
                  "identical_thinking": same_thinking,
                  "content_sha256": [hashlib.sha256(o["content"].encode()).hexdigest()[:16] for o in outs]}
        self.log("determinism", **result)
        return result
