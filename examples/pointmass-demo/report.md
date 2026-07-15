# WAMProbe PointMass-2D Demo

This report compares action-aware and deliberately broken reference baselines.

| Model | Action Dependence | Counterfactual Direction | No-op Stability | State ADE ↓ | Top-1 Regret ↓ |
|---|---|---|---|---|---|
| oracle-pointmass | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| copy-last-frame | 0.0000 | 0.0000 | 1.0000 | 0.5000 | 1.0000 |
| wrong-direction | 1.0000 | -1.0000 | 1.0000 | 1.0000 | 2.0000 |
| action-agnostic | 0.0000 | 0.0000 | 0.0000 | 0.7286 | 1.0000 |

A high Action Dependence score is not sufficient: the wrong-direction baseline
depends on the action but fails Counterfactual Direction Accuracy. This is why
WAMProbe reports a metric profile instead of a single aggregate score.
