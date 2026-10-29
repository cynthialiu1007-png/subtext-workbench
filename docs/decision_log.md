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
## 2026-10-29 Analysis settings (module 7), fixed before any embedding or analysis was run
- Second scoring by Prof. Hu cannot be completed before the deadline; it moves to after submission. Response key read before second scoring: docs/deviation_2026-10-29_unblinding_before_second_scoring.md.
- RQ3 within E segments added: docs/addendum_2026-10-29_rq3_within_E.md.
- Embeddings: nomic-embed-text via Ollama; the interpretation field is prefixed with "clustering: " (the model's task prefix for grouping texts and detecting semantic duplicates). Embeddings are computed once and cached in analysis/embeddings.jsonl.
- Conventions: X treated as missing and reported; McNemar exact (binomial); Wilcoxon signed-rank with zero differences dropped; effect sizes median paired difference and matched-pairs rank-biserial r; AUC oriented so that higher values mean higher error risk (mean confidence reversed); pooled bootstrap resamples segments as clusters; calibration uses run-1 confidence; confidence SD is the sample SD; d' from lenient read rate and over-interpretation rate with the log-linear correction; excluding the medium-confidence segments drops the whole pair in paired analyses and the E segment elsewhere; kappa on E unweighted (F/P/N/M/X) and linearly weighted on read score for items neither scorer coded X, on C unweighted (A/O/X) with raw agreement.
- Analysis dependencies: numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2 (each released at least two weeks earlier, with Python 3.14 wheels).

## 2026-10-29 Repository for the Stage 1 submission
- The repository is made public at submission, with author names (no anonymisation), and archived with a DOI.
- The response key is published with the submission: docs/deviation_2026-10-29_response_key_published.md.
- Licences: code MIT; materials, data, model outputs and documentation CC BY 4.0.
- The 48 segments were written by the author directly in English, without AI or grammar tools.
- Added `python -m subtext verify` (reproduction level 1) and `python -m subtext audit-quotes` (read-only audit of absent quotes; no tier changed).
- Absent-quote review: the 29 quotes classified absent were reviewed against the passages (judgements drafted by Claude, reviewed and adopted by XL); no tier changed. See docs/quote_audit_main_review.md.
- Disclosure: Claude suggested the segment framework (design matrix, layer definitions, writing rules); the author wrote all 48 segments.
- Workbench prototype: one self-contained HTML page (docs/workbench/index.html) built from repository files by `python -m subtext build-demo`; replay of recorded outputs only (no model calls), latency shown 30 times faster; answer key hidden by default; replay examples C-L3-01-E and C-L1-02-E, chosen to illustrate, not as typical cases.
- Repository made public on 2026-10-29, before submission; GitHub Pages serves docs/ (workbench at docs/workbench/).
