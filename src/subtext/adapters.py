"""Model adapter layer. Every model call goes through ModelAdapter.generate(), so a new backend
(another local server, a commercial API) is added by writing one subclass and naming it in the config.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Result:
    content: str                      # the answer text (expected to be JSON)
    thinking: str | None              # reasoning trace if the backend returns it separately
    done_reason: str | None           # "stop", "length", ...
    usage: dict = field(default_factory=dict)    # token counts and durations
    raw: dict = field(default_factory=dict)      # the backend's full response body
    wall_seconds: float = 0.0


class ModelAdapter:
    def identity(self, model: str) -> dict:
        """Return everything needed to pin the model version (name, digest, size, ...)."""
        raise NotImplementedError

    def backend_version(self) -> str:
        raise NotImplementedError

    def generate(self, model: str, system: str, user: str, schema: dict, options: dict,
                 think: bool) -> Result:
        raise NotImplementedError


class OllamaAdapter(ModelAdapter):
    def __init__(self, host: str = "http://localhost:11434", timeout: int = 1800,
                 keep_alive: str = "30m"):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.keep_alive = keep_alive

    def _get(self, path):
        with urllib.request.urlopen(self.host + path, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def _post(self, path, body):
        req = urllib.request.Request(self.host + path, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama HTTP {e.code}: {e.read().decode('utf-8', 'replace')}") from e

    def backend_version(self) -> str:
        return self._get("/api/version").get("version", "unknown")

    def identity(self, model: str) -> dict:
        for m in self._get("/api/tags").get("models", []):
            if m.get("name") == model or m.get("model") == model:
                return {"name": m.get("name"), "digest": m.get("digest"), "size": m.get("size"),
                        "modified_at": m.get("modified_at"), "details": m.get("details", {})}
        raise RuntimeError(f"Model {model!r} not found locally. Run: ollama pull {model}")

    def generate(self, model, system, user, schema, options, think) -> Result:
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "format": schema,
            "think": think,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": options,
        }
        t0 = time.time()
        resp = self._post("/api/chat", body)
        wall = time.time() - t0
        msg = resp.get("message", {})
        usage = {k: resp.get(k) for k in ["prompt_eval_count", "eval_count", "total_duration",
                                          "load_duration", "prompt_eval_duration", "eval_duration"]}
        return Result(content=msg.get("content", ""), thinking=msg.get("thinking"),
                      done_reason=resp.get("done_reason"), usage=usage, raw=resp, wall_seconds=wall)


ADAPTERS = {"ollama": OllamaAdapter}


def make_adapter(cfg: dict) -> ModelAdapter:
    kind = cfg.get("backend", "ollama")
    params = {k: v for k, v in cfg.items() if k != "backend"}
    return ADAPTERS[kind](**params)
