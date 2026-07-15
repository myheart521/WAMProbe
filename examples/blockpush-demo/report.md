# WAMProbe blockpush-2d-v0.1 Demo

This report compares action-aware and deliberately broken reference baselines.

| Model | Action Dependence | Permutation Effect | Permutation p-value ↓ | Counterfactual Direction | No-op Stability | State ADE ↓ | State FDE ↓ | CRC Spearman | CRC Kendall τ | CRC NDCG | CRC Pairwise Accuracy | Top-1 Regret ↓ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| oracle-simulator | 1.0000 | 2.1138 | 0.0167 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| noisy-dynamics | 0.9907 | 2.1119 | 0.0167 | 0.9978 | 0.0000 | 0.0427 | 0.0355 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| copy-last-frame | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.3031 | 0.4369 | 0.0000 | 0.0000 | 0.4871 | 0.5000 | 0.3000 |
| wrong-direction | 1.0000 | -0.1578 | 0.4833 | -0.6630 | 1.0000 | 0.5548 | 0.7953 | -0.2500 | -0.2500 | 0.4371 | 0.3750 | 0.3000 |
| action-agnostic | 0.0000 | 0.0000 | 1.0000 | 0.1685 | 0.0000 | 0.7361 | 0.9391 | 0.0000 | 0.0000 | 0.4871 | 0.5000 | 0.3000 |

## Context-block 95% confidence intervals

Intervals resample whole contexts, not correlated action branches or frames.

