# Core metric cards

WAMProbe reports a profile rather than one composite score. All aggregate confidence
intervals resample complete shared contexts; action branches and frames from one context
are never treated as independent samples.

| Metric | Requires | Definition | Direction / range | Principal limitation |
|---|---|---|---|---|
| Action Dependence | paired candidate futures | mean predicted pair separation normalized by true separation | higher; analytic implementation clipped to [0,1] | separation can be confidently wrong |
| ADS permutation effect | paired action/future alignment | observed action-future association minus within-context permutation null | higher is stronger alignment | small branch sets give coarse p-values |
| ADS permutation p-value | same | add-one Monte Carlo randomization probability | lower is stronger evidence | not an effect size and not independent across frames |
| Counterfactual Direction | vector states | cosine of predicted and true displacement | -1 opposite, 0 absent/orthogonal, 1 aligned | ignores calibrated magnitude |
| No-op Stability/Fidelity | explicit no-op truth | point-mass drift score or exact manipulation no-op fidelity | higher is better | a static model can pass no-op alone |
| State ADE | typed state trajectory | mean Euclidean error over steps and branches | lower, ≥0 | state dimensions and units must be semantically aligned |
| State FDE | typed state trajectory | mean final-state Euclidean error | lower, ≥0 | can hide transient physical violations |
| CRC Spearman | candidate returns | rank correlation with average tie ranks | higher, [-1,1] | unstable for very small/tied candidate sets |
| CRC Kendall tau-b | candidate returns | concordant-minus-discordant pairs with tie correction | higher, [-1,1] | ignores return magnitude |
| CRC NDCG | candidate returns | discounted gain after shifting relevance non-negative | higher, [0,1] | shift convention must stay fixed |
| CRC pairwise accuracy | candidate returns | correct preference fraction; model ties receive 0.5 | higher, [0,1] | true-return ties are excluded |
| Top-1 Regret | candidate returns | oracle return minus return of model-selected candidate | lower, ≥0 | depends on candidate-set coverage |
| RGB PSNR | same-shape rendered RGB frames | `10 log10(255²/MSE)`, averaged over branches and frames | higher, dB; exact matches capped at 100 dB | pixel alignment and appearance can disagree with dynamics/control value |
| Global SSIM diagnostic | same-camera rendered RGB frames | mean per-channel luminance/contrast/structure over each whole frame | higher, typically [-1,1] | not standard windowed SSIM and can hide local/contact errors |
| Closed-loop return | repeated candidate scoring + true transition | task return after score-execute-observe replanning | higher; task-specific units | depends on candidate generator, scorer and execution budget |
| Closed-loop success | shared context and oracle control | fraction matching the simulator-future scorer's return within the fixed tolerance | higher, [0,1] | toy equality threshold is not a general task-success definition |
| Closed-loop oracle gap | same | simulator-future return minus controller return per context | lower; 0 matches reference | a greedy simulator scorer is not a proof of globally optimal control |
| Latency | timed model call | synchronized wall time per prediction | lower, seconds | hardware and warm-up dependent |
| Peak allocated/reserved memory | CUDA runtime | maximum allocator bytes during one prediction | lower, GiB | not total board memory or energy |
| NFE sensitivity | matched inputs/seeds | paired action RMS and executed endpoint distance across NFE | lower means more stable | stability does not establish correctness |
| Seed sensitivity | matched inputs/NFE | paired action RMS and executed endpoint distance across seeds | lower means more stable | deterministic collapse can also score low |
| Branch EEF/object separation | paired simulator futures | mean pairwise final-state distance | diagnostic, ≥0 | raw object vectors are comparable only within a task |
| No-op EEF drift | explicit simulator no-op | distance from initial to final EEF | lower, ≥0 | controller settling can produce small nonzero drift |

## Applicability rules

Metrics are gated by the adapter capability manifest. Missing inputs produce an explicit
skip, never a surrogate value. In particular, the released StarWAM adapter emits actions
but no action-conditioned future artifact. WAMProbe therefore skips candidate-action
mask/shuffle, predicted-video PSNR/SSIM/FVD and future-state ADE/FDE for that adapter.

An undefined correlation caused by a constant outcome is serialized as JSON `null` and
explained in the report. A zero sparse success rate remains a reported negative result;
it is not dropped from aggregation.

PSNR and global SSIM are secondary diagnostics only. They require pixel futures in the
same camera geometry and are never substituted for a missing state, causal, ranking, or
regret metric. The built-in global variant is deliberately named `global_ssim`; reports
must not label it as standard windowed SSIM. Exact PSNR matches use a finite 100 dB cap so
JSON remains portable.

Closed-loop metrics additionally require a legal candidate generator, a fixed task scorer,
an executable transition, and an explicit replanning contract. WAMProbe records the total
control steps, executed prefix, candidate tie order and per-context action sequence. The
scoring window is capped by the remaining execution budget. Controllers without predicted
candidate futures retain `null` offline CRC/regret rather than receiving invented values.

## Reference-baseline expectations

- Oracle dynamics should minimize ADE/FDE and regret while maximizing direction and CRC.
- Copy-last and action-agnostic baselines should have weak action dependence and ranking.
- Wrong-direction should separate futures but have negative direction correctness.
- Seeded noisy dynamics should degrade ADE/FDE and ranking as noise rises.
- Appearance-corrupted oracle futures should preserve exact FDE/CRC/regret while degrading
  PSNR/global SSIM, demonstrating that video fidelity cannot replace control grounding.
- Oracle/noisy future scorers should outperform copy-last, wrong-direction, and
  action-agnostic scorers in the analytic closed loop; random and action-only controls stay
  visible rather than being folded into a composite score.

Any new metric must add a failure-mode statement, capability requirement, reference
ordering test, aggregation unit and range/direction before it enters a public report.
