# WAMProbe PointMass-2D Demo

This report compares action-aware and deliberately broken reference baselines.

| Model | Action Dependence | Permutation Effect | Permutation p-value ↓ | Counterfactual Direction | No-op Stability | State ADE ↓ | State FDE ↓ | Top-1 Regret ↓ |
|---|---|---|---|---|---|---|---|---|
| oracle-pointmass | 1.0000 | 2.8542 | 0.0667 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| noisy-linear | 0.9886 | 2.7893 | 0.0667 | 0.9972 | 0.0000 | 0.0736 | 0.0927 | 0.0000 |
| copy-last-frame | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.5000 | 0.8000 | 1.0000 |
| wrong-direction | 1.0000 | 2.8542 | 0.0667 | -1.0000 | 1.0000 | 1.0000 | 1.6000 | 2.0000 |
| action-agnostic | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.7286 | 1.1657 | 1.0000 |

## Context-block 95% confidence intervals

Intervals resample whole contexts, not correlated action branches or frames.

| Model | Metric | Mean | 95% CI | Median | Std |
|---|---|---:|---:|---:|---:|
| oracle-pointmass | Action Dependence | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-pointmass | Permutation Effect | 2.8542 | [2.8542, 2.8542] | 2.8542 | 0.0000 |
| oracle-pointmass | Permutation p-value ↓ | 0.0667 | [0.0667, 0.0667] | 0.0667 | 0.0000 |
| oracle-pointmass | Counterfactual Direction | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-pointmass | No-op Stability | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| oracle-pointmass | State ADE ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| oracle-pointmass | State FDE ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| oracle-pointmass | Top-1 Regret ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| noisy-linear | Action Dependence | 0.9886 | [0.9787, 0.9966] | 0.9967 | 0.0149 |
| noisy-linear | Permutation Effect | 2.7893 | [2.7724, 2.8072] | 2.7865 | 0.0301 |
| noisy-linear | Permutation p-value ↓ | 0.0667 | [0.0667, 0.0667] | 0.0667 | 0.0000 |
| noisy-linear | Counterfactual Direction | 0.9972 | [0.9965, 0.9979] | 0.9973 | 0.0013 |
| noisy-linear | No-op Stability | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| noisy-linear | State ADE ↓ | 0.0736 | [0.0667, 0.0814] | 0.0736 | 0.0128 |
| noisy-linear | State FDE ↓ | 0.0927 | [0.0825, 0.1027] | 0.0895 | 0.0184 |
| noisy-linear | Top-1 Regret ↓ | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | Action Dependence | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | Permutation Effect | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | Permutation p-value ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| copy-last-frame | Counterfactual Direction | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| copy-last-frame | No-op Stability | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| copy-last-frame | State ADE ↓ | 0.5000 | [0.5000, 0.5000] | 0.5000 | 0.0000 |
| copy-last-frame | State FDE ↓ | 0.8000 | [0.8000, 0.8000] | 0.8000 | 0.0000 |
| copy-last-frame | Top-1 Regret ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| wrong-direction | Action Dependence | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| wrong-direction | Permutation Effect | 2.8542 | [2.8542, 2.8542] | 2.8542 | 0.0000 |
| wrong-direction | Permutation p-value ↓ | 0.0667 | [0.0667, 0.0667] | 0.0667 | 0.0000 |
| wrong-direction | Counterfactual Direction | -1.0000 | [-1.0000, -1.0000] | -1.0000 | 0.0000 |
| wrong-direction | No-op Stability | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| wrong-direction | State ADE ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| wrong-direction | State FDE ↓ | 1.6000 | [1.6000, 1.6000] | 1.6000 | 0.0000 |
| wrong-direction | Top-1 Regret ↓ | 2.0000 | [2.0000, 2.0000] | 2.0000 | 0.0000 |
| action-agnostic | Action Dependence | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | Permutation Effect | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | Permutation p-value ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |
| action-agnostic | Counterfactual Direction | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | No-op Stability | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 |
| action-agnostic | State ADE ↓ | 0.7286 | [0.7286, 0.7286] | 0.7286 | 0.0000 |
| action-agnostic | State FDE ↓ | 1.1657 | [1.1657, 1.1657] | 1.1657 | 0.0000 |
| action-agnostic | Top-1 Regret ↓ | 1.0000 | [1.0000, 1.0000] | 1.0000 | 0.0000 |

