# WAM/VLA failure-case evidence map

- Status: Phase 0 literature screen
- Evidence cutoff: 2026-07-15
- Scope: World Action Models (WAMs), video-action models, and closely related VLAs

## Purpose

This document turns reported WAM/VLA weaknesses into testable requirements for
WAMProbe. It is an evidence map, not an independent reproduction of every cited result.
The central question is whether a model's predicted future is controlled by the proposed
action and useful for control, rather than merely plausible or correlated with success.

## Evidence labels

- **R1 — reported empirical finding:** the cited paper reports a controlled comparison,
  diagnostic, or quantified result. WAMProbe has not independently reproduced it yet.
- **R2 — author-stated limitation:** the cited paper states the problem as motivation; the
  exact failure rate may depend on its setup.
- **H — WAMProbe hypothesis:** a proposed probe or expected result. It must not be quoted
  as a literature finding until tested.

Sources are version-pinned arXiv records or official repositories. Cases based only on an
abstract are kept at R2 unless the abstract explicitly describes a controlled empirical
study. Three central papers—dynamic consistency, behavioral diagnostics, and Fast-WAM—
were additionally checked against their full text.

## Case index

| ID | Reported failure or ambiguity | Evidence | WAMProbe test direction | Source |
|---|---|---|---|---|
| FC-01 | Final success hides target progress, distractor motion, action smoothness, and runtime differences | R1 | behavior profile beside success | [S1] |
| FC-02 | A future can look plausible while being dynamically incompatible with its action | R1 | paired action-state consistency | [S2] |
| FC-03 | Static/background collapse can make a failed rollout deceptively consistent | R1 | consistency plus a minimum-dynamics guard | [S2] |
| FC-04 | Fixed action chunks keep executing after the imagined future diverges from reality | R1 | prefix consistency and adaptive replanning signal | [S3] |
| FC-05 | One stochastic diffusion sample is brittle and errors compound over an episode | R1 | multi-seed calibration and candidate regret | [S4] |
| FC-06 | Pixel prediction entangles dynamics with lighting/texture and weakens under occlusion or off-screen motion | R1 | perturbation invariance plus track/state probes | [S5] |
| FC-07 | Robot-data fine-tuning can erase compositional priors inherited from video pretraining | R1 | ID/OOD compositional split and feature reliance | [S6] |
| FC-08 | Uniform action loss underweights slow, precision-critical interaction phases | R1 | phase-stratified metrics around contact | [S7] |
| FC-09 | Policies can exploit scene-level shortcuts instead of causally relevant objects | R1 | object/distractor counterfactual swaps | [S8] |
| FC-10 | Numerical actions can misalign with video priors; visual action encodings can miss temporal motion | R1 | representation-aware action intervention tests | [S9] |
| FC-11 | Dense video imagination spends compute on irrelevant details and long-horizon errors can mislead control | R1 | budgeted utility and horizon sweep | [S10] |
| FC-12 | Test-time future generation may add large latency without improving task success | R1 | matched-training inference ablation | [S11] |
| FC-13 | Strong semantic VLAs can still fail on unseen physical motions and environments | R1 | physical-motion OOD split | [S12] |
| FC-14 | Learned policies can fail when hidden dynamics such as mass or friction change | R1 | simulator parameter interventions | [S13] |
| FC-15 | Robustness depends on how video priors are integrated, not merely on the WAM/VLA label | R1 | capability- and architecture-stratified reporting | [S14] |

## Detailed implications

### FC-01: success-only evaluation hides behavior

Mai et al. report that success rate alone conceals differences in motion consistency,
target-object progress, distractor disturbance, runtime, and future-oriented internal
representations. They also find that the pattern varies across sequential, joint, and
auxiliary WAM designs [S1].

**H:** WAMProbe should never replace its metric profile with one aggregate score. LIBERO
evaluation should pair success with target progress, distractor displacement, control
smoothness, and runtime. Results must be grouped by declared capability and architecture.

### FC-02: plausible is not action-compatible

Ruan et al. show that action-state consistency separates many successful and failed
rollouts and captures information beyond visual realism [S2]. Their full text reports that
a generated future may misrepresent contact or object motion while remaining visually
plausible.

**H:** shared-state action branches are WAMProbe's primary unit. Counterfactual Direction
Accuracy, state ADE/FDE, and candidate regret should be reported together; video quality is
secondary and cannot establish action grounding.

### FC-03: static futures can game consistency

The same study identifies *background collapse*: a failed, low-motion trajectory can
receive a favorable consistency score because a static background is easy to predict
[S2]. This is a concrete warning that consistency itself can be gamed.

