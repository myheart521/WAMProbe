# Minimal closed-loop replanning utility

Each cycle scores the same legal action set, executes only the selected trajectory prefix in true dynamics, then replans from the resulting state; the scoring window is capped by the remaining episode budget. Cross-profile Pearson values are descriptive because there are only five future scorers; context-block intervals remain the primary uncertainty view.

## blockpush-2d-v0.1

Control steps: 6; execute prefix: 1.

| Controller | Kind | Offline CRC | Offline regret | Closed return [95% CI] | Success | Oracle gap |
|---|---|---:|---:|---:|---:|---:|
| oracle-simulator | future-scorer | 1.0000 | 0.0000 | 0.0000 [0.0000, 0.0000] | 1.0000 | 0.0000 |
| noisy-dynamics | future-scorer | 1.0000 | 0.0000 | 0.0000 [0.0000, 0.0000] | 1.0000 | 0.0000 |
| copy-last-frame | future-scorer | 0.0000 | 0.3000 | -0.3000 [-0.3000, -0.3000] | 0.0000 | 0.3000 |
| wrong-direction | future-scorer | -0.2500 | 0.3000 | -0.3000 [-0.3000, -0.3000] | 0.0000 | 0.3000 |
| action-agnostic | future-scorer | 0.0000 | 0.3000 | -0.3000 [-0.3000, -0.3000] | 0.0000 | 0.3000 |
| simulator-oracle-scorer | simulator-control | n/a | n/a | 0.0000 [0.0000, 0.0000] | 1.0000 | 0.0000 |
| fixed-action-policy | action-only-control | n/a | n/a | 0.0000 [0.0000, 0.0000] | 1.0000 | 0.0000 |
| random-candidate | random-control | n/a | n/a | -0.2850 [-0.3000, -0.2650] | 0.0000 | 0.2850 |

Future-scorer profile correlation: offline CRC vs closed-loop return = 0.9855; offline regret vs closed-loop return = -1.0000.

Offline-CRC/return ordering disagreed on 0/6 comparable future-scorer pairs.

## gripper-catch-v0.1

Control steps: 5; execute prefix: 1.

| Controller | Kind | Offline CRC | Offline regret | Closed return [95% CI] | Success | Oracle gap |
|---|---|---:|---:|---:|---:|---:|
| oracle-simulator | future-scorer | 1.0000 | 0.0000 | 1.0000 [1.0000, 1.0000] | 1.0000 | 0.0000 |
| noisy-dynamics | future-scorer | 1.0000 | 0.0000 | 0.9967 [0.9900, 1.0000] | 0.9167 | 0.0033 |
| copy-last-frame | future-scorer | 0.0000 | 1.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 | 1.0000 |
| wrong-direction | future-scorer | 0.0000 | 1.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 | 1.0000 |
| action-agnostic | future-scorer | 0.0000 | 1.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 | 1.0000 |
| simulator-oracle-scorer | simulator-control | n/a | n/a | 1.0000 [1.0000, 1.0000] | 1.0000 | 0.0000 |
| fixed-action-policy | action-only-control | n/a | n/a | 1.0000 [1.0000, 1.0000] | 1.0000 | 0.0000 |
| random-candidate | random-control | n/a | n/a | 0.2367 [0.0000, 0.4733] | 0.0833 | 0.7633 |

Future-scorer profile correlation: offline CRC vs closed-loop return = 1.0000; offline regret vs closed-loop return = -1.0000.

Offline-CRC/return ordering disagreed on 0/6 comparable future-scorer pairs.

Success means matching the greedy simulator-future scorer's final return within
1e-9 on the same context and control budget. Score ties use the benchmark's stable
candidate order. The scoring horizon is capped by the episode steps remaining,
preventing terminal scores beyond the execution budget. These analytic tasks
validate the evaluator; they do not establish real-robot or large-model closed-loop
performance.
