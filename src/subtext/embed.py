"""Embeddings of the interpretation field, computed once and cached.

python -m subtext embed --config config/analysis.yaml

For every schema-valid (model, run, code) cell of the phase, the `interpretation` text is embedded
with the configured Ollama embedding model, after prepending the configured task prefix.
The cache makes the analysis reproducible without Ollama:

  analysis/embeddings.jsonl       one row per cell: model, run, code, text_sha256, embedding
  analysis/embeddings_meta.json   embedding model, digest, Ollama version, prefix, repeat check,
                                  SHA-256 of embeddings.jsonl

The cache is written once. It is never overwritten unless --force is given; a forced rebuild is
recorded in the meta file.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import urllib.request
from pathlib import Path

import yaml

from .validate import parse_json


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_analysis_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cell_key(model: str, run: int, code: str) -> str:
    return f"{model}|{run}|{code}"


def valid_cells(phase: str) -> dict:
    """{(model, run, code): record} for the schema-valid attempt of every cell in a phase."""
    cells = {}
    for p in sorted((Path("runs") / phase).glob("*/run*/code*_a*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if not rec["validation"]["schema_ok"]:
            continue
        k = (rec["model"], int(rec["run"]), rec["code"])
        if k in cells:
            raise RuntimeError(f"two schema-valid attempts for {k}: {cells[k]['_path']} and {p}")
        obj, _ = parse_json(rec["response"]["content"])
        rec["_obj"], rec["_path"] = obj, str(p)
        cells[k] = rec
    return cells


class OllamaEmbedder:
    def __init__(self, host: str, model: str, timeout: int = 600):
        self.host, self.model, self.timeout = host.rstrip("/"), model, timeout

    def _get(self, path):
        with urllib.request.urlopen(self.host + path, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def version(self) -> str:
        return self._get("/api/version").get("version", "unknown")

    def identity(self) -> dict:
        wanted = {self.model, self.model + ":latest"}
        for m in self._get("/api/tags").get("models", []):
            if m.get("name") in wanted or m.get("model") in wanted:
                return {"name": m.get("name"), "digest": m.get("digest"), "size": m.get("size"),
                        "details": m.get("details", {})}
        raise RuntimeError(f"Embedding model {self.model!r} not found locally. Run: ollama pull {self.model}")

    def embed(self, texts: list) -> list:
        body = {"model": self.model, "input": texts}
        req = urllib.request.Request(self.host + "/api/embed", data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            out = json.loads(r.read().decode("utf-8"))
        vecs = out.get("embeddings")
        if not vecs or len(vecs) != len(texts):
            raise RuntimeError(f"unexpected /api/embed response: {str(out)[:300]}")
        return vecs


def run_embed(config_path: str, force: bool = False) -> dict:
    cfg = load_analysis_config(config_path)
    ecfg = cfg["embedding"]
    out_dir = Path(cfg["outputs"]["dir"])
    cache, meta_path = out_dir / "embeddings.jsonl", out_dir / "embeddings_meta.json"
    if cache.exists() and not force:
        raise RuntimeError(f"{cache} already exists. Embeddings are computed once; "
                           "use --force only for a recorded reason.")
    previous_meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else None

    cells = valid_cells(cfg["phase"])
    if not cells:
        raise RuntimeError(f"no schema-valid records under runs/{cfg['phase']}/")
    emb = OllamaEmbedder(ecfg["host"], ecfg["model"], ecfg.get("timeout", 600))
    ident, version = emb.identity(), emb.version()
    prefix = ecfg.get("prefix", "")
    keys = sorted(cells)
    texts = [cells[k]["_obj"]["interpretation"] for k in keys]

    vectors = []
    bs = int(ecfg.get("batch_size", 16))
    for i in range(0, len(texts), bs):
        if emb.identity()["digest"] != ident["digest"]:
            raise RuntimeError("embedding model digest changed during the run")
        vectors.extend(emb.embed([prefix + t for t in texts[i:i + bs]]))
        print(f"  embedded {min(i + bs, len(texts))}/{len(texts)}", flush=True)

    n_rep = min(int(ecfg.get("repeat_check", 5)), len(texts))
    again = emb.embed([prefix + t for t in texts[:n_rep]]) if n_rep else []
    max_abs = max((abs(a - b) for v1, v2 in zip(vectors, again) for a, b in zip(v1, v2)), default=0.0)

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for k, t, v in zip(keys, texts, vectors):
            model, run, code = k
            f.write(json.dumps({"key": cell_key(*k), "model": model, "run": run, "code": code,
                                "text_sha256": text_sha(t), "dim": len(v), "embedding": v}) + "\n")
    tmp.replace(cache)
    meta = {
        "created_at": now(), "phase": cfg["phase"], "n": len(keys),
        "embedding_model": ident, "ollama_version": version, "prefix": prefix,
        "text_field": "interpretation", "dim": len(vectors[0]),
        "repeat_check": {"n": n_rep, "max_abs_difference": max_abs,
                         "identical": max_abs == 0.0},
        "embeddings_sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
    }
    if previous_meta:
        meta["replaces"] = {"created_at": previous_meta.get("created_at"),
                            "embeddings_sha256": previous_meta.get("embeddings_sha256")}
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def load_embeddings(cfg: dict, cells: dict) -> dict:
    """Read the cache and check it against the current records. Returns ({cell: unit vector}, meta)."""
    out_dir = Path(cfg["outputs"]["dir"])
    cache, meta_path = out_dir / "embeddings.jsonl", out_dir / "embeddings_meta.json"
    if not cache.exists():
        raise RuntimeError(f"{cache} not found. Run: python -m subtext embed --config <analysis.yaml>")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if hashlib.sha256(cache.read_bytes()).hexdigest() != meta["embeddings_sha256"]:
        raise RuntimeError(f"{cache} does not match the SHA-256 in {meta_path}")
    vecs = {}
    with open(cache, encoding="utf-8") as f:
        for row in map(json.loads, f):
            k = (row["model"], int(row["run"]), row["code"])
            if k not in cells:
                raise RuntimeError(f"cached embedding for unknown cell {k}")
            if row["text_sha256"] != text_sha(cells[k]["_obj"]["interpretation"]):
                raise RuntimeError(f"interpretation text changed since embedding: {k}")
            v = row["embedding"]
            norm = math.sqrt(sum(x * x for x in v))
            vecs[k] = [x / norm for x in v]
    missing = set(cells) - set(vecs)
    if missing:
        raise RuntimeError(f"{len(missing)} cells have no cached embedding, e.g. {sorted(missing)[:3]}")
    return vecs, meta
