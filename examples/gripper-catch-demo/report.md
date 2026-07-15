# WAMProbe gripper-catch-v0.1 Demo

This report compares action-aware and deliberately broken reference baselines.

| Model | Action Dependence | Permutation Effect | Permutation p-value ↓ | Counterfactual Direction | No-op Stability | State ADE ↓ | State FDE ↓ | CRC Spearman | CRC Kendall τ | CRC NDCG | CRC Pairwise Accuracy | Top-1 Regret ↓ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| oracle-simulator | 1.0000 | 2.0096 | 0.0556 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| noisy-dynamics | 0.9985 | 2.0099 | 0.0556 | 0.9986 | 0.0000 | 0.0563 | 0.0305 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| copy-last-frame | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.8856 | 1.0447 | 0.0000 | 0.0000 | 0.7103 | 0.5000 | 1.0000 |
| wrong-direction | 0.1735 | -0.2389 | 0.5556 | 0.3687 | 1.0000 | 0.8387 | 0.9663 | 0.0000 | 0.0000 | 0.7103 | 0.5000 | 1.0000 |
| action-agnostic | 0.0000 | 0.0000 | 1.0000 | 0.5811 | 0.0000 | 0.6439 | 1.1560 | 0.0000 | 0.0000 | 0.7103 | 0.5000 | 1.0000 |

## Context-block 95% confidence intervals

Intervals resample whole contexts, not correlated action branches or frames.

| Model | Metric | Mean | 95% CI | Median | Std |
|---|---|---:|---:|---:|---:|
| oracle-simulator | Action Dependence | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | Permutation Effect | 2.0096 | [1.9929, 2.0262] | 2.0318 | 0.0314 |
| oracle-simulator | Permutation p-value ↓ | 0.0556 | [0.0451, 0.0660] | 0.0417 | 0.0196 |
| oracle-simulator | Counterfactual Direction | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | No-op Stability | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | State ADE ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| oracle-simulator | State FDE ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| oracle-simulator | CRC Spearman | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | CRC Kendall τ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | CRC NDCG | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | CRC Pairwise Accuracy | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | Top-1 Regret ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| noisy-dynamics | Action Dependence | 0.9985 | [0.9964, 0.9999] | 1.0000 | 0.0032 |
| noisy-dynamics | Permutation Effect | 2.0099 | [1.9928, 2.0265] | 2.0276 | 0.0314 |
| noisy-dynamics | Permutation p-value ↓ | 0.0556 | [0.0451, 0.0660] | 0.0417 | 0.0196 |
| noisy-dynamics | Counterfactual Direction | 0.9986 | [0.9982, 0.9990] | 0.9987 | 0.0008 |
| noisy-dynamics | No-op Stability | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| noisy-dynamics | State ADE ↓ | 0.0563 | [0.0372, 0.0765] | 0.0550 | 0.0366 |
| noisy-dynamics | State FDE ↓ | 0.0305 | [0.0272, 0.0336] | 0.0304 | 0.0059 |
| noisy-dynamics | CRC Spearman | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| noisy-dynamics | CRC Kendall τ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| noisy-dynamics | CRC NDCG | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| noisy-dynamics | CRC Pairwise Accuracy | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| noisy-dynamics | Top-1 Regret ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | Action Dependence | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | Permutation Effect | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | Permutation p-value ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| copy-last-frame | Counterfactual Direction | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | No-op Stability | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | State ADE ↓ | 0.8856 | [0.8855, 0.8858] | 0.8854 | 0.0003 |
| copy-last-frame | State FDE ↓ | 1.0447 | [1.0442, 1.0453] | 1.0441 | 0.0009 |
| copy-last-frame | CRC Spearman | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | CRC Kendall τ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | CRC NDCG | 0.7103 | [0.5981, 0.8353] | 0.6309 | 0.2117 |
| copy-last-frame | CRC Pairwise Accuracy | 0.5000 | [0.5000, 0.5000] | 0.5000 | 0.0000 |
| copy-last-frame | Top-1 Regret ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| wrong-direction | Action Dependence | 0.1735 | [0.1725, 0.1745] | 0.1749 | 0.0020 |
| wrong-direction | Permutation Effect | -0.2389 | [-0.7944, 0.3167] | 0.5019 | 1.0476 |
| wrong-direction | Permutation p-value ↓ | 0.5556 | [0.3889, 0.7222] | 0.3333 | 0.3143 |
| wrong-direction | Counterfactual Direction | 0.3687 | [0.3646, 0.3727] | 0.3740 | 0.0076 |
| wrong-direction | No-op Stability | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| wrong-direction | State ADE ↓ | 0.8387 | [0.8380, 0.8393] | 0.8378 | 0.0012 |
| wrong-direction | State FDE ↓ | 0.9663 | [0.9643, 0.9683] | 0.9637 | 0.0037 |
| wrong-direction | CRC Spearman | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| wrong-direction | CRC Kendall τ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| wrong-direction | CRC NDCG | 0.7103 | [0.5962, 0.8244] | 0.6309 | 0.2117 |
| wrong-direction | CRC Pairwise Accuracy | 0.5000 | [0.5000, 0.5000] | 0.5000 | 0.0000 |
| wrong-direction | Top-1 Regret ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| action-agnostic | Action Dependence | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | Permutation Effect | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | Permutation p-value ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| action-agnostic | Counterfactual Direction | 0.5811 | [0.5799, 0.5823] | 0.5795 | 0.0023 |
| action-agnostic | No-op Stability | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | State ADE ↓ | 0.6439 | [0.6396, 0.6481] | 0.6495 | 0.0080 |
| action-agnostic | State FDE ↓ | 1.1560 | [1.1527, 1.1593] | 1.1604 | 0.0062 |
| action-agnostic | CRC Spearman | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | CRC Kendall τ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | CRC NDCG | 0.7103 | [0.5962, 0.8353] | 0.6309 | 0.2117 |
| action-agnostic | CRC Pairwise Accuracy | 0.5000 | [0.5000, 0.5000] | 0.5000 | 0.0000 |
| action-agnostic | Top-1 Regret ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |

