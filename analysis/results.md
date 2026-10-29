# Stage 1 analysis results

Generated 2026-10-29T00:30:24+00:00 by `python -m subtext analyze`. Aggregates only. Primary scorer XL, stage pre-discussion. Response key opened: True.

## Instability (all five runs)

| model | version | measure | mean | median |
|---|---|---|---|---|
| qwen3:8b | E | semantic_dispersion | 0.073 | 0.068 |
| qwen3:8b | E | tone_disagreement | 0.050 | 0.000 |
| qwen3:8b | E | confidence_sd | 3.804 | 4.472 |
| qwen3:8b | E | confidence_mean | 90.542 | 90.000 |
| qwen3:8b | C | semantic_dispersion | 0.060 | 0.057 |
| qwen3:8b | C | tone_disagreement | 0.042 | 0.000 |
| qwen3:8b | C | confidence_sd | 3.970 | 4.328 |
| qwen3:8b | C | confidence_mean | 91.792 | 92.000 |
| qwen3:14b | E | semantic_dispersion | 0.062 | 0.064 |
| qwen3:14b | E | tone_disagreement | 0.058 | 0.000 |
| qwen3:14b | E | confidence_sd | 1.535 | 2.236 |
| qwen3:14b | E | confidence_mean | 94.000 | 94.000 |
| qwen3:14b | C | semantic_dispersion | 0.051 | 0.047 |
| qwen3:14b | C | tone_disagreement | 0.083 | 0.000 |
| qwen3:14b | C | confidence_sd | 0.475 | 0.000 |
| qwen3:14b | C | confidence_mean | 94.667 | 95.000 |
| cross-model | E | cross_model_distance | 0.089 | 0.088 |
| cross-model | C | cross_model_distance | 0.074 | 0.063 |

## RQ1b: instability, E vs C (paired by pair_id)

| model | measure | mean E | mean C | median diff [CI] | r_rb [CI] | Wilcoxon p | nonzero pairs |
|---|---|---|---|---|---|---|---|
| qwen3:8b | semantic_dispersion | 0.073 | 0.060 | 0.012 [0.005, 0.023] | 0.493 [0.047, 0.840] | 0.034 | 24/24 |
| qwen3:8b | tone_disagreement | 0.050 | 0.042 | 0.000 [0.000, 0.000] | 0.200 [-1.000, 1.000] | 0.655 | 5/24 |
| qwen3:8b | confidence_sd | 3.804 | 3.970 | 0.000 [-1.445, 1.005] | -0.067 [-0.521, 0.442] | 0.794 | 20/24 |
| qwen3:8b | confidence_mean | 90.542 | 91.792 | -1.500 [-3.500, 1.000] | -0.415 [-0.772, 0.056] | 0.087 | 22/24 |
| qwen3:14b | semantic_dispersion | 0.062 | 0.051 | 0.012 [-0.003, 0.026] | 0.420 [-0.013, 0.773] | 0.074 | 24/24 |
| qwen3:14b | tone_disagreement | 0.058 | 0.083 | 0.000 [0.000, 0.000] | -0.286 [-1.000, 0.667] | 0.490 | 7/24 |
| qwen3:14b | confidence_sd | 1.535 | 0.475 | 0.251 [0.000, 2.236] | 0.914 [0.667, 1.000] | 0.002 | 14/24 |
| qwen3:14b | confidence_mean | 94.000 | 94.667 | -0.500 [-1.000, 0.000] | -0.686 [-1.000, -0.219] | 0.019 | 14/24 |
| cross-model | cross_model_distance | 0.089 | 0.074 | 0.019 [0.000, 0.032] | 0.487 [0.053, 0.847] | 0.037 | 24/24 |

## Rubric Section 8 metrics (run 1)