**H:** any learned action-state consistency metric needs a transition-magnitude diagnostic.
Near-static non-noop branches should be flagged, while true no-op branches remain a
separate No-op Stability test. A model must not gain credit merely by predicting no change.

### FC-04: fixed chunks ignore future-reality divergence

Wang et al. identify a deployment failure in which a WAM executes a fixed action chunk
without checking whether reality still matches the predicted future. Their adaptive
verifier replans earlier in difficult or contact-rich phases and reports improved real-world
success [S3].

**H:** introduce Horizon Prefix Consistency before closed-loop utility. Measure the first
time at which predicted and realized state prefixes diverge, then correlate that event with
the action-chunk length that should have been executed.

### FC-05: a single stochastic sample is brittle

Dai et al. attribute brittleness to committing to one stochastic diffusion/flow action
sample per round and report improvements from parallel candidate sampling and geometric
consensus [S4].

**H:** adapters with stochastic generation must expose deterministic seeds. WAMProbe
should report per-context seed variance, candidate ranking stability, calibration, and
Top-1 Regret rather than evaluating one lucky rollout.

### FC-06: pixels entangle dynamics and appearance

Guan et al. report that pixel prediction entangles dynamics with lighting and texture.
Their point-track representation is intended to preserve long-horizon motion through
occlusion and partial out-of-frame movement, with the largest reported gains on those
settings [S5].

**H:** the pixel benchmark should include lighting/texture perturbations that preserve
dynamics. Where simulator state or tracks are available, WAMProbe should compare them
with pixel metrics instead of treating pixel similarity as ground truth.

### FC-07: video priors can be lost during robot fine-tuning

Mishra et al. systematically study a video-action generalization gap: compositional priors
present in a generative video model can weaken after fine-tuning on robot actions [S6].
They report that reliance on future-predictive latents changes with task phase.

**H:** evaluate identical models on ID and compositional-OOD intervention groups. Feature
reliance should be measured separately for planning, approach, contact, and precision
phases rather than averaged over an episode.

### FC-08: not every action timestep is equally important

Peng et al. identify a mismatch between uniform loss weighting and manipulation's
physical hierarchy: low-velocity interaction segments can decide success while fast
transit segments tolerate larger errors [S7].

**H:** state ADE must be accompanied by phase-conditioned ADE/FDE and control regret.
Errors around contact, release, and low-velocity alignment should be reported separately.

### FC-09: scene shortcuts can replace causal grounding

Sun et al. identify shortcut learning in robotic foundation models: policies exploit
predictive but non-causal scene correlations rather than task-relevant visual evidence
[S8]. Their experiments cover VLA and WAM-style pipelines.

**H:** construct paired scenes that change background, distractor identity, or irrelevant
object placement while preserving task dynamics. A grounded model's action ranking and
relevant future transition should remain stable.

### FC-10: action representation can be mismatched

Chen et al. argue that numerical robot actions do not align naturally with pretrained video
generators, while earlier visual action representations can omit temporal motion structure.
Their optical-flow formulation reports gains in both policy and world-model modes [S9].

**H:** metric requirements must be representation-aware. State actions, end-effector
trajectories, point tracks, flow, and latent actions need explicit conversion metadata; an
unsupported comparison must be skipped rather than silently approximated.

### FC-11: more imagined frames are not automatically more useful

Zhang et al. identify three coupled limitations of video-based WAMs: dense multi-frame
tokens increase inference cost, video prediction spends capacity on action-irrelevant
details, and long-horizon errors may mislead action prediction [S10]. Their ImageWAM
results report lower cost with target-frame editing features.

**H:** sweep prediction horizon and compute budget. Report control utility per unit latency
and memory, and check whether longer futures reduce Top-1 Regret instead of assuming that
more frames imply better world understanding.

### FC-12: decoded future imagination may have little control value

Fast-WAM provides a controlled comparison between video co-training and explicit future
generation at inference. Its full text reports similar benchmark success for Fast-WAM and
imagine-then-execute variants, while the latter have substantially higher latency; removing
video co-training causes a much larger performance drop [S11].

**H:** WAMProbe must distinguish `future_pixels`, `world_features`, and `action_only`
capabilities. Compare models with matched training while masking or bypassing decoded
future generation, then report both control utility and cost.

### FC-13: semantic generalization is not physical generalization

Ye et al. motivate DreamZero with the observation that strong VLAs can generalize
semantically yet struggle with unseen physical motions and novel environments [S12]. They
report improved real-robot generalization from joint video-action modeling.

