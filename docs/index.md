# WAMProbe

WAMProbe is a counterfactual evaluation toolkit for World Action Models. It asks whether
different candidate actions produce different predicted futures, whether those differences
agree with the real dynamics, and whether the predictions improve action selection.

The same initial state is restored before every branch:

```text
shared context
├── no-op       → predicted future / true future
├── move left   → predicted future / true future
├── move right  → predicted future / true future
└── expert act  → predicted future / true future
```

WAMProbe reports action dependence, direction correctness, physical accuracy, candidate
ranking, regret, closed-loop return, uncertainty, and compute cost as separate profiles.
It intentionally does not publish a single composite score.

## Start here

- Follow the [15-minute quick start](QUICKSTART.md) for dependency-free CPU experiments.
- Connect a model with the tested [custom adapter starter guide](adapters/CUSTOM_ADAPTER.md).
- Read the [scope and capability RFC](rfcs/0001-scope-and-capabilities.md) before adding an adapter.
- Use the [core metric cards](metrics/CORE_METRICS.md) to select capability-compatible metrics.
- Review the [reproducibility guide](reproducibility/REPRODUCIBILITY.md) before comparing results.
- Inspect the [StarWAM model card](models/STARWAM.md) for the first real-model integration.
- Check [Next steps](NEXT_STEPS.md) for milestone dependencies and contribution-sized tasks.

Install the dependency-free core with `pip install wamprobe`. Committed example reports
and audited release artifacts remain available on
[PyPI](https://pypi.org/project/wamprobe/) and in the
[GitHub repository](https://github.com/myheart521/WAMProbe).