| | n E | strict | lenient | mean score | misread | n C | over-interp. | discrimination | d′ | X |
|---|---|---|---|---|---|---|---|---|---|---|
| pooled | 48 | 0.146 | 0.354 | 0.500 | 0.000 | 48 | 0.000 | 0.354 | 1.953 | 0 |
| qwen3:8b | 24 | 0.125 | 0.333 | 0.458 | 0.000 | 24 | 0.000 | 0.333 | 1.641 | 0 |
| qwen3:14b | 24 | 0.167 | 0.375 | 0.542 | 0.000 | 24 | 0.000 | 0.375 | 1.748 | 0 |

## RQ1a: interpretive error, E vs C (McNemar, exact)

| variant | model | pairs | error E | error C | diff [CI] | E only | C only | p |
|---|---|---|---|---|---|---|---|---|
| main | qwen3:8b | 24 | 0.667 | 0.000 | 0.667 [0.458, 0.833] | 16 | 0 | 0.000 |
| main | qwen3:14b | 24 | 0.625 | 0.000 | 0.625 [0.457, 0.792] | 15 | 0 | 0.000 |
| P_as_error | qwen3:8b | 24 | 0.875 | 0.000 | 0.875 [0.708, 1.000] | 21 | 0 | 0.000 |
| P_as_error | qwen3:14b | 24 | 0.833 | 0.000 | 0.833 [0.667, 0.958] | 20 | 0 | 0.000 |
| excluding_medium_confidence | qwen3:8b | 21 | 0.714 | 0.000 | 0.714 [0.524, 0.905] | 15 | 0 | 0.000 |
| excluding_medium_confidence | qwen3:14b | 21 | 0.619 | 0.000 | 0.619 [0.429, 0.810] | 13 | 0 | 0.000 |

## RQ3: AUC for interpretive error (run 1)

`all_48` is pre-specified; `within_E` is the addendum analysis (exploratory).