## Paired model differences

Differences are left minus right over exactly aligned context IDs.

| Models | Metric | Mean difference | 95% CI | Contexts |
|---|---|---:|---:|---:|
| oracle-pointmass − noisy-linear | Action Dependence | 0.0114 | [0.0035, 0.0215] | 12 |
| oracle-pointmass − noisy-linear | Permutation Effect | 0.0649 | [0.0487, 0.0818] | 12 |
| oracle-pointmass − noisy-linear | Permutation p-value ↓ | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-pointmass − noisy-linear | Counterfactual Direction | 0.0028 | [0.0020, 0.0035] | 12 |
| oracle-pointmass − noisy-linear | No-op Stability | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-pointmass − noisy-linear | State ADE ↓ | -0.0736 | [-0.0810, -0.0667] | 12 |
| oracle-pointmass − noisy-linear | State FDE ↓ | -0.0927 | [-0.1032, -0.0831] | 12 |
| oracle-pointmass − noisy-linear | Top-1 Regret ↓ | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-pointmass − copy-last-frame | Action Dependence | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-pointmass − copy-last-frame | Permutation Effect | 2.8542 | [2.8542, 2.8542] | 12 |
| oracle-pointmass − copy-last-frame | Permutation p-value ↓ | -0.9333 | [-0.9333, -0.9333] | 12 |
| oracle-pointmass − copy-last-frame | Counterfactual Direction | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-pointmass − copy-last-frame | No-op Stability | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-pointmass − copy-last-frame | State ADE ↓ | -0.5000 | [-0.5000, -0.5000] | 12 |
| oracle-pointmass − copy-last-frame | State FDE ↓ | -0.8000 | [-0.8000, -0.8000] | 12 |
| oracle-pointmass − copy-last-frame | Top-1 Regret ↓ | -1.0000 | [-1.0000, -1.0000] | 12 |
| oracle-pointmass − wrong-direction | Action Dependence | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-pointmass − wrong-direction | Permutation Effect | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-pointmass − wrong-direction | Permutation p-value ↓ | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-pointmass − wrong-direction | Counterfactual Direction | 2.0000 | [2.0000, 2.0000] | 12 |
| oracle-pointmass − wrong-direction | No-op Stability | 0.0000 | [0.0000, 0.0000] | 12 |
| oracle-pointmass − wrong-direction | State ADE ↓ | -1.0000 | [-1.0000, -1.0000] | 12 |
| oracle-pointmass − wrong-direction | State FDE ↓ | -1.6000 | [-1.6000, -1.6000] | 12 |
| oracle-pointmass − wrong-direction | Top-1 Regret ↓ | -2.0000 | [-2.0000, -2.0000] | 12 |
| oracle-pointmass − action-agnostic | Action Dependence | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-pointmass − action-agnostic | Permutation Effect | 2.8542 | [2.8542, 2.8542] | 12 |
| oracle-pointmass − action-agnostic | Permutation p-value ↓ | -0.9333 | [-0.9333, -0.9333] | 12 |
| oracle-pointmass − action-agnostic | Counterfactual Direction | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-pointmass − action-agnostic | No-op Stability | 1.0000 | [1.0000, 1.0000] | 12 |
| oracle-pointmass − action-agnostic | State ADE ↓ | -0.7286 | [-0.7286, -0.7286] | 12 |
| oracle-pointmass − action-agnostic | State FDE ↓ | -1.1657 | [-1.1657, -1.1657] | 12 |
| oracle-pointmass − action-agnostic | Top-1 Regret ↓ | -1.0000 | [-1.0000, -1.0000] | 12 |

A high Action Dependence score is not sufficient: the wrong-direction baseline
depends on the action but fails Counterfactual Direction Accuracy. WAMProbe
therefore reports a metric profile rather than a single composite score.
