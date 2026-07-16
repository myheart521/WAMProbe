# Connect a custom state-future model

This guide turns a model-specific inference function into WAMProbe's typed
`WAMAdapter` contract. Start from the runnable code in
[`examples/custom_adapter`](https://github.com/myheart521/WAMProbe/tree/main/examples/custom_adapter)
rather than
building the evaluation loop yourself.

## What the starter kit proves

The example deliberately separates model inference from evaluation:

```text
shared Context2D + candidate Action2D
                  │
                  ▼
          PredictionRequest
                  │
                  ▼
      your StateFutureBackend
                  │
                  ▼
validated horizon-length state future
                  │
                  ▼
 WAMProbe metrics and standard report artifacts
```

The included `LinearStateBackend` is only a wiring oracle. It uses the action
delta directly and should achieve zero Top-1 Regret on PointMass2D. It is not a
learned model and its result is not research evidence.

## Run the unchanged example

From a development checkout:

```bash
python -m pip install -e '.[dev]'
python -m examples.custom_adapter.run \
  --output runs/custom-adapter \
  --contexts 8 \
  --seed 7
```

The output directory contains:

```text
runs/custom-adapter/
├── summary.json   # aggregate result, uncertainty, and schema version
├── results.jsonl  # stable context-level records
├── report.md      # reviewable metric table
└── report.html    # standalone human-readable report
```

## Implement the backend boundary

Copy `examples/custom_adapter` into a model-specific module and replace
`LinearStateBackend` with a class implementing this narrow protocol:

```python
class MyBackend:
    def predict_positions(
        self,
        request: PredictionRequest,
    ) -> tuple[tuple[float, float], ...]:
        model_input = preprocess(request)
        prediction = self.model.generate(model_input, seed=request.seed)
        return decode_positions(prediction, horizon=request.horizon)
```

Every request field has evaluation semantics and must be mapped intentionally:

| Field | Meaning | Integration check |
|---|---|---|
| `context_id` | Identity of the shared initial state | Equal across every action branch in a group |
| `action_name` | Stable candidate-action identity | Preserved in the returned trajectory |
| `position_xy` | Current observed state | Never replaced with a post-action state |
| `goal_xy` | Task goal used by the toy scorer | Keep separate from the action input |
| `action_delta_xy` | Counterfactual intervention | Must affect the model input or conditioning path |
| `horizon` | Required number of future states | Return exactly this many states |
| `seed` | Reproduction seed | Forward to every stochastic sampler |

The adapter rejects non-positive horizons, missing or extra time steps, malformed
coordinates, and non-finite values before metrics see them. Keep these checks when
replacing the backend.

## Declare only real capabilities

`ModelCapabilities` controls which evidence can be interpreted. The starter
declares deterministic state futures. If repeated calls with the same seed are
not deterministic, set `deterministic_seed=False`. Set `stochastic=True` when the
model represents a distribution or samples futures. Do not claim pixels,
latents, action scores, or action prediction unless the adapter exposes those
outputs directly.

The current starter targets models that can decode a two-dimensional state
future. Pixel- or latent-only models require a capability-specific adapter and
metrics; do not silently convert an unrelated proxy into a state trajectory.

## Required model-specific tests

Before proposing an adapter, add tests that demonstrate:

1. two different actions from one context reach the model as different inputs;
2. context and action identities survive preprocessing and decoding;
3. the same seed reproduces the same result, or nondeterminism is declared;
4. wrong-length, NaN, and infinite outputs fail loudly;
5. the smallest public checkpoint/configuration completes one bounded smoke run;
6. expected oracle and broken-baseline ordering remains intact.

Run the repository checks listed in
[`CONTRIBUTING.md`](https://github.com/myheart521/WAMProbe/blob/main/CONTRIBUTING.md),
then open an **Adapter proposal** before a large integration. Pin the upstream
repository revision, checkpoint hash, preprocessing version, license, hardware,
and exact smoke command.

## Submit a result responsibly

Use the **Experiment result** issue form and attach or link the standard report
artifacts. A valid result identifies the WAMProbe commit, adapter and upstream
revisions, benchmark configuration, hardware/software environment, exact command,
artifact hashes, and unsupported metrics. Generated evidence must not contain
tokens, private data, browser sessions, local credentials, or model weights.

## 中文速览

这个 Starter Kit 的作用，是把模型自己的推理函数接到 WAMProbe 的类型化评测接口上。
你通常只需要复制 `examples/custom_adapter`，替换 `LinearStateBackend`，并把
`PredictionRequest` 中的上下文、动作、预测长度和随机种子完整传给模型。后端必须返回与
`horizon` 等长的有限二维状态序列；不要丢弃动作条件，也不要把像素或潜变量偷偷换成
不相关的状态代理。提交适配器前，需要固定上游版本、权重哈希、预处理规则、环境和 smoke
命令，并为动作条件、确定性和异常输出补测试。
