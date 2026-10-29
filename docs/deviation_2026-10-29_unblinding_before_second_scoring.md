# Deviation: response key read before second scoring (2026-10-29)

Plan reference: stage1_scoring_protocol.md Section 2 (the key is not opened until all scoring, including the second scorer's, is complete) and Section 4 (second scoring and agreement); analysis plan Sections 5 and 7.

What changes: the second scorer (XH) cannot score the practice set and the second-scorer set before the Stage 1 deadline (1 November 2026). The primary scorer's scores (XL, 96 responses, pre-discussion) are complete and committed. To report Stage 1 results by model, the response key is read before second scoring.

Procedure instead:
1. The key (scoring/private/key.json) is read only by `python -m subtext analyze`, after its SHA-256 is checked against scoring/sets_manifest.json. It stays outside the repository.
2. Committed outputs (analysis/) are aggregates by model, layer and level. Segment-level results by model are written only to scoring/private/ (git-ignored). XL does not open the key or the segment-level file before second scoring and any rescoring are complete.
3. Second scoring by XH, Cohen's kappa and the discussion of disagreements take place after submission, under the procedure in docs/deviation_2026-10-28_calibration_order.md. XH remains blind to model and run. Stage 1 submission materials state that inter-rater agreement has not yet been assessed.
4. If the discussion changes a provisional rule, XL rescores the affected responses in the blind interface by response_id. By then XL will have seen results aggregated by model; this is reported. The primary analysis remains on pre-discussion scores; final-stage rescores are reported as a sensitivity analysis.

Written and committed before the key was read.