## Paired model differences

Differences are left minus right over exactly aligned context IDs.

| Models | Metric | Mean difference | 95% CI | Contexts |
|---|---|---:|---:|---:|
| oracle-simulator − noisy-dynamics | Action Dependence | 0.0015 | [0.0001, 0.0034] | 12 |
| oracle-simulator − noisy-dynamics | Permutation Effect | -0.0004 | [-0.0028, 0.0019] | 12 |
| oracle-simulator − noisy-dynamics | Permutation p-value ↓ | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − noisy-dynamics | Counterfactual Direction | 0.0014 | [0.0010, 0.0018] | 12 |
| oracle-simulator − noisy-dynamics | No-op Stability | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − noisy-dynamics | State ADE ↓ | -0.0563 | [-0.0760, -0.0367] | 12 |
| oracle-simulator − noisy-dynamics | State FDE ↓ | -0.0305 | [-0.0340, -0.0270] | 12 |
| oracle-simulator − noisy-dynamics | CRC Spearman | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − noisy-dynamics | CRC Kendall τ | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − noisy-dynamics | CRC NDCG | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − noisy-dynamics | CRC Pairwise Accuracy | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − noisy-dynamics | Top-1 Regret ↓ | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − copy-last-frame | Action Dependence | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − copy-last-frame | Permutation Effect | 2.0096 | [1.9929, 2.0262] | 12 |
| oracle-simulator − copy-last-frame | Permutation p-value ↓ | -0.9444 | [-0.9549, -0.9340] | 12 |
| oracle-simulator − copy-last-frame | Counterfactual Direction | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − copy-last-frame | No-op Stability | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − copy-last-frame | State ADE ↓ | -0.8856 | [-0.8858, -0.8855] | 12 |
| oracle-simulator − copy-last-frame | State FDE ↓ | -1.0447 | [-1.0452, -1.0442] | 12 |
| oracle-simulator − copy-last-frame | CRC Spearman | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − copy-last-frame | CRC Kendall τ | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − copy-last-frame | CRC NDCG | 0.2897 | [0.1667, 0.4038] | 12 |
| oracle-simulator − copy-last-frame | CRC Pairwise Accuracy | 0.5000 | [0.5000, 0.5000] | 12 |
| oracle-simulator − copy-last-frame | Top-1 Regret ↓ | -1.0000 | [-1.0000, -1.0000] | 12 |
| oracle-simulator − wrong-direction | Action Dependence | 0.8265 | [0.8255, 0.8275] | 12 |
| oracle-simulator − wrong-direction | Permutation Effect | 2.2484 | [1.7095, 2.7873] | 12 |
| oracle-simulator − wrong-direction | Permutation p-value ↓ | -0.5000 | [-0.6562, -0.3438] | 12 |
| oracle-simulator − wrong-direction | Counterfactual Direction | 0.6313 | [0.6273, 0.6354] | 12 |
| oracle-simulator − wrong-direction | No-op Stability | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − wrong-direction | State ADE ↓ | -0.8387 | [-0.8393, -0.8380] | 12 |
| oracle-simulator − wrong-direction | State FDE ↓ | -0.9663 | [-0.9683, -0.9643] | 12 |
| oracle-simulator − wrong-direction | CRC Spearman | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − wrong-direction | CRC Kendall τ | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − wrong-direction | CRC NDCG | 0.2897 | [0.1754, 0.4038] | 12 |
| oracle-simulator − wrong-direction | CRC Pairwise Accuracy | 0.5000 | [0.5000, 0.5000] | 12 |
| oracle-simulator − wrong-direction | Top-1 Regret ↓ | -1.0000 | [-1.0000, -1.0000] | 12 |
| oracle-simulator − action-agnostic | Action Dependence | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − action-agnostic | Permutation Effect | 2.0096 | [1.9929, 2.0262] | 12 |
| oracle-simulator − action-agnostic | Permutation p-value ↓ | -0.9444 | [-0.9549, -0.9340] | 12 |
| oracle-simulator − action-agnostic | Counterfactual Direction | 0.4189 | [0.4177, 0.4201] | 12 |
| oracle-simulator − action-agnostic | No-op Stability | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − action-agnostic | State ADE ↓ | -0.6439 | [-0.6481, -0.6396] | 12 |
| oracle-simulator − action-agnostic | State FDE ↓ | -1.1560 | [-1.1593, -1.1527] | 12 |
| oracle-simulator − action-agnostic | CRC Spearman | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − action-agnostic | CRC Kendall τ | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − action-agnostic | CRC NDCG | 0.2897 | [0.1647, 0.4147] | 12 |
| oracle-simulator − action-agnostic | CRC Pairwise Accuracy | 0.5000 | [0.5000, 0.5000] | 12 |
| oracle-simulator − action-agnostic | Top-1 Regret ↓ | -1.0000 | [-1.0000, -1.0000] | 12 |

Action separation alone does not establish correct direction, state dynamics,
or control ranking. WAMProbe therefore reports a metric profile rather than a
single composite score.
