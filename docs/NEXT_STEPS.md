# Next steps / 后续路线图

This roadmap separates work that can be automated in the repository from gates
that require independent people or new scientific evidence. A checked code task
must never be used as a substitute for an unmet evidence gate.

本路线图区分“仓库内可以自动完成的工程任务”和“必须由独立用户或新实验提供证据的验收
门槛”。代码完成不代表外部证据已经满足。

## Dependency path / 依赖关系

```text
P0 independent reproduction ──► P1 final v0.1.0

P2 contributor readiness ──► P3 broader paired benchmarks
                         └──► P4 action-conditioned real WAM

P1 stable release + public evidence ──► P5 DOI and outreach
```

## Milestones / 里程碑

| Priority | Milestone | Current state | Completion evidence |
|---|---|---|---|
| P0 | Independent clean-install reproduction / 独立干净环境复现 | **Blocked by an independent user** | A non-maintainer posts commit, environment, commands, exit status, elapsed time, and output hash in Issue #2 |
| P1 | Promote `v0.1.0rc1` to `v0.1.0` / 发布正式版 | **Blocked by P0** | P0 accepted, release audit green, signed/tagged release artifacts and provenance available |
| P2 | Contributor readiness / 贡献者接入能力 | **In progress** | Runnable adapter starter, contribution/result forms, roadmap, labeled starter issues, green CI |
| P3 | Broader paired diagnostics / 扩展配对诊断 | **Planned** | More LIBERO initial states plus Occluded-Object memory benchmark with restore/order checks |
| P4 | Real action-conditioned WAM evidence / 真实动作条件 WAM | **Planned; model capability required** | Public model exposes candidate-conditioned futures, adapter passes semantic tests, bounded report is reproducible |
| P5 | Archival and outreach / 归档与传播 | **After stable release** | Zenodo DOI, updated citation metadata, release notes, public result call |

Tracked work:

- P0: [independent reproduction gate #2](https://github.com/myheart521/WAMProbe/issues/2)
- P3: [LIBERO initial-state coverage #10](https://github.com/myheart521/WAMProbe/issues/10)
  and [Occluded-Object RFC #7](https://github.com/myheart521/WAMProbe/issues/7)
- P4: [public action-conditioned WAM audit #9](https://github.com/myheart521/WAMProbe/issues/9)
- Starter contributions: [adapter troubleshooting #11](https://github.com/myheart521/WAMProbe/issues/11)
  and [malformed-output tests #12](https://github.com/myheart521/WAMProbe/issues/12)
- P5: [Zenodo DOI preparation #8](https://github.com/myheart521/WAMProbe/issues/8)

## P0 — independent reproduction

The maintainer can improve instructions and debug a failed report, but cannot
perform this acceptance item on the maintainer's own machine. The external user
should use the **External reproduction** issue form. Issue #2 remains the source
of truth.

维护者可以完善说明、协助排错，但不能在自己的机器上代替外部用户完成验收。真实独立用户
应通过 **External reproduction** 表单提交，Issue #2 是唯一验收记录。

## P1 — stable release gate

After P0 is accepted:

1. confirm the candidate commit is clean and all required CI/security checks pass;
2. run the documented reproducible build and archive audit;
3. update version, changelog, citation, and release notes consistently;
4. publish the final tag and artifacts through the release workflow;
5. verify a clean install from the published package.

Do not publish `v0.1.0` before P0.

## P2 — contributor readiness

Repository-owned deliverables:

- a tested `examples/custom_adapter` integration path;
- a detailed adapter guide with semantic and provenance checks;
- structured experiment-result and external-reproduction issue forms;
- visible, labeled, bounded issues suitable for first-time contributors;
- README and documentation-site links to each contribution path.

## P3 — benchmark expansion

Two bounded tracks should remain separate:

- **LIBERO-CF-Mini coverage:** add initial states and perturbations while preserving
  snapshot restore, shared-context pairing, deterministic action order reversal,
  asset licensing, and split/leakage documentation.
- **Occluded-Object diagnostic:** test whether action-conditioned futures retain a
  task-relevant object after it becomes unobserved. Define oracle, copy-last,
  memoryless, and wrong-memory baselines before adding a learned model.

Every addition needs a benchmark card, generation or conversion code, hashes,
and expected-ordering tests.

## P4 — real WAM integration

Select a public model only when its actual interface can produce a future for
each proposed action from the same context. A model that emits only an action
chunk may be useful for another WAMProbe capability tier, but it does not provide
candidate-conditioned future evidence.

The first integration should be intentionally small: one pinned checkpoint, one
configuration, one paired context group, a documented GPU budget, cached
prediction provenance, and an explicit list of unavailable metrics. Expand only
after the semantic smoke test passes.

## P5 — DOI and outreach

Prepare Zenodo metadata and communication material after the stable release so
the DOI points to immutable public artifacts. Outreach should ask for independent
reproductions and comparable structured reports, not only stars or screenshots.

## Maintainer decision rules / 维护规则

- Never mark P0 complete from a maintainer-controlled machine.
- Never release a metric without an anti-gaming or failure-baseline test.
- Never label a proxy as a capability the model does not expose.
- Never commit checkpoints, datasets, credentials, or generated private evidence.
- Prefer small reproducible issues with an explicit acceptance checklist.
