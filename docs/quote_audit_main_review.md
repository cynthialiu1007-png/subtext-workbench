# Review of absent quotes in the main run (2026-10-29)

Source: docs/quote_audit_main.md (`python -m subtext audit-quotes --phase main`, read-only).
Plan reference: analysis plan Section 4 (quote tiers). No tier and no classification rule is changed; the pre-specified fabricated-evidence rate is reported as defined (qwen3:8b 16/1,192 = 1.3%; qwen3:14b 13/1,336 = 1.0%). This review is a post hoc, descriptive check of the 29 quotes classified `absent`.

Who: item-level judgements drafted by Claude (Anthropic) against the passage text; reviewed item by item and adopted by XL. Because a language model drafted the judgements, every item is listed with its reason so that readers can check it against the passage.

## Criteria

1. Is every element of the quote's content (events, people, numbers, attributions) supported by the passage?
2. If so, do the wording changes leave the meaning intact, or could they mislead a reader about what was said?

Categories: **meaning preserved** (editorial changes only); **preserved but potentially misleading** (content supported, but omission or rearrangement could change how a reader understands it); **content altered** (an element not supported by the passage).

## Result

None of the 29 quotes is invented text: every quote reproduces passage material. 25 preserve the meaning, 2 are potentially misleading, and 2 alter content (both qwen3:8b). Quotes whose content is altered: qwen3:8b 2/1,192 (0.17%); qwen3:14b 0/1,336.

## Items

| # | model · run · code | change | judgement |
|---|---|---|---|
| 1 | 14b · 1 · 122 (C-L3-01-E) | "the director said at a meeting that" shortened to "the director said" | meaning preserved |
| 2 | 14b · 1 · 215 (C-L1-02-C) | "when he's finished he's the first to laugh" spliced with the later sentence "He's the only one there enjoying himself", no ellipsis | meaning preserved |
| 3 | 14b · 2 · 124 (C-L3-02-C) | "That whiteboard" → "the whiteboard" | meaning preserved |
| 4 | 14b · 2 · 215 (C-L1-02-C) | "He says no, it's his tradition" (tense changed) joined by ellipsis to "the next day he told one first as usual", which follows a different episode in which he said he would consider the request | preserved but potentially misleading |
| 5 | 14b · 3 · 106 (C-L1-02-E) | as item 2 | meaning preserved |
| 6 | 14b · 3 · 122 (C-L3-01-E) | as item 1 | meaning preserved |
| 7 | 14b · 3 · 213 (A-L1-01-C) | "a colleague and I checked them all in" → "we checked them all in", within an elided quote | meaning preserved |
| 8 | 14b · 4 · 122 (C-L3-01-E) | as item 1 | meaning preserved |
| 9 | 14b · 4 · 205 (D-L3-01-C) | "Our supervisor's" → "the supervisor's" | meaning preserved |
| 10 | 14b · 4 · 221 (A-L1-02-E) | "pack", "leave" → "packed", "left", within an elided quote | meaning preserved |
| 11 | 14b · 5 · 110 (B-L3-01-E) | "worked" added before "from six in the evening until nearly two"; a later sentence appended | meaning preserved |
| 12 | 14b · 5 · 122 (C-L3-01-E) | as item 1 | meaning preserved |
| 13 | 14b · 5 · 215 (C-L1-02-C) | "He says no" → "He said no" | meaning preserved |
| 14 | 8b · 1 · 102 (D-L1-01-C) | "disinfection cabinet" truncated to "disin"; the sealing step omitted without ellipsis | meaning preserved |
| 15 | 8b · 1 · 119 (B-L3-02-C) | the sentence "Fifteen years of work, it's about time I had a rest." omitted without ellipsis | meaning preserved |
| 16 | 8b · 1 · 216 (A-L3-01-C) | subject "Manager Zhao" placed directly before "told the guest very calmly" (intervening clauses omitted) | meaning preserved |
| 17 | 8b · 1 · 216 (A-L3-01-C) | "Then he gave him" → "Manager Zhao gave him" | meaning preserved |
| 18 | 8b · 2 · 106 (C-L1-02-E) | "more than 120" → "more than 12,000" | content altered |
| 19 | 8b · 2 · 116 (A-L3-01-E) | "a night's stay free of charge" → "a free stay"; "apologise" → "apologize"; subject added | meaning preserved |
| 20 | 8b · 2 · 116 (A-L3-01-E) | "my bonus that month was more than 300 yuan less" → "my bonus was reduced by 300 yuan" | content altered |
| 21 | 8b · 2 · 216 (A-L3-01-C) | as item 17 | meaning preserved |
| 22 | 8b · 3 · 110 (B-L3-01-E) | "and they still haven't hired" → "but they still haven't hired", within an elided quote | meaning preserved |
| 23 | 8b · 3 · 206 (B-L3-02-E) | "Fifteen years of work" → "Fifteen years of" | meaning preserved |
| 24 | 8b · 3 · 218 (D-L2-01-C) | "at New Year she'd give" → "she gave", within an elided quote | meaning preserved |
| 25 | 8b · 3 · 219 (B-L1-01-C) | "she made a point of" → "the guest made a point of" | meaning preserved |
| 26 | 8b · 4 · 216 (A-L3-01-C) | as item 16 | meaning preserved |
| 27 | 8b · 4 · 216 (A-L3-01-C) | as item 17 | meaning preserved |
| 28 | 8b · 5 · 102 (D-L1-01-C) | four clauses reordered, "When" dropped, "redone" truncated to "red" | preserved but potentially misleading |
| 29 | 8b · 5 · 124 (C-L3-02-C) | "asking how many" → "asked how many", within an elided quote | meaning preserved |

## Context: edited quotes in all tiers

Beyond `absent`, quotes that are not verbatim after typographic normalisation and case-folding (tiers elided, stitched, near and absent) make up 98/1,192 (8.2%) for qwen3:8b and 137/1,336 (10.3%) for qwen3:14b. The models rarely invent evidence, but they often edit it while presenting it as quotation; quotes produced by a model therefore need automatic checking against the source before they are used as evidence.
