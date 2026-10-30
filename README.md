# Subtext Workbench — Stage 1

Research artifact for a Stage 1 submission to the *Organization Science* special issue **AI-Assisted Frontiers in Organizational Science**.

**Question.** Much of what matters in organizations is said obliquely: displayed feelings that differ from felt ones, praise that is not meant, laughter at a superior's joke, silence about power. When large language models (LLMs) read such talk, where can their reading be trusted and where does it fail? The project's aim is to test whether systematic human–LLM interpretive divergence can serve as a validated signal for locating emotional subtext in organizational discourse, and to map where AI-assisted qualitative inference holds and where it fails.

**Stage 1** compares two local open-weight models (`qwen3:8b`, `qwen3:14b`) with a sealed answer key on 48 author-written interview segments (24 matched pairs: a version with emotional subtext, E, and a sincere control, C), across four layers of meaning (implicit evaluation, suppressed emotion, irony and humour, power-related silence) and three levels of difficulty. Each model read every segment five times with a neutral Gioia-style first-order coding prompt. Run-1 interpretations were scored blind by the first author.

- RQ1: Do E segments produce more interpretive error and more instability than their paired C segments?
- RQ2: How does agreement with the answer key vary by layer and difficulty?
- RQ3: Do the models' own instability (across runs and across models) and self-rated confidence predict their errors?

Results: [`analysis/results.md`](analysis/results.md) and [`analysis/figures/`](analysis/figures/). All inferential results are exploratory.

**Status.** Second scoring (Prof. Xiaoran Hu, LSE) and inter-rater agreement are not yet complete; they follow the Stage 1 submission (see [deviation record](docs/deviation_2026-10-29_unblinding_before_second_scoring.md)). No result in this repository has been checked for inter-rater agreement yet.

---

## Repository map

```text
materials/sealed/       sealed segments, answer key, coding lists A/B, scoring rubric, Stage 1 scoring
                        protocol; SHA256SUMS.txt; tag seal-v1. Never modified after sealing.
data/derived/           coder inputs and answer key parsed from the sealed files (python -m subtext prepare)
prompts/v1/             neutral coding prompt: system prompt, message template, JSON output schema
config/                 pilot.yaml, main.yaml (model runs), analysis.yaml (embeddings and analysis)
src/subtext/            pipeline code (see "Commands")
app/scoring_app.py      blind scoring interface (Streamlit)
runs/pilot/             pilot outputs (calibration practice only, excluded from results)
runs/main/              all 480 main-run records: full request, raw response, thinking trace, model digest,
                        Ollama version, seed, timing, token counts, validation
scoring/sheets/         blind scoring sheets (practice, primary, second)
scoring/sets_manifest.json   sheet hashes and the response-key SHA-256, recorded before scoring began
scoring/private/key.json     response key (published with the submission; see docs)
scoring/scores/         score files <set>__<scorer>.csv
analysis/               embedding cache, results (JSON and Markdown), figures, analysis manifest
docs/                   analysis plan, decision log, calibration record, deviations, addendum, audit timeline
docs/workbench/         workbench prototype (one HTML page, built by python -m subtext build-demo)
logs/                   model-access record (2026-10-28)
tests/                  unit tests (quote checking, schema validation, statistics)
```

## Setup

Python 3.14 was used; the pinned versions in `requirements.txt` were each released at least two weeks before use.

```bash
git clone https://github.com/cynthialiu1007-png/subtext-workbench.git
cd subtext-workbench
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
```

## Reproduction in three levels

### Level 1 — verify the record (no models, about a minute)

```bash
python -m subtext verify
python tests/test_validate.py
python tests/test_analysis.py
```

`verify` checks that the sealed files match `SHA256SUMS.txt`; that the derived inputs come from the sealed files; that all 480 run records were made with the committed prompt, one model digest per model and the configured seeds; that the scoring sheets and the published response key match the hashes recorded before scoring; that the embedding cache matches the current interpretations; that the inputs of the committed analysis are unchanged; and that the Git history shows the key events in the required order (sealing before any model run, the analysis plan before the main run, scores before unblinding, the addendum before results). The timeline is also in [`docs/audit_timeline.md`](docs/audit_timeline.md).

### Level 2 — reproduce every reported number and figure from the cached outputs (no models, a few minutes)

```bash
python -m subtext summarize --phase main
python -m subtext audit-quotes --phase main
python -m subtext analyze --deviation docs/deviation_2026-10-29_unblinding_before_second_scoring.md
git diff --stat analysis/
```

`summarize` recomputes output validity, quote tiers and the fabricated-evidence rate from the raw records. `analyze` recomputes the instability measures (from the cached embeddings), the rubric metrics, RQ1–RQ3 and the three figures; the `--deviation` flag is required while second scoring is incomplete (the analysis code refuses to read the response key otherwise). Apart from timestamps and PDF metadata, `git diff` should show no change. Bootstrap intervals use a fixed seed (20261029).

Recomputing the embeddings requires Ollama and `nomic-embed-text` (digest recorded in `analysis/embeddings_meta.json`); do this in a copy of the repository, because `python -m subtext embed --force` replaces the cache.

