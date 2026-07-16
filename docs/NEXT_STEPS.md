# Next steps / 后续路线图

This roadmap separates completed release engineering from work that still needs new
scientific evidence. Maintainer verification and independent reproduction remain distinct
claims even though independent reproduction is not a `v0.1` release gate.

本路线图区分已经完成的发布工程与仍需新科学证据的工作。维护者验收和独立复现始终是两种
不同声明，但独立复现不再作为 `v0.1` 的发布门槛。

## Dependency path / 依赖关系

```text
P0 maintainer clean install ──► P1 final v0.1.0

optional independent reports ──► additional public evidence

P2 contributor readiness ──► P3 broader paired benchmarks
                         └──► P4 action-conditioned real WAM

P1 stable release + public evidence ──► P5 DOI and outreach
```

## Milestones / 里程碑

| Priority | Milestone | Current state | Completion evidence |
|---|---|---|---|
| P0 | Maintainer clean-install acceptance / 维护者干净环境验收 | **Complete** | Public wheel and PyPI installs, exact commands, exit status, elapsed time, and output hash recorded in Issue #2 |
| P1 | Stable `v0.1.0` / 正式稳定版 | **Complete** | Release audit green, tagged artifacts and provenance available, published-package smoke passed |
| P2 | Contributor readiness / 贡献者接入能力 | **Complete** | Runnable adapter starter, contribution/result forms, roadmap, labeled starter issues, green CI |
| P3 | Broader paired diagnostics / 扩展配对诊断 | **Planned** | More LIBERO initial states plus Occluded-Object memory benchmark with restore/order checks |
| P4 | Real action-conditioned WAM evidence / 真实动作条件 WAM | **Planned; model capability required** | Public model exposes candidate-conditioned futures, adapter passes semantic tests, bounded report is reproducible |
| P5 | Archival and outreach / 归档与传播 | **Ready after v0.1.0** | Zenodo DOI, updated citation metadata, release notes, public result call |

Tracked work:

- P0: [maintainer acceptance record #2](https://github.com/myheart521/WAMProbe/issues/2)
- P3: [LIBERO initial-state coverage #10](https://github.com/myheart521/WAMProbe/issues/10)
  and [Occluded-Object RFC #7](https://github.com/myheart521/WAMProbe/issues/7)
- P4: [public action-conditioned WAM audit #9](https://github.com/myheart521/WAMProbe/issues/9)
- Starter contributions: [adapter troubleshooting #11](https://github.com/myheart521/WAMProbe/issues/11)
  and [malformed-output tests #12](https://github.com/myheart521/WAMProbe/issues/12)
- P5: [Zenodo DOI preparation #8](https://github.com/myheart521/WAMProbe/issues/8)

## P0 — maintainer clean-install acceptance

The maintainer installed the public package in fresh environments, ran the CLI and bounded
demo, and recorded the version, environment, command, elapsed time, and output hash in
Issue #2. This completes the `v0.1` package acceptance chosen by the project owner. It does
not establish independent external reproduction.

维护者已经在全新环境安装公开发行包，运行 CLI 和有界 demo，并在 Issue #2 中记录版本、
环境、命令、耗时和输出哈希。这满足项目所有者为 `v0.1` 选择的包验收口径，但不代表独立
外部复现。

## P1 — stable release gate

The stable release procedure is:

1. confirm the candidate commit is clean and all required CI/security checks pass;
2. run the documented reproducible build and archive audit;
3. update version, changelog, citation, and release notes consistently;
4. publish the final tag and artifacts through the release workflow;
5. verify a clean install from the published package.

P0 is complete. Published-package smoke evidence closes P1.

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
the DOI points to immutable public artifacts. The project may accept optional independent
reproductions and comparable structured reports without treating them as a release gate.

## Maintainer decision rules / 维护规则

- Never describe a maintainer-controlled check as independent reproduction.
- Never release a metric without an anti-gaming or failure-baseline test.
- Never label a proxy as a capability the model does not expose.
- Never commit checkpoints, datasets, credentials, or generated private evidence.
- Prefer small reproducible issues with an explicit acceptance checklist.