| analysis | target | n (errors) | predictor | AUC [CI] | skipped resamples |
|---|---|---|---|---|---|
| all_48__main | qwen3:8b | 48 (16) | semantic_dispersion | 0.494 [0.312, 0.673] | 0 |
| all_48__main | qwen3:8b | 48 (16) | tone_disagreement | 0.494 [0.385, 0.616] | 0 |
| all_48__main | qwen3:8b | 48 (16) | confidence_sd | 0.450 [0.279, 0.629] | 0 |
| all_48__main | qwen3:8b | 48 (16) | confidence_mean | 0.564 [0.376, 0.746] | 0 |
| all_48__main | qwen3:8b | 48 (16) | cross_model_distance | 0.557 [0.376, 0.724] | 0 |
| all_48__main | qwen3:14b | 48 (15) | semantic_dispersion | 0.521 [0.306, 0.722] | 0 |
| all_48__main | qwen3:14b | 48 (15) | tone_disagreement | 0.473 [0.344, 0.611] | 0 |
| all_48__main | qwen3:14b | 48 (15) | confidence_sd | 0.525 [0.391, 0.679] | 0 |
| all_48__main | qwen3:14b | 48 (15) | confidence_mean | 0.525 [0.391, 0.679] | 0 |
| all_48__main | qwen3:14b | 48 (15) | cross_model_distance | 0.590 [0.396, 0.766] | 0 |
| all_48__main | pooled | 96 (31) | semantic_dispersion | 0.517 [0.376, 0.659] | 0 |
| all_48__main | pooled | 96 (31) | tone_disagreement | 0.481 [0.390, 0.581] | 0 |
| all_48__main | pooled | 96 (31) | confidence_sd | 0.484 [0.376, 0.582] | 0 |
| all_48__main | pooled | 96 (31) | confidence_mean | 0.532 [0.422, 0.637] | 0 |
| all_48__main | pooled | 96 (31) | cross_model_distance | 0.573 [0.407, 0.729] | 0 |
| all_48__main__excluding_medium_confidence | qwen3:8b | 45 (15) | semantic_dispersion | 0.496 [0.306, 0.678] | 0 |
| all_48__main__excluding_medium_confidence | qwen3:8b | 45 (15) | tone_disagreement | 0.481 [0.376, 0.596] | 0 |
| all_48__main__excluding_medium_confidence | qwen3:8b | 45 (15) | confidence_sd | 0.434 [0.253, 0.615] | 0 |
| all_48__main__excluding_medium_confidence | qwen3:8b | 45 (15) | confidence_mean | 0.574 [0.379, 0.769] | 0 |
| all_48__main__excluding_medium_confidence | qwen3:8b | 45 (15) | cross_model_distance | 0.580 [0.396, 0.751] | 0 |
| all_48__main__excluding_medium_confidence | qwen3:14b | 45 (13) | semantic_dispersion | 0.490 [0.274, 0.711] | 0 |
| all_48__main__excluding_medium_confidence | qwen3:14b | 45 (13) | tone_disagreement | 0.499 [0.366, 0.642] | 0 |
| all_48__main__excluding_medium_confidence | qwen3:14b | 45 (13) | confidence_sd | 0.572 [0.416, 0.742] | 0 |
| all_48__main__excluding_medium_confidence | qwen3:14b | 45 (13) | confidence_mean | 0.572 [0.417, 0.743] | 0 |
| all_48__main__excluding_medium_confidence | qwen3:14b | 45 (13) | cross_model_distance | 0.538 [0.346, 0.717] | 0 |
| all_48__main__excluding_medium_confidence | pooled | 90 (28) | semantic_dispersion | 0.502 [0.362, 0.642] | 0 |
| all_48__main__excluding_medium_confidence | pooled | 90 (28) | tone_disagreement | 0.486 [0.390, 0.592] | 0 |
| all_48__main__excluding_medium_confidence | pooled | 90 (28) | confidence_sd | 0.503 [0.395, 0.605] | 0 |
| all_48__main__excluding_medium_confidence | pooled | 90 (28) | confidence_mean | 0.560 [0.445, 0.668] | 0 |
| all_48__main__excluding_medium_confidence | pooled | 90 (28) | cross_model_distance | 0.560 [0.378, 0.727] | 0 |
| all_48__P_as_error | qwen3:8b | 48 (21) | semantic_dispersion | 0.607 [0.429, 0.762] | 0 |
| all_48__P_as_error | qwen3:8b | 48 (21) | tone_disagreement | 0.544 [0.437, 0.665] | 0 |
| all_48__P_as_error | qwen3:8b | 48 (21) | confidence_sd | 0.470 [0.305, 0.638] | 0 |
| all_48__P_as_error | qwen3:8b | 48 (21) | confidence_mean | 0.576 [0.404, 0.749] | 0 |
| all_48__P_as_error | qwen3:8b | 48 (21) | cross_model_distance | 0.670 [0.504, 0.825] | 0 |
| all_48__P_as_error | qwen3:14b | 48 (20) | semantic_dispersion | 0.552 [0.373, 0.725] | 0 |
| all_48__P_as_error | qwen3:14b | 48 (20) | tone_disagreement | 0.461 [0.341, 0.589] | 0 |
| all_48__P_as_error | qwen3:14b | 48 (20) | confidence_sd | 0.644 [0.504, 0.782] | 0 |
| all_48__P_as_error | qwen3:14b | 48 (20) | confidence_mean | 0.653 [0.513, 0.789] | 0 |
| all_48__P_as_error | qwen3:14b | 48 (20) | cross_model_distance | 0.679 [0.511, 0.831] | 0 |
| all_48__P_as_error | pooled | 96 (41) | semantic_dispersion | 0.582 [0.450, 0.709] | 0 |
| all_48__P_as_error | pooled | 96 (41) | tone_disagreement | 0.501 [0.410, 0.599] | 0 |
| all_48__P_as_error | pooled | 96 (41) | confidence_sd | 0.526 [0.439, 0.613] | 0 |
| all_48__P_as_error | pooled | 96 (41) | confidence_mean | 0.584 [0.489, 0.674] | 0 |
| all_48__P_as_error | pooled | 96 (41) | cross_model_distance | 0.674 [0.508, 0.827] | 0 |
| all_48__P_as_error__excluding_medium_confidence | qwen3:8b | 45 (18) | semantic_dispersion | 0.578 [0.393, 0.747] | 0 |
| all_48__P_as_error__excluding_medium_confidence | qwen3:8b | 45 (18) | tone_disagreement | 0.506 [0.403, 0.619] | 0 |
| all_48__P_as_error__excluding_medium_confidence | qwen3:8b | 45 (18) | confidence_sd | 0.444 [0.273, 0.625] | 0 |
| all_48__P_as_error__excluding_medium_confidence | qwen3:8b | 45 (18) | confidence_mean | 0.537 [0.350, 0.725] | 0 |
| all_48__P_as_error__excluding_medium_confidence | qwen3:8b | 45 (18) | cross_model_distance | 0.636 [0.456, 0.800] | 0 |
| all_48__P_as_error__excluding_medium_confidence | qwen3:14b | 45 (17) | semantic_dispersion | 0.563 [0.371, 0.749] | 0 |
| all_48__P_as_error__excluding_medium_confidence | qwen3:14b | 45 (17) | tone_disagreement | 0.453 [0.333, 0.583] | 0 |
| all_48__P_as_error__excluding_medium_confidence | qwen3:14b | 45 (17) | confidence_sd | 0.659 [0.511, 0.806] | 0 |
| all_48__P_as_error__excluding_medium_confidence | qwen3:14b | 45 (17) | confidence_mean | 0.665 [0.518, 0.809] | 0 |
| all_48__P_as_error__excluding_medium_confidence | qwen3:14b | 45 (17) | cross_model_distance | 0.643 [0.460, 0.806] | 0 |
| all_48__P_as_error__excluding_medium_confidence | pooled | 90 (35) | semantic_dispersion | 0.572 [0.424, 0.712] | 0 |
| all_48__P_as_error__excluding_medium_confidence | pooled | 90 (35) | tone_disagreement | 0.477 [0.382, 0.576] | 0 |
| all_48__P_as_error__excluding_medium_confidence | pooled | 90 (35) | confidence_sd | 0.519 [0.425, 0.612] | 0 |
| all_48__P_as_error__excluding_medium_confidence | pooled | 90 (35) | confidence_mean | 0.567 [0.465, 0.672] | 0 |
| all_48__P_as_error__excluding_medium_confidence | pooled | 90 (35) | cross_model_distance | 0.639 [0.458, 0.803] | 0 |
| within_E__main | qwen3:8b | 24 (16) | semantic_dispersion | 0.234 [0.059, 0.452] | 0 |
| within_E__main | qwen3:8b | 24 (16) | tone_disagreement | 0.457 [0.259, 0.643] | 0 |
| within_E__main | qwen3:8b | 24 (16) | confidence_sd | 0.312 [0.075, 0.607] | 0 |
| within_E__main | qwen3:8b | 24 (16) | confidence_mean | 0.445 [0.200, 0.719] | 0 |
| within_E__main | qwen3:8b | 24 (16) | cross_model_distance | 0.359 [0.109, 0.637] | 0 |
| within_E__main | qwen3:14b | 24 (15) | semantic_dispersion | 0.407 [0.179, 0.652] | 0 |
| within_E__main | qwen3:14b | 24 (15) | tone_disagreement | 0.504 [0.328, 0.667] | 0 |
| within_E__main | qwen3:14b | 24 (15) | confidence_sd | 0.233 [0.046, 0.456] | 0 |
| within_E__main | qwen3:14b | 24 (15) | confidence_mean | 0.233 [0.047, 0.458] | 0 |
| within_E__main | qwen3:14b | 24 (15) | cross_model_distance | 0.459 [0.219, 0.714] | 0 |
| within_E__main | pooled | 48 (31) | semantic_dispersion | 0.338 [0.178, 0.525] | 0 |
| within_E__main | pooled | 48 (31) | tone_disagreement | 0.481 [0.358, 0.600] | 0 |
| within_E__main | pooled | 48 (31) | confidence_sd | 0.353 [0.210, 0.522] | 0 |
| within_E__main | pooled | 48 (31) | confidence_mean | 0.392 [0.231, 0.563] | 0 |
| within_E__main | pooled | 48 (31) | cross_model_distance | 0.411 [0.198, 0.639] | 0 |
| within_E__main__excluding_medium_confidence | qwen3:8b | 21 (15) | semantic_dispersion | 0.211 [0.026, 0.438] | 0 |
| within_E__main__excluding_medium_confidence | qwen3:8b | 21 (15) | tone_disagreement | 0.483 [0.283, 0.643] | 0 |
| within_E__main__excluding_medium_confidence | qwen3:8b | 21 (15) | confidence_sd | 0.289 [0.031, 0.625] | 0 |
| within_E__main__excluding_medium_confidence | qwen3:8b | 21 (15) | confidence_mean | 0.500 [0.228, 0.794] | 0 |
| within_E__main__excluding_medium_confidence | qwen3:8b | 21 (15) | cross_model_distance | 0.433 [0.147, 0.738] | 0 |
| within_E__main__excluding_medium_confidence | qwen3:14b | 21 (13) | semantic_dispersion | 0.337 [0.127, 0.596] | 0 |
| within_E__main__excluding_medium_confidence | qwen3:14b | 21 (13) | tone_disagreement | 0.562 [0.389, 0.719] | 0 |
| within_E__main__excluding_medium_confidence | qwen3:14b | 21 (13) | confidence_sd | 0.284 [0.058, 0.542] | 0 |
| within_E__main__excluding_medium_confidence | qwen3:14b | 21 (13) | confidence_mean | 0.284 [0.059, 0.543] | 0 |
| within_E__main__excluding_medium_confidence | qwen3:14b | 21 (13) | cross_model_distance | 0.385 [0.133, 0.648] | 0 |
| within_E__main__excluding_medium_confidence | pooled | 42 (28) | semantic_dispersion | 0.288 [0.142, 0.474] | 0 |
| within_E__main__excluding_medium_confidence | pooled | 42 (28) | tone_disagreement | 0.523 [0.409, 0.640] | 0 |
| within_E__main__excluding_medium_confidence | pooled | 42 (28) | confidence_sd | 0.384 [0.228, 0.569] | 0 |
| within_E__main__excluding_medium_confidence | pooled | 42 (28) | confidence_mean | 0.449 [0.286, 0.629] | 0 |
| within_E__main__excluding_medium_confidence | pooled | 42 (28) | cross_model_distance | 0.408 [0.167, 0.667] | 0 |
| within_E__P_as_error | qwen3:8b | 24 (21) | semantic_dispersion | 0.302 [0.000, 0.667] | 88 |
| within_E__P_as_error | qwen3:8b | 24 (21) | tone_disagreement | 0.619 [0.543, 0.714] | 88 |
| within_E__P_as_error | qwen3:8b | 24 (21) | confidence_sd | 0.167 [0.000, 0.478] | 88 |
| within_E__P_as_error | qwen3:8b | 24 (21) | confidence_mean | 0.349 [0.065, 0.682] | 88 |
| within_E__P_as_error | qwen3:8b | 24 (21) | cross_model_distance | 0.603 [0.217, 0.913] | 88 |
| within_E__P_as_error | qwen3:14b | 24 (20) | semantic_dispersion | 0.338 [0.087, 0.617] | 25 |
| within_E__P_as_error | qwen3:14b | 24 (20) | tone_disagreement | 0.487 [0.200, 0.667] | 25 |
| within_E__P_as_error | qwen3:14b | 24 (20) | confidence_sd | 0.394 [0.019, 0.739] | 25 |
| within_E__P_as_error | qwen3:14b | 24 (20) | confidence_mean | 0.438 [0.163, 0.739] | 25 |
| within_E__P_as_error | qwen3:14b | 24 (20) | cross_model_distance | 0.662 [0.351, 0.921] | 25 |
| within_E__P_as_error | pooled | 48 (41) | semantic_dispersion | 0.341 [0.112, 0.589] | 25 |
| within_E__P_as_error | pooled | 48 (41) | tone_disagreement | 0.544 [0.389, 0.667] | 25 |
| within_E__P_as_error | pooled | 48 (41) | confidence_sd | 0.361 [0.217, 0.565] | 25 |
| within_E__P_as_error | pooled | 48 (41) | confidence_mean | 0.441 [0.261, 0.641] | 25 |
| within_E__P_as_error | pooled | 48 (41) | cross_model_distance | 0.636 [0.345, 0.913] | 25 |
| within_E__P_as_error__excluding_medium_confidence | qwen3:8b | 21 (18) | semantic_dispersion | 0.278 [0.000, 0.632] | 70 |
| within_E__P_as_error__excluding_medium_confidence | qwen3:8b | 21 (18) | tone_disagreement | 0.583 [0.500, 0.676] | 70 |
| within_E__P_as_error__excluding_medium_confidence | qwen3:8b | 21 (18) | confidence_sd | 0.148 [0.000, 0.432] | 70 |
| within_E__P_as_error__excluding_medium_confidence | qwen3:8b | 21 (18) | confidence_mean | 0.324 [0.079, 0.647] | 70 |
| within_E__P_as_error__excluding_medium_confidence | qwen3:8b | 21 (18) | cross_model_distance | 0.556 [0.150, 0.899] | 70 |
| within_E__P_as_error__excluding_medium_confidence | qwen3:14b | 21 (17) | semantic_dispersion | 0.338 [0.000, 0.647] | 24 |
| within_E__P_as_error__excluding_medium_confidence | qwen3:14b | 21 (17) | tone_disagreement | 0.478 [0.184, 0.658] | 24 |
| within_E__P_as_error__excluding_medium_confidence | qwen3:14b | 21 (17) | confidence_sd | 0.404 [0.000, 0.750] | 24 |
| within_E__P_as_error__excluding_medium_confidence | qwen3:14b | 21 (17) | confidence_mean | 0.441 [0.167, 0.756] | 24 |
| within_E__P_as_error__excluding_medium_confidence | qwen3:14b | 21 (17) | cross_model_distance | 0.618 [0.250, 0.895] | 24 |
| within_E__P_as_error__excluding_medium_confidence | pooled | 42 (35) | semantic_dispersion | 0.322 [0.081, 0.592] | 24 |
| within_E__P_as_error__excluding_medium_confidence | pooled | 42 (35) | tone_disagreement | 0.518 [0.356, 0.636] | 24 |
| within_E__P_as_error__excluding_medium_confidence | pooled | 42 (35) | confidence_sd | 0.351 [0.202, 0.545] | 24 |
| within_E__P_as_error__excluding_medium_confidence | pooled | 42 (35) | confidence_mean | 0.424 [0.243, 0.627] | 24 |
| within_E__P_as_error__excluding_medium_confidence | pooled | 42 (35) | cross_model_distance | 0.590 [0.250, 0.892] | 24 |

## Calibration (run-1 confidence vs share correct)

| scope | model | n | mean confidence | accuracy | overconfidence |
|---|---|---|---|---|---|
| all_48 | qwen3:8b | 48 | 91.042 | 0.667 | 0.244 |
| all_48 | qwen3:14b | 48 | 94.479 | 0.688 | 0.257 |
| within_E | qwen3:8b | 24 | 90.625 | 0.333 | 0.573 |
| within_E | qwen3:14b | 24 | 94.583 | 0.375 | 0.571 |

## Inter-rater agreement (pre-discussion)

- practice: pending
- second: pending