| Model | Metric | Mean | 95% CI | Median | Std |
|---|---|---:|---:|---:|---:|
| oracle-simulator | Action Dependence | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | Permutation Effect | 2.1138 | [2.1138, 2.1138] | 2.1138 | 0.0000 |
| oracle-simulator | Permutation p-value ↓ | 0.0167 | [0.0167, 0.0167] | 0.0167 | 0.0000 |
| oracle-simulator | Counterfactual Direction | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | No-op Stability | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | State ADE ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| oracle-simulator | State FDE ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| oracle-simulator | CRC Spearman | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | CRC Kendall τ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | CRC NDCG | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | CRC Pairwise Accuracy | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-simulator | Top-1 Regret ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| noisy-dynamics | Action Dependence | 0.9907 | [0.9849, 0.9959] | 0.9934 | 0.0100 |
| noisy-dynamics | Permutation Effect | 2.1119 | [2.1091, 2.1149] | 2.1136 | 0.0052 |
| noisy-dynamics | Permutation p-value ↓ | 0.0167 | [0.0167, 0.0167] | 0.0167 | 0.0000 |
| noisy-dynamics | Counterfactual Direction | 0.9978 | [0.9968, 0.9988] | 0.9982 | 0.0018 |
| noisy-dynamics | No-op Stability | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| noisy-dynamics | State ADE ↓ | 0.0427 | [0.0319, 0.0538] | 0.0428 | 0.0196 |
| noisy-dynamics | State FDE ↓ | 0.0355 | [0.0293, 0.0416] | 0.0353 | 0.0114 |
| noisy-dynamics | CRC Spearman | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| noisy-dynamics | CRC Kendall τ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| noisy-dynamics | CRC NDCG | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| noisy-dynamics | CRC Pairwise Accuracy | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| noisy-dynamics | Top-1 Regret ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | Action Dependence | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | Permutation Effect | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | Permutation p-value ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| copy-last-frame | Counterfactual Direction | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | No-op Stability | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| copy-last-frame | State ADE ↓ | 0.3031 | [0.3031, 0.3031] | 0.3031 | 0.0000 |
| copy-last-frame | State FDE ↓ | 0.4369 | [0.4369, 0.4369] | 0.4369 | 0.0000 |
| copy-last-frame | CRC Spearman | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | CRC Kendall τ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | CRC NDCG | 0.4871 | [0.4407, 0.5423] | 0.4653 | 0.0923 |
| copy-last-frame | CRC Pairwise Accuracy | 0.5000 | [0.5000, 0.5000] | 0.5000 | 0.0000 |
| copy-last-frame | Top-1 Regret ↓ | 0.3000 | [0.3000, 0.3000] | 0.3000 | 0.0000 |
| wrong-direction | Action Dependence | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| wrong-direction | Permutation Effect | -0.1578 | [-0.1578, -0.1578] | -0.1578 | 0.0000 |
| wrong-direction | Permutation p-value ↓ | 0.4833 | [0.4833, 0.4833] | 0.4833 | 0.0000 |
| wrong-direction | Counterfactual Direction | -0.6630 | [-0.6630, -0.6630] | -0.6630 | 0.0000 |
| wrong-direction | No-op Stability | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| wrong-direction | State ADE ↓ | 0.5548 | [0.5548, 0.5548] | 0.5548 | 0.0000 |
| wrong-direction | State FDE ↓ | 0.7953 | [0.7953, 0.7953] | 0.7953 | 0.0000 |
| wrong-direction | CRC Spearman | -0.2500 | [-0.2500, -0.2500] | -0.2500 | 0.0000 |
| wrong-direction | CRC Kendall τ | -0.2500 | [-0.2500, -0.2500] | -0.2500 | 0.0000 |
| wrong-direction | CRC NDCG | 0.4371 | [0.4160, 0.4596] | 0.4307 | 0.0405 |
| wrong-direction | CRC Pairwise Accuracy | 0.3750 | [0.3750, 0.3750] | 0.3750 | 0.0000 |
| wrong-direction | Top-1 Regret ↓ | 0.3000 | [0.3000, 0.3000] | 0.3000 | 0.0000 |
| action-agnostic | Action Dependence | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | Permutation Effect | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | Permutation p-value ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| action-agnostic | Counterfactual Direction | 0.1685 | [0.1685, 0.1685] | 0.1685 | 0.0000 |
| action-agnostic | No-op Stability | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | State ADE ↓ | 0.7361 | [0.7361, 0.7361] | 0.7361 | 0.0000 |
| action-agnostic | State FDE ↓ | 0.9391 | [0.9391, 0.9391] | 0.9391 | 0.0000 |
| action-agnostic | CRC Spearman | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | CRC Kendall τ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | CRC NDCG | 0.4871 | [0.4392, 0.5387] | 0.4653 | 0.0923 |
| action-agnostic | CRC Pairwise Accuracy | 0.5000 | [0.5000, 0.5000] | 0.5000 | 0.0000 |
| action-agnostic | Top-1 Regret ↓ | 0.3000 | [0.3000, 0.3000] | 0.3000 | 0.0000 |

## Paired model differences

Differences are left minus right over exactly aligned context IDs.