**H:** benchmark splits should independently vary language, object identity, geometry,
motion, and environment. A single OOD average cannot reveal which form of generalization
the model acquired.

### FC-14: hidden dynamics shift

Lyu et al. report that prior learning-based manipulation methods depend on multi-view/pose
tracking and fail to generalize across changes such as object mass and table friction [S13].

**H:** paired simulator snapshots should vary one hidden physical parameter at a time.
Measure whether the predicted action effect, uncertainty, and candidate ranking change in
the correct direction.

### FC-15: architecture matters more than the family label

Zhang et al. compare WAMs, VLAs, and hybrids under visual and language perturbations and
report that robustness varies with how video priors are integrated; hybrid methods occupy
an intermediate regime [S14]. This complements the architecture-dependent behavior found
in [S1].

**H:** WAMProbe reports no universal “WAM versus VLA” winner. Every result row must carry
a capability manifest and architecture tag, and comparisons must remain within compatible
output groups.

## Resulting v0.1 priorities

The literature screen changes implementation order in five ways:

1. add context-block confidence intervals and seed variance before adding learned metrics;
2. add a low-dynamics/background-collapse guard to future consistency evaluation;
3. make task phase and contact state first-class benchmark metadata;
4. report budgeted control utility beside prediction quality;
5. preserve capability-stratified reports rather than creating a composite leaderboard.

## Sources

- **[S1]** Mai et al., “Beyond Task Success: Behavioral and Representational
  Diagnostics for WAM and VLA,” [arXiv:2606.01095v1](https://arxiv.org/abs/2606.01095v1).
- **[S2]** Ruan et al., “Is the Future Compatible? Diagnosing Dynamic Consistency in
  World Action Models,” [arXiv:2605.07514v1](https://arxiv.org/abs/2605.07514v1).
- **[S3]** Wang et al., “When to Trust Imagination: Adaptive Action Execution for World
  Action Models,” [arXiv:2605.06222v2](https://arxiv.org/abs/2605.06222v2).
- **[S4]** Dai et al., “Geometry Guided Self-Consistency for Physical AI,”
  [arXiv:2605.08638v1](https://arxiv.org/abs/2605.08638v1).
- **[S5]** Guan et al., “Point Tracking Improves World Action Models,”
  [arXiv:2605.23856v1](https://arxiv.org/abs/2605.23856v1).
- **[S6]** Mishra et al., “Understanding and Mitigating the Video-Action Generalization
  Gap via Temporal Ratio,” [arXiv:2607.08127v1](https://arxiv.org/abs/2607.08127v1).
- **[S7]** Peng et al., “AttenA+: Rectifying Action Inequality in Robotic Foundation
  Models,” [arXiv:2605.13548v3](https://arxiv.org/abs/2605.13548v3).
- **[S8]** Sun et al., “Artificial Foveated Perception for Mitigating Shortcut Learning in
  Robotic Foundation Models,” [arXiv:2607.10655v1](https://arxiv.org/abs/2607.10655v1).
- **[S9]** Chen et al., “FlowWAM: Optical Flow as a Unified Action Representation for
  World Action Models,” [arXiv:2607.13017v1](https://arxiv.org/abs/2607.13017v1).
- **[S10]** Zhang et al., “ImageWAM: Do World Action Models Really Need Video
  Generation, or Just Image Editing?,”
  [arXiv:2606.19531v1](https://arxiv.org/abs/2606.19531v1).
- **[S11]** Yuan et al., “Fast-WAM: Do World Action Models Need Test-time Future
  Imagination?,” [arXiv:2603.16666v2](https://arxiv.org/abs/2603.16666v2).
- **[S12]** Ye et al., “World Action Models are Zero-shot Policies,”
  [arXiv:2602.15922v1](https://arxiv.org/abs/2602.15922v1).
- **[S13]** Lyu et al., “DyWA: Dynamics-adaptive World Action Model for Generalizable
  Non-prehensile Manipulation,”
  [arXiv:2503.16806v2](https://arxiv.org/abs/2503.16806v2).
- **[S14]** Zhang et al., “Do World Action Models Generalize Better than VLAs? A
  Robustness Study,” [arXiv:2603.22078v3](https://arxiv.org/abs/2603.22078v3).

## Known limits of this screen

- It records claims made by the cited authors; it does not certify their experimental
  validity or compare incompatible benchmark versions.
- Several sources are recent preprints and may change after the pinned arXiv version.
- The external-reader comprehension check in Phase 0 still requires a human reviewer and
  cannot be completed by repository automation.
- Each accepted metric still needs a dedicated RFC, reference baseline behavior, and a
  reproducible sanity test before implementation.