### Level 3 — rerun the models (Ollama required; about 6.5 hours on the original machine)

The original runs used Ollama 0.40.11 on a MacBook Pro with Apple silicon and 16 GB unified memory, `qwen3:8b` (digest `500a1f067a9f…`) and `qwen3:14b` (digest `bdbd181c33f2…`), Q4_K_M, thinking mode on, temperature 0.6, top-p 0.95, top-k 20, min-p 0, context 8192, seeds 1–5.

```bash
ollama pull qwen3:8b && ollama pull qwen3:14b
cp config/main.yaml config/rerun.yaml        # then set   phase: rerun
python -m subtext check-env --config config/rerun.yaml
python -m subtext run --config config/rerun.yaml
python -m subtext summarize --phase rerun
```

Outputs go to `runs/rerun/`, so the original records are untouched. On the original machine, Ollama version and model digests, the same seed reproduced an output byte for byte (determinism check, `runs/pilot/determinism/`); identical outputs are not expected on other hardware or versions. Scores are tied to the original run-1 outputs, so Level 3 reproduces the instability measures and output statistics, not the scored results.

## Workbench prototype

Live page: https://cynthialiu1007-png.github.io/subtext-workbench/workbench/

[`docs/workbench/index.html`](docs/workbench/index.html) is a single self-contained page (no installation, no network access) built from the repository files by `python -m subtext build-demo`. Open it in any browser; when the repository is public it is also served through GitHub Pages.

- **Replay** sends one interview passage to the two models and shows the recorded readings returning in the order and with the latency of the original runs (30 times faster), the quoted evidence lighting up on the passage, the instability signals, and then the answer key and blind scores. The page calls no model: every reading is a recorded output from `runs/main/`.
- **Workbench** lays out all 48 segments as a triage map (layer of meaning by level of difficulty, each subtext version beside its sincere control), coloured by a chosen instability signal; the passage with every quote located and marked by its check result; and the ten readings, each with tone, confidence, codes, quotes, thinking trace and a link to its raw record. The answer key and scores are hidden until switched on.
- **Findings** and **Provenance** show the Stage 1 results from `analysis/results.json` and the SHA-256 of every input.

The readings map is a two-dimensional classical MDS projection of the cosine distances between the ten readings of a segment, on one scale shared by all segments; the reported measures are computed from the full embeddings.

## Audit trail and records

- **Sealing.** Segments, answer key, rubric and scoring protocol were committed and tagged `seal-v1` before any model run. Corrections are never made to sealed files; they are recorded as new, dated files.
- **Pre-specification.** The analysis plan ([`docs/analysis_plan_v1.md`](docs/analysis_plan_v1.md)) was committed after the pilot and before the main run and has not been edited since.
- **Blinding.** Scoring sheets hide model, run, confidence, codes and quote checks; response IDs come from a system random source, and the key's SHA-256 was committed before scoring. The key was read by the analysis code only after primary scoring was committed.
- **Deviations and additions**, each committed before the step it concerns:
  [calibration order](docs/deviation_2026-10-28_calibration_order.md) ·
  [unblinding before second scoring](docs/deviation_2026-10-29_unblinding_before_second_scoring.md) ·
  [RQ3 within E segments (addendum)](docs/addendum_2026-10-29_rq3_within_E.md) ·
  [response key published](docs/deviation_2026-10-29_response_key_published.md)
- **Decisions and calibration:** [`docs/decision_log.md`](docs/decision_log.md), [`docs/calibration_record.md`](docs/calibration_record.md).
- **Quote audit:** [`docs/quote_audit_main.md`](docs/quote_audit_main.md) (generated) and [`docs/quote_audit_main_review.md`](docs/quote_audit_main_review.md) (item-level review; no tier changed).

## Commands

`python -m subtext <command>`: `prepare` · `check-env` · `run` · `determinism` · `summarize` · `make-sets` · `export-excel` · `import-excel` · `embed` · `analyze` · `audit-quotes` · `verify` · `build-demo`. Blind scoring interface: `streamlit run app/scoring_app.py`.

## Use of AI in this project

The 48 segments were written by the first author directly in English, without AI or grammar tools. Claude (Anthropic) suggested the framework for the segments (design matrix, definitions of the layers of meaning, writing rules), which the author adopted; three demonstration segments drafted by Claude while the framework was discussed were not used in the study. Claude drafted the scoring rubric, which the author revised and finalised before sealing. Claude drafted reference scores for the 12-response practice set, which the author reviewed item by item before saving (see the calibration record). The primary scores are the author’s own; two items (R0A24DC, R8403CD) were discussed with Claude during scoring. The models under study were run locally through Ollama.

## People

Xiner Liu (London School of Economics): segments, answer key, rubric, primary scoring (XL).
Xiaoran Hu (London School of Economics): second scorer (XH), pending.

## Licence and citation

Code: MIT ([`LICENSE`](LICENSE)). Materials, data, model outputs and documentation: CC BY 4.0 ([`LICENSE-DATA.md`](LICENSE-DATA.md)). An archived release with a DOI will be listed here.
