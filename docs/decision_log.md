# Decision log

## 2026-10-28
- Study materials sealed in the commit tagged seal-v1: segments and answer key, coding lists A/B, scoring rubric, Stage 1 scoring protocol.
- Stage 1 model configuration: local models only, qwen3:8b (ID 500a1f067a9f) and qwen3:14b (ID bdbd181c33f2). Reason: the planned Ollama cloud Qwen model had been retired, no Qwen model remained in the cloud catalog, and cloud models now require paid credits (see logs/2026-10-28_model_access.md). The comparison holds model family and generation constant and varies size only.
- Coding prompt v1 adopted (prompts/v1). Field order: codes, interpretation, tone, confidence. Quote limit: 30 words. Only the interpretation field is scored.
