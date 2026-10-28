# Decision log

## 2026-10-28
- Study materials sealed in the commit tagged seal-v1: segments and answer key, coding lists A/B, scoring rubric, Stage 1 scoring protocol.
- Stage 1 model configuration: local models only, qwen3:8b (ID 500a1f067a9f) and qwen3:14b (ID bdbd181c33f2). Reason: the planned Ollama cloud Qwen model had been retired, no Qwen model remained in the cloud catalog, and cloud models now require paid credits (see logs/2026-10-28_model_access.md). The comparison holds model family and generation constant and varies size only.
- Coding prompt v1 adopted (prompts/v1). Field order: codes, interpretation, tone, confidence. Quote limit: 30 words. Only the interpretation field is scored.
## 2026-10-28 Pilot run and decisions before the main run
- Pilot: segments 105, 112, 116; qwen3:8b and qwen3:14b; 2 runs each (seeds 901, 902). All 12 calls schema-valid at first attempt. Reasoning trace returned as a separate field. Same-seed check (8B, segment 105, seed 999): identical outputs.
- Mean time per call: 8B 38 s, 14B 57 s. Decision: 14B runs 5 times.
- Prompt v1 retained. 8B exceeded the 30-word quote limit in 11 of 30 quotes; recorded as a form deviation, not corrected.
- One 8B quote reordered sentences from the passage and was classified as absent. Added the "stitched" tier, which is not counted as fabrication.
- Rubric application note for E segments (implicit mismatch) added to the analysis plan.
- Embedding model for semantic dispersion: nomic-embed-text.
- Full specification: docs/analysis_plan_v1.md.
