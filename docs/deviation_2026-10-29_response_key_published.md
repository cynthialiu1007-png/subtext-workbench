# Deviation: response key published with the Stage 1 submission (2026-10-29)

Plan reference: stage1_scoring_protocol.md Section 2; docs/deviation_2026-10-29_unblinding_before_second_scoring.md, points 1 and 2.

What changes: the response key (scoring/private/key.json) is committed to the repository and made public with the Stage 1 submission, so that every result reported by model can be reproduced from the repository. This replaces points 1 and 2 of the unblinding deviation, under which the key stayed outside the repository and XL did not open the key or the segment-level file.

Verification: the key's SHA-256 was recorded in scoring/sets_manifest.json when the scoring sets were made, before any score was entered (commit "Create blind scoring sets; key SHA-256 recorded in sets_manifest.json"; see docs/audit_timeline.md). `python -m subtext verify` checks that the published key matches that hash and that the hash has not changed since it was first committed.

Consequences:
1. From this point XL is not blind to model identity. Any final-stage rescoring by XL after the discussion with the second scorer is reported as a sensitivity analysis only; the primary analysis stays on pre-discussion scores.
2. The second scorer (XH) scores from the exported blind sheets, which show neither model nor run, and is asked not to consult the key or runs/ before his scores are imported. His blinding is procedural, as it already was in practice: the model outputs in runs/ have been in the repository since the main run.
3. Inter-rater agreement is computed on XH's pre-discussion scores, as planned.

Written and committed together with the key.