| Models | Metric | Mean difference | 95% CI | Contexts |
|---|---|---:|---:|---:|
| oracle-simulator − noisy-dynamics | Action Dependence | 0.0093 | [0.0041, 0.0152] | 12 |
| oracle-simulator − noisy-dynamics | Permutation Effect | 0.0019 | [-0.0008, 0.0050] | 12 |
| oracle-simulator − noisy-dynamics | Permutation p-value ↓ | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − noisy-dynamics | Counterfactual Direction | 0.0022 | [0.0012, 0.0032] | 12 |
| oracle-simulator − noisy-dynamics | No-op Stability | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − noisy-dynamics | State ADE ↓ | -0.0427 | [-0.0531, -0.0314] | 12 |
| oracle-simulator − noisy-dynamics | State FDE ↓ | -0.0355 | [-0.0419, -0.0285] | 12 |
| oracle-simulator − noisy-dynamics | CRC Spearman | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − noisy-dynamics | CRC Kendall τ | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − noisy-dynamics | CRC NDCG | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − noisy-dynamics | CRC Pairwise Accuracy | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − noisy-dynamics | Top-1 Regret ↓ | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − copy-last-frame | Action Dependence | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − copy-last-frame | Permutation Effect | 2.1138 | [2.1138, 2.1138] | 12 |
| oracle-simulator − copy-last-frame | Permutation p-value ↓ | -0.9833 | [-0.9833, -0.9833] | 12 |
| oracle-simulator − copy-last-frame | Counterfactual Direction | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − copy-last-frame | No-op Stability | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − copy-last-frame | State ADE ↓ | -0.3031 | [-0.3031, -0.3031] | 12 |
| oracle-simulator − copy-last-frame | State FDE ↓ | -0.4369 | [-0.4369, -0.4369] | 12 |
| oracle-simulator − copy-last-frame | CRC Spearman | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − copy-last-frame | CRC Kendall τ | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − copy-last-frame | CRC NDCG | 0.5129 | [0.4634, 0.5615] | 12 |
| oracle-simulator − copy-last-frame | CRC Pairwise Accuracy | 0.5000 | [0.5000, 0.5000] | 12 |
| oracle-simulator − copy-last-frame | Top-1 Regret ↓ | -0.3000 | [-0.3000, -0.3000] | 12 |
| oracle-simulator − wrong-direction | Action Dependence | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − wrong-direction | Permutation Effect | 2.2716 | [2.2716, 2.2716] | 12 |
| oracle-simulator − wrong-direction | Permutation p-value ↓ | -0.4667 | [-0.4667, -0.4667] | 12 |
| oracle-simulator − wrong-direction | Counterfactual Direction | 1.6630 | [1.6630, 1.6630] | 12 |
| oracle-simulator − wrong-direction | No-op Stability | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-simulator − wrong-direction | State ADE ↓ | -0.5548 | [-0.5548, -0.5548] | 12 |
| oracle-simulator − wrong-direction | State FDE ↓ | -0.7953 | [-0.7953, -0.7953] | 12 |
| oracle-simulator − wrong-direction | CRC Spearman | 1.2500 | [1.2500, 1.2500] | 12 |
| oracle-simulator − wrong-direction | CRC Kendall τ | 1.2500 | [1.2500, 1.2500] | 12 |
| oracle-simulator − wrong-direction | CRC NDCG | 0.5629 | [0.5404, 0.5855] | 12 |
| oracle-simulator − wrong-direction | CRC Pairwise Accuracy | 0.6250 | [0.6250, 0.6250] | 12 |
| oracle-simulator − wrong-direction | Top-1 Regret ↓ | -0.3000 | [-0.3000, -0.3000] | 12 |
| oracle-simulator − action-agnostic | Action Dependence | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − action-agnostic | Permutation Effect | 2.1138 | [2.1138, 2.1138] | 12 |
| oracle-simulator − action-agnostic | Permutation p-value ↓ | -0.9833 | [-0.9833, -0.9833] | 12 |
| oracle-simulator − action-agnostic | Counterfactual Direction | 0.8315 | [0.8315, 0.8315] | 12 |
| oracle-simulator − action-agnostic | No-op Stability | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − action-agnostic | State ADE ↓ | -0.7361 | [-0.7361, -0.7361] | 12 |
| oracle-simulator − action-agnostic | State FDE ↓ | -0.9391 | [-0.9391, -0.9391] | 12 |
| oracle-simulator − action-agnostic | CRC Spearman | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − action-agnostic | CRC Kendall τ | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-simulator − action-agnostic | CRC NDCG | 0.5129 | [0.4570, 0.5645] | 12 |
| oracle-simulator − action-agnostic | CRC Pairwise Accuracy | 0.5000 | [0.5000, 0.5000] | 12 |
| oracle-simulator − action-agnostic | Top-1 Regret ↓ | -0.3000 | [-0.3000, -0.3000] | 12 |

Action separation alone does not establish correct direction, state dynamics,
or control ranking. WAMProbe therefore reports a metric profile rather than a
single composite score.
