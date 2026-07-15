# WAMProbe 开源项目详细规划

> 面向 World Action Model 的因果一致性、动力学可信度与控制价值评测工具箱

| 项目字段 | 内容 |
|---|---|
| 文档版本 | v0.1-draft |
| 更新时间 | 2026-07-15 |
| 推荐许可证 | Apache-2.0 |
| 默认开发规模 | 1–2 人，兼职 10–15 小时/周 |
| 基线周期 | 16 周完成可公开的 v0.1 |
| 主要语言 | Python 3.11+ |
| 首要用户 | WAM 研究者、模型作者、机器人学习评测人员 |

---

## 1. 项目摘要

WAMProbe 的目标不是再做一个通用机器人成功率排行榜，也不是评价生成视频“看起来是否真实”。它要回答一个更具体的问题：

> 当机器人采取不同动作时，World Action Model 是否能预测出正确、可区分、物理上合理的不同未来，并且这些预测是否真的能帮助机器人选择动作？

项目将提供：

1. 一个覆盖不同 WAM 形态的能力声明与适配器协议；
2. 一组以反事实干预为核心的因果和动力学指标；
3. 一个共享初始状态、多动作分支的配对评测数据格式；
4. 从合成环境、离线模拟数据到闭环规划的分层 benchmark；
5. 可复现的命令行工具、缓存、统计分析和 HTML/JSON 报告；
6. StarWAM/FastWAM 等开源模型的参考适配器；
7. 能支撑技术报告或 benchmark paper 的实验设计。

WAMProbe 与现有 VLA 通用评测框架互补：通用框架回答“模型完成任务了吗”，WAMProbe 进一步回答“模型预测的未来是否受动作因果控制，以及这种预测为什么能够或不能够改善控制”。

---

## 2. 背景与问题定义

### 2.1 什么是本项目所说的 WAM

本项目采用宽口径定义：只要模型在训练或推理中联合利用“未来世界变化”和“机器人动作”，即可视为 WAM 家族的一部分。主要包括四类：

1. **Imagine-then-Execute**：先显式生成未来视频/状态，再从未来推导动作；
2. **Feature-Conditioned Action**：不一定生成完整视频，而是用未来预测特征帮助动作头；
3. **Joint Video-Action Modeling**：在共享或交互的 token/latent 空间中联合预测视频与动作；
4. **Auxiliary Future Prediction**：未来预测只作为训练辅助任务，推理时可能仅输出动作。

因此，WAMProbe 不能要求所有模型都实现同一种 `generate_video()` 接口。它需要使用 capability manifest，仅对模型实际具备的能力运行适用指标。

### 2.2 当前评测存在的核心缺口

常见评测主要有两类：

- **任务成功率**：能衡量最终表现，但很难解释世界建模是否真的发挥作用；
- **视频生成指标**：能衡量外观或分布相似度，但未必衡量动作是否控制了未来。

以下失败模式可能被现有指标漏掉：

- 模型生成很真实的视频，但几乎忽略输入 action；
- 左移、右移、闭合夹爪产生几乎相同的未来；
- 预测的机械臂运动与输入动作方向相反；
- 物体在没有接触时自行移动；
- 单步预测准确，但长时 rollout 漂移或前后不一致；
- 世界模型预测准确，却不能正确排序候选动作；
- 模型依赖未来特征，但这种依赖对闭环控制没有收益；
- 高成本未来生成带来的控制提升不足以抵消推理延迟。

### 2.3 核心研究问题

WAMProbe 围绕五个问题组织评测：

| 编号 | 研究问题 |
|---|---|
| RQ1 | 模型是否真的使用 action，而不是仅根据当前画面生成最常见未来？ |
| RQ2 | action 的变化是否导致方向正确、幅度合理的未来变化？ |
| RQ3 | 预测未来是否满足基本的运动学、接触和时间一致性？ |
| RQ4 | 预测未来能否帮助模型正确排序候选动作并改善闭环控制？ |
| RQ5 | 世界建模收益与推理延迟、显存和生成步数之间如何权衡？ |

### 2.4 初始研究假设

- **H1**：有效 WAM 在 action shuffle/mask 后，因果指标应显著下降；若不下降，说明模型可能忽略 action。
- **H2**：传统视频指标与控制收益仅有弱到中等相关，不能替代控制价值指标。
- **H3**：反事实动作排序能力比单纯视频相似度更能预测闭环成功率提升。
- **H4**：模型对未来特征的依赖随任务阶段变化；接近接触和精细操作阶段可能更依赖当前状态。
- **H5**：增加 rollout horizon 或生成 NFE 不会单调提升控制价值，存在性价比最优点。

---

## 3. 项目边界

### 3.1 v0.1 必须完成

- 一个稳定的 Python adapter protocol；
- 一个机器可读 capability manifest；
- 一个共享初始状态、多动作分支的 intervention dataset schema；
- 至少 4 个无需大模型的 reference baselines；
- 至少 1 个真实开源 WAM adapter；
- Tier 0 合成 benchmark 和 Tier 1 配对模拟 benchmark；
- 至少 6 个核心指标，覆盖因果、动力学、控制价值和效率；
- CLI、结构化结果、HTML 报告、置信区间和运行元数据；
- CPU CI 与可选 GPU nightly tests；
- 一份完整的 benchmark card 和复现实验。

### 3.2 暂不纳入 v0.1

- 不训练新的大规模 WAM；
- 不做真实机器人安全认证；
- 不取代通用 VLA task-success harness；
- 不建立未经验证的单一总分排行榜；
- 不把 FVD、PSNR、SSIM 等视频指标当作主要结论；
- 不承诺一开始支持所有 WAM 代码库；
- 不在 v0.1 强制统一所有 action space，而是要求 adapter 显式描述和转换；
- 不把模型的 latent 强行映射为像素视频。

### 3.3 v0.1 的产品原则

1. **Capability-aware**：不同 WAM 只运行适用测试；
2. **Counterfactual-first**：尽量使用相同初始状态下的多动作分支；
3. **Control-grounded**：指标最终要与真实 simulator return/success 建立关系；
4. **Baseline-heavy**：任何指标都必须能击败并区分简单作弊基线；
5. **Reproducible**：配置、代码版本、数据版本、硬件和随机种子全部进入结果；
6. **No silent fallback**：缺失能力或字段必须明确跳过/报错，不能静默使用替代逻辑。

---

## 4. 目标用户与典型使用场景

### 4.1 模型作者

需求：判断新 WAM 是否真的利用未来预测，而不是仅凭强大的当前帧编码器完成动作预测。

```bash
wamprobe run \
  --model configs/models/my_wam.yaml \
  --benchmark configs/benchmarks/libero_cf_mini.yaml \
  --output runs/my_wam
```

### 4.2 Benchmark 维护者

需求：新增一组共享初始状态、多动作分支的数据，并验证它能够区分 oracle、action-aware 和 action-agnostic baseline。

```bash
wamprobe benchmark validate ./benchmarks/my_counterfactual_suite
```

### 4.3 论文复现者/审稿人

需求：用相同模型输出缓存重新计算指标，或者比较两个 checkpoint 的 paired difference。

```bash
wamprobe compare runs/model_a runs/model_b --paired --bootstrap 2000
```

### 4.4 控制/规划研究者

需求：将 WAM 用作 candidate action scorer，检查它能否降低 top-1 regret 并提升 MPC 成功率。

```bash
wamprobe mpc \
  --world-model configs/models/my_wam.yaml \
  --planner configs/planners/cem_small.yaml \
  --env configs/envs/libero_pick.yaml
```

---

## 5. 系统总体设计

### 5.1 分层评测结构

```text
Tier 0：合成因果单测
  └─ 已知动力学、低成本、快速验证指标是否正常

Tier 1：配对反事实模拟数据
  └─ 相同 initial state + 多个 action branch + ground-truth future

Tier 2：闭环候选动作选择/MPC
  └─ 测试世界预测是否真的提升控制收益

Tier 3：真实机器人（v1.0 之后，可选）
  └─ 小规模验证 sim 指标与真实控制的相关性
```

### 5.2 运行流水线

```text
解析配置
  → 校验模型能力与 benchmark 要求
  → 校验 observation/action schema
  → 加载 intervention groups
  → 执行/读取模型预测缓存
  → 运行 capability-gated metrics
  → 按 context/task 聚合
  → bootstrap 置信区间与 paired comparison
  → 输出 JSONL + summary.json + HTML report + model card
```

### 5.3 推荐仓库结构

```text
wamprobe/
├── pyproject.toml
├── README.md
├── LICENSE
├── CITATION.cff
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── src/wamprobe/
│   ├── api/
│   │   ├── model.py             # WAMAdapter Protocol
│   │   ├── types.py             # Observation/Action/FuturePrediction
│   │   ├── capabilities.py      # capability manifest
│   │   └── errors.py
│   ├── adapters/
│   │   ├── baselines/
│   │   │   ├── copy_last.py
│   │   │   ├── action_agnostic.py
│   │   │   ├── linear_dynamics.py
│   │   │   └── oracle_sim.py
│   │   ├── starwam/
│   │   └── fastwam/
│   ├── data/
│   │   ├── schema.py
│   │   ├── intervention_dataset.py
│   │   ├── lerobot_bridge.py
│   │   └── validation.py
│   ├── metrics/
│   │   ├── causal/
│   │   ├── dynamics/
│   │   ├── control/
│   │   ├── uncertainty/
│   │   └── efficiency/
│   ├── benchmarks/
│   │   ├── toy2d/
│   │   └── libero_cf/
│   ├── evaluators/
│   │   ├── offline.py
│   │   ├── counterfactual.py
│   │   └── closed_loop.py
│   ├── stats/
│   │   ├── bootstrap.py
│   │   ├── correlations.py
│   │   └── paired_tests.py
│   ├── cache/
│   ├── reporting/
│   ├── config/
│   └── cli.py
├── configs/
│   ├── models/
│   ├── benchmarks/
│   └── experiments/
├── schemas/
│   ├── capability-v0.1.schema.json
│   ├── intervention-v0.1.schema.json
│   └── result-v0.1.schema.json
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── golden/
│   └── gpu/
├── docs/
│   ├── concepts/
│   ├── metrics/
│   ├── adapters/
│   ├── benchmark-card.md
│   └── reproducibility.md
├── examples/
└── scripts/
```

---

## 6. 模型能力协议

### 6.1 Capability Manifest

示例：

```yaml
schema_version: 0.1
model_id: example/starwam-libero

inputs:
  rgb: true
  proprioception: true
  language: true
  history_frames: 2

outputs:
  action_prediction:
    supported: true
    horizon: 16
  future_prediction:
    supported: true
    representation: pixels   # pixels | states | latents | none
    horizon: 16
    stochastic: true
  action_scoring:
    supported: false
  world_features:
    supported: true

action_space:
  type: ee_delta
  dimensions: 7
  coordinate_frame: robot_base
  translation_unit: meter
  rotation_representation: axis_angle

runtime:
  supports_batching: true
  max_batch_size: 8
  deterministic_seed: true
```

### 6.2 Python Adapter Protocol

建议使用 `typing.Protocol`，而不是要求模型继承重量级基类：

```python
from typing import Protocol

class WAMAdapter(Protocol):
    @property
    def capabilities(self) -> "ModelCapabilities": ...

    def predict_action(
        self,
        context: "ContextBatch",
        *,
        seed: int,
    ) -> "ActionPrediction": ...

    def predict_future(
        self,
        context: "ContextBatch",
        actions: "ActionBatch",
        *,
        seed: int,
    ) -> "FuturePrediction": ...

    def score_actions(
        self,
        context: "ContextBatch",
        actions: "ActionBatch",
        *,
        seed: int,
    ) -> "ActionScores": ...

    def close(self) -> None: ...
```

实现规则：

- 不支持的方法应在 capability 中声明 `false`，调用时抛出明确的 `UnsupportedCapabilityError`；
- adapter 必须返回 action/future 的语义元数据，禁止只返回匿名 tensor；
- adapter 负责模型特有 preprocessing，但必须记录 resolved preprocessing config；
- 所有输出必须带 sample/context ID，避免 batch 重排造成错配；
- 随机生成模型必须接受显式 seed，并报告实际使用的采样参数；
- v0.1 使用进程内 adapter，v0.2 增加隔离依赖的 remote adapter protocol。

### 6.3 Capability 与指标的对应关系

| 能力 | 可运行指标 |
|---|---|
| `future_prediction=pixels` | 动作敏感性、视觉变化方向、no-op 稳定性、感知一致性、视频辅助指标 |
| `future_prediction=states` | 状态 ADE/FDE、运动学一致性、接触/约束一致性 |
| `future_prediction=latents` | latent action dependence、probe-based cycle consistency；不能声称像素真实性 |
| `action_scoring=true` | candidate ranking、top-1 regret、NDCG、MPC utility |
| `action_prediction=true` | action error、chunk continuity、闭环成功率辅助结果 |
| `world_features=true` | feature reliance、action mask/shuffle ablation、任务阶段依赖分析 |

---

## 7. 反事实数据设计

### 7.1 核心数据单元：Intervention Group

普通机器人数据只有实际执行的一条轨迹，无法知道“如果当时执行另一个动作会怎样”。WAMProbe 的关键数据单元是共享初始状态的动作分支：

```text
context_id = 00427
initial simulator state = S0

branch 0: no-op             → future_0, return_0
branch 1: move left         → future_1, return_1
branch 2: move right        → future_2, return_2
branch 3: close gripper     → future_3, return_3
branch 4: expert action     → future_4, return_4
branch 5: perturbed expert  → future_5, return_5
```

只有保持初始状态相同，才能把未来差异归因于动作差异。

### 7.2 数据存储策略

v0.1 不重新发明完整机器人数据格式。建议：

- 图像、状态和动作 episode 使用 LeRobot v3 兼容存储；
- 新增 `interventions.parquet` 描述分支关系；
- 新增 `wamprobe_manifest.json` 描述语义和版本；
- simulator state snapshot 单独存储并记录 hash；
- 视频可以延迟解码，指标优先读取必要帧。

`interventions.parquet` 最少包含：

| 字段 | 含义 |
|---|---|
| `context_id` | 共享初始状态 ID |
| `branch_id` | 该 context 下的动作分支 ID |
| `episode_index` | 对应底层 episode |
| `start_frame` | 干预开始帧 |
| `horizon` | 未来长度 |
| `action_family` | no-op/expert/random/perturbed/directional |
| `action_spec_id` | 动作语义规范 ID |
| `return` | simulator ground-truth return |
| `success` | 是否成功 |
| `termination_reason` | 成功、碰撞、超时等 |
| `state_snapshot_hash` | 初始 simulator state 的校验值 |

### 7.3 动作分支生成策略

每个 context 默认产生 4–6 个分支：

1. `no_op`：检测无动作情况下的虚假运动；
2. `expert`：专家/数据动作；
3. `reverse`：关键平移或关节动作取反；
4. `scaled`：动作幅度乘 0.5 或 1.5；
5. `orthogonal`：在允许空间内构造正交方向；
6. `random_valid`：满足约束但任务上不一定合理的动作。

动作生成必须经过约束投影，避免用明显非法动作让指标变得过于简单。

### 7.4 数据切分

- **ID split**：训练/适配时出现过的物体、场景、语言模板；
- **OOD-object**：新物体外观或类别；
- **OOD-layout**：新初始位置和遮挡；
- **OOD-action-scale**：训练范围边界附近的动作幅度；
- **OOD-language**：语义相同但不同表述；
- **long-horizon**：预测长度超过常规训练 horizon。

同一个 `context_id` 的所有 branch 必须位于同一 split，防止反事实分支泄漏。

---

## 8. Benchmark 设计

### 8.1 Tier 0：WAMProbe-Toy

目标：用可解释、已知动力学、低成本环境验证指标本身。

建议包含四个任务：

1. **PointMass-2D**：动作直接控制二维位移；
2. **BlockPush-2D**：包含接触前后两个动力学阶段；
3. **Gripper-Catch**：检测夹爪语义、接触和物体附着；
4. **Occluded-Object**：测试世界状态记忆与未来变化，不只依赖当前像素。

每个任务提供：

- 状态和 RGB 两种观察；
- 确定性和带噪声两种动力学；
- ground-truth transition function；
- oracle world model；
- action-agnostic、copy-last 和错误方向模型；
- 1000 个 intervention groups 的小型公开数据。

验收重点：每个核心指标必须按预期排序：

```text
oracle > noisy action-aware > action-agnostic > wrong-direction/copy-last
```

如果指标不能稳定得到这个顺序，不允许进入 Tier 1 主报告。

### 8.2 Tier 1：LIBERO-CF-Mini

目标：在更接近真实机器人视觉的模拟环境中创建配对反事实数据。

建议 v0.1 只选 3–5 个任务，覆盖：

- 到达/空间移动；
- 抓取；
- 推动物体；
- 放置；
- 简单的两阶段任务。

初始规模：

- 200 个 context；
- 每个 context 4 个 action branches；
- 每个 branch 8–16 个未来帧；
- 固定 2 个相机视角；
- 同时保存 simulator state 和渲染视频；
- pilot 版本控制在可下载、可本地快速验证的规模。

注意事项：

- 固定 MuJoCo/LIBERO 版本和资产 hash；
- 明确 seen/unseen instruction 设置；
- 相同 context 的 branch 必须从完全一致的 simulator snapshot 恢复；
- 记录渲染 FPS、控制 FPS 和 action repeat；
- 对每个任务写 benchmark card，说明哪些物理属性可以可靠评测。

2026-07-15 pilot 进展：已在固定 `libero_spatial` task 0/context 上生成 4 个分支、
每分支 8 步和 2 个相机视角。恢复契约采用 MuJoCo `mjSTATE_INTEGRATION`，并额外恢复
robosuite 时钟、controller、observable、Python/NumPy RNG 与 Panda gripper 的
`current_action`。两次 restore、重复 no-op、正序/逆序执行均达到逐状态完全一致，
最大状态误差为 0。该 pilot 的诊断动作 return/success 均为 0，因此只证明配对数据
生成和分支分离，不是 LIBERO 策略成功率结果。

### 8.3 Tier 2：Closed-Loop Utility

目标：验证离线指标是否与控制收益相关。

最小闭环设置：

1. planner 产生 K 个合法 candidate action chunks；
2. WAM 直接评分，或预测 future 后由固定 reward/success scorer 评分；
3. 执行 top-1 chunk 的前 n 步；
4. 重新观察并规划；
5. 与不使用 WAM 的 planner、随机 scorer、oracle scorer 比较。

核心对照：

- random candidate selection；
- behavior policy 直接输出；
- action-only value/reward model；
- WAM-based scorer；
- simulator oracle scorer（上界）。

首版只需要回答：

> 离线 counterfactual ranking 更好的模型，是否也能在相同 candidate set 下获得更高 return？

---

## 9. 指标体系

### 9.1 指标设计规则

- v0.1 不发布单一综合总分；
- 每项指标必须说明“越高越好/越低越好”、适用能力和失败模式；
- 所有 learned metric 必须固定版本、权重和训练数据；
- 先报告 context-level score，再聚合到 task/model；
- paired intervention 不按帧当作独立样本，避免虚假的超窄置信区间；
- 除均值外报告中位数、分位数和 bootstrap 95% CI；
- stochastic WAM 至少运行 3 个生成 seed，区分 epistemic/采样方差与 context 方差。

### 9.2 Causal / Action Grounding 指标

#### M1. Action Dependence Score（ADS）

目的：判断在固定 context 下，预测未来是否随 action 系统性变化。

流程：

1. 对同一 context 输入 K 个动作分支；
2. 将预测 future 映射到固定特征 `phi(future)`；
3. 计算 action distance matrix 与 future-change distance matrix 的相关/依赖程度；
4. 使用 context 内 action permutation 构造零假设分布；
5. 报告相对 permutation baseline 的标准化 effect size。

防作弊：仅产生随机视觉噪声也会增加 future difference，因此 ADS 必须与方向正确性和 ground-truth alignment 联合报告。

#### M2. Counterfactual Direction Accuracy（CDA）

目的：动作变化导致的预测变化方向是否与 ground truth 一致。

可在状态、光流、关键点或对象轨迹空间计算：

```text
cosine(predicted_delta_i - predicted_delta_j,
       true_delta_i - true_delta_j)
```

报告 cosine mean、方向正确率和按动作幅度分桶结果。

#### M3. Action-Future Cycle Consistency（AFCC）

目的：从“当前观察 + 预测未来”能否反推出输入动作。

使用一个固定、独立、只在 ground-truth transition 上训练的 inverse probe，避免模型与自己的 action head 自洽却与真实世界不一致。

报告：

- continuous action reconstruction error；
- action family classification accuracy；
- predicted future 与 ground-truth future 上的 probe gap。

#### M4. Action Shuffle Drop（ASD）

目的：通过消融直接测量 action 信息的贡献。

对 context 保持不变，随机打乱 action，比较 causal/grounding 指标下降幅度。下降过小意味着模型可能忽略 action；但下降越大不一定越好，必须结合真实准确性。

### 9.3 Dynamics / Physical Consistency 指标

#### M5. No-Op Stability（NOS）

在 no-op 分支中测量：

- 背景/静态物体漂移；
- 机械臂无指令移动；
- latent/state drift；
- stochastic prediction 的合理变化范围。

这是检测“模型不管 action 都生成常见成功轨迹”的重要负例。

#### M6. State ADE/FDE

若模型输出状态或可以通过固定视觉跟踪器提取状态，计算 average/final displacement error。必须按对象、机械臂末端和夹爪分别报告，不能只给整体平均。

#### M7. Kinematic Consistency（KC）

将 action chunk 通过已知运动学/控制语义积分，得到预期末端或关节轨迹，与预测 future 中的机器人轨迹比较。

检查：

- 方向和幅度；
- 速度/加速度边界；
- 关节极限；
- chunk 内时间连续性；
- 预测机器人和真实 action 的时延。

#### M8. Contact Plausibility（CP）

仅在 simulator state 或可靠对象跟踪可用时运行：

- 无接触情况下物体是否突然移动；
- 抓取后物体与夹爪是否保持合理相对位姿；
- 穿透、瞬移或不合理速度；
- 接触事件时间是否与 ground truth 接近。

#### M9. Horizon Prefix Consistency（HPC）

使用相同 context/action 分别预测短 horizon 和长 horizon，比较长预测前缀与短预测。对于随机模型使用相同 seed/noise schedule 能对齐的部分；不能对齐时报告分布距离而不是逐像素误差。

### 9.4 Control Utility 指标

#### M10. Candidate Ranking Correlation（CRC）

对每个 context 的 K 个候选动作，用 simulator return 作为 ground truth，计算：

- Spearman correlation；
- Kendall tau；
- NDCG@K；
- pairwise preference accuracy。

#### M11. Top-1 Regret

```text
regret = max(true_return_of_candidates)
         - true_return_of_model_selected_candidate
```

同时报告 normalized regret，避免不同任务 return scale 不同。

#### M12. Closed-Loop Utility Gain（CLUG）

在固定 candidate generator 和执行预算下：

```text
CLUG = return(WAM scorer) - return(reference scorer)
```

reference 至少包括 random、action-only 和 behavior policy。

### 9.5 Uncertainty 与效率指标

#### M13. Counterfactual Calibration

若模型能产生多个样本或显式不确定性，检查预测方差是否与真实 future error、ranking error 对齐。报告 ECE、NLL（适用时）和 risk-coverage curve。

#### M14. Budgeted Control Utility

同时记录：

- 首次推理延迟和稳态延迟；
- 每秒 context/action branches；
- peak GPU memory；
- NFE/生成步数；
- 输入/输出 horizon；
- 每次成功决策的估算计算成本。

报告 utility-latency Pareto frontier，而不是只报告最快或最高分。

### 9.6 视频指标的地位

LPIPS、DINO feature distance、FVD、PSNR、SSIM 可以作为辅助诊断，但必须满足：

- 不进入 v0.1 主排名；
- 与 causal/control metrics 分栏展示；
- 明确说明对 stochastic future 的限制；
- 研究其与 candidate ranking/closed-loop return 的相关性。

---

## 10. Reference Baselines

v0.1 必须先实现无需外部大模型的 baseline，用于验证指标：

| Baseline | 用途 | 预期表现 |
|---|---|---|
| `CopyLastFrame` | 完全不预测变化 | NOS 高，但 action dependence/方向性低 |
| `ActionAgnosticReplay` | 根据 context 生成常见未来但忽略 action | 视频可能合理，ASD/CDA/CRC 低 |
| `WrongDirectionDynamics` | 故意把动作方向取反 | ADS 可能高，但 CDA/KC 很低 |
| `NoisyLinearDynamics` | 使用 action，但加入可控噪声 | 随噪声增加平滑退化 |
| `OracleSimulator` | simulator 真实 rollout | 大多数指标上界 |
| `RandomActionScorer` | 候选动作随机排序 | ranking/utility 下界 |

每个新指标必须通过 baseline monotonicity test。例如，逐步增加 `NoisyLinearDynamics` 噪声时，核心准确性指标应总体单调下降。

---

## 11. 模型适配计划

### 11.1 首个真实 Adapter 的选择标准

- 开源许可证清晰；
- 有可下载 checkpoint；
- 可以运行 future/action 相关输出；
- 安装过程可锁定；
- 单个评测样本的算力成本可接受；
- 最好已支持 LIBERO 或 LeRobot 数据。

### 11.2 推荐顺序

1. **StarWAM adapter**：代码以模块化 WAM 家族为目标，适合验证 capability protocol；
2. **FastWAM adapter**：用于 action-only/联合变体和效率评测，但要根据公开 checkpoint 实际能力启用指标；
3. **其他 WAM**：待 v0.1 协议稳定后通过独立 extras/plugin 添加。

截至 2026-07-15 的代码、checkpoint、许可证与环境审计已完成。第一实现目标保留为
StarWAM，LingBot-VA 调整为第二个论文对照，Fast-WAM 在权重许可证元数据明确前只作为
action-only/效率设计参考。版本 pin、风险和第一实现切片见
[`docs/research/ADAPTER_SELECTION.md`](research/ADAPTER_SELECTION.md)。

### 11.3 依赖隔离

v0.1：

- adapter 使用 optional dependencies，例如 `pip install wamprobe[starwam]`；
- 核心包不依赖 CUDA、MuJoCo 或具体生成模型；
- GPU integration test 允许按 label/nightly 执行；
- adapter 锁定已验证的上游 commit/tag。

v0.2：

- 增加 remote model server；
- 核心 runner 与模型环境通过 msgpack/HTTP 或 WebSocket 通信；
- 每个 adapter 可拥有独立容器或 `uv` environment；
- prediction cache 与指标计算完全解耦。

---

## 12. 配置、缓存与结果格式

### 12.1 实验配置

推荐使用 YAML + Pydantic，避免 v0.1 引入复杂配置框架。

```yaml
experiment:
  name: starwam_libero_cf_pilot
  seeds: [0, 1, 2]

model:
  adapter: starwam
  checkpoint: model-id-or-path
  dtype: bfloat16
  batch_size: 4

benchmark:
  id: libero-cf-mini-v0.1
  split: id_test
  max_contexts: 100

metrics:
  - action_dependence
  - counterfactual_direction
  - no_op_stability
  - state_ade_fde
  - candidate_ranking
  - efficiency

cache:
  predictions: true
  key_fields:
    - model_checkpoint_hash
    - adapter_version
    - benchmark_hash
    - resolved_preprocessing
    - seed
```

### 12.2 输出目录

```text
runs/starwam_libero_cf_pilot/
├── resolved_config.yaml
├── run_metadata.json
├── capabilities.json
├── predictions/
├── per_branch.jsonl
├── per_context.jsonl
├── summary.json
├── comparisons.json
├── report.html
├── environment.txt
└── logs/
```

### 12.3 结果元数据

至少记录：

- WAMProbe 版本和 git SHA；
- model adapter 版本和上游 commit；
- checkpoint ID/hash；
- benchmark/data hash；
- resolved config；
- Python、PyTorch、CUDA、driver、GPU；
- random seeds；
- preprocessing/normalization；
- 是否确定性运行；
- 失败、超时、OOM 和跳过样本数量；
- 每个 metric 的版本。

---

## 13. 统计与实验规范

### 13.1 聚合层级

正确层级：

```text
frame → branch → context → task → suite → model
```

统计检验和 bootstrap 主要在 `context` 或 `task seed` 层进行，不能把相邻视频帧当作独立样本。

### 13.2 默认报告

- mean、median、标准差；
- 5/25/75/95 分位数；
- context-block bootstrap 95% CI；
- paired model difference 和 CI；
- effect size；
- 有效样本数、失败率和跳过原因；
- task-wise 与 aggregate 两套结果。

### 13.3 相关性验证

项目早期最重要的不是模型排名，而是证明指标有效。需要验证：

1. 指标能否区分 reference baselines；
2. action shuffle/mask 是否导致预期下降；
3. 指标是否随可控噪声单调退化；
4. 离线 ranking 指标是否与 simulator return 相关；
5. causal metric 是否能解释相同视频质量下的控制差异；
6. 指标对 feature extractor、horizon 和相机视角是否稳健。

### 13.4 多重比较

当比较多个模型、任务和指标时：

- 主假设在实验前写入 config/report；
- 次要探索结果明确标注 exploratory；
- 需要显著性判断时使用 Benjamini–Hochberg 控制 FDR；
- 不因某一个 seed 或任务的异常结果下结论。

---

## 14. 实验矩阵与算力预算

### 14.1 Pilot 实验

建议先运行：

```text
100 contexts
× 4 action branches
× 3 generation seeds
× 8 future frames
= 1,200 branch predictions
```

先验证指标、缓存、统计和报告，不追求论文级规模。

### 14.2 Full v0.1 实验

```text
200–500 contexts
× 4–6 branches
× 3 seeds
× 8–16 future frames
× 1–2 real WAMs
```

实际成本高度依赖模型。必须在 pilot 后根据单 branch latency 制定硬预算，默认总 GPU 时间上限而不是无限扩展样本。

### 14.3 硬件分层

| 开发内容 | 最低要求 |
|---|---|
| 核心 API、schema、Toy benchmark、报告 | CPU 即可 |
| 小型 learned probe/视觉特征 | 8–16 GB GPU 可选 |
| StarWAM/FastWAM 等真实 WAM | 以对应模型为准，可能需要 48–80 GB 或多 GPU |
| CI | CPU；GPU 测试 nightly/手动触发 |

项目必须保证没有大 GPU 的贡献者也能开发核心包和运行 Toy benchmark。

---

## 15. CLI 设计

```bash
# 查看可用模型、benchmark 和指标
wamprobe list models
wamprobe list benchmarks
wamprobe list metrics

# 检查能力与配置兼容性，不运行推理
wamprobe doctor --model model.yaml --benchmark benchmark.yaml

# 生成/校验反事实数据
wamprobe benchmark build --config libero_cf_build.yaml
wamprobe benchmark validate ./data/libero_cf_mini

# 执行评测
wamprobe run --config experiments/starwam_pilot.yaml

# 只从缓存重算指标
wamprobe score --predictions runs/pilot/predictions --metrics metrics.yaml

# 比较模型
wamprobe compare runs/model_a runs/model_b --paired --bootstrap 2000

# 生成报告
wamprobe report runs/model_a --format html
```

CLI 验收要求：

- `--help` 能说明输入、输出和示例；
- 所有失败使用稳定 exit code；
- `doctor` 在下载 checkpoint 前就能发现能力不匹配；
- 支持 `--max-contexts` 和 smoke test；
- 中断后可以基于内容寻址缓存恢复；
- OOM/timeout 记录为结构化失败，不吞掉整个实验。

---

## 16. 测试与 CI

### 16.1 测试分层

1. **Unit tests**：schema、metric 数学、统计和缓存；
2. **Property tests**：动作 permutation、batch reorder、seed 和 shape 不变量；
3. **Golden tests**：固定小数据的 per-context/summary 输出；
4. **Baseline ordering tests**：确保 oracle/错误 baseline 排序合理；
5. **Integration tests**：Toy benchmark 端到端 CLI；
6. **GPU adapter tests**：小样本 nightly；
7. **Schema compatibility tests**：旧 result/manifest 可被新版本读取或明确拒绝。

### 16.2 质量门槛

- Ruff format/lint；
- mypy 或 Pyright strict for core API；
- pytest；
- 核心模块 coverage ≥ 85%；
- markdown link check；
- JSON Schema validation；
- package build/install smoke test；
- Linux 为首要平台，Windows/macOS 核心包 best effort；
- release 使用 PyPI trusted publishing 和签名/校验信息。

---

## 17. 16 周实施计划

### Phase 0：问题收敛（第 1–2 周）

当前进度（2026-07-15）：15 个文献失败模式和首个 Adapter 审计已经完成，见
[`docs/research/WAM_VLA_FAILURE_CASES.md`](research/WAM_VLA_FAILURE_CASES.md) 与
[`docs/research/ADAPTER_SELECTION.md`](research/ADAPTER_SELECTION.md)。外部研究者 README
理解度检查仍需人工完成。

任务：

- 阅读并整理 10–15 个 WAM/VLA 评测失败案例；
- 明确四类 WAM capability taxonomy；
- 写出 metric design RFC；
- 确认首个真实模型 adapter 和可用 checkpoint；
- 建立仓库治理文件、CI 骨架和文档站。

交付物：

- `docs/rfcs/0001-scope-and-capabilities.md`；
- `docs/rfcs/0002-counterfactual-metrics.md`；
- capability schema 草案；
- Toy benchmark 设计稿。

退出条件：

- 至少一个外部研究者能根据文档解释 WAMProbe 与普通视频/VLA 评测的区别；
- 首个 adapter 的模型能力和许可证已经核实。

### Phase 1：核心 API 与数据格式（第 3–4 周）

完成状态（2026-07-15）：typed API、capability/result/intervention schema、doctor、dummy
adapters 以及通用 intervention JSONL loader 已落地。Prediction cache 以完整输入和配置生成
内容地址，使用原子写入与 payload SHA256 校验；相同 demo 可从 5/5 缓存结果恢复，损坏条目
会明确失败而不会静默重算。`dataset-export`、`dataset-validate`、`report` 和 `compare` CLI
均已通过端到端测试。

任务：

- 完成 typed data classes 和 `WAMAdapter`；
- capability/result/intervention schemas；
- config 解析、registry、错误体系；
- prediction cache 最小实现；
- dummy adapters。

交付物：

- `wamprobe doctor`；
- `CopyLastFrame`、`WrongDirectionDynamics`；
- schema golden fixtures；
- API 文档。

退出条件：

- 所有核心测试 CPU CI 通过；
- 不支持的 capability 不会静默执行。

### Phase 2：Toy Benchmark 与核心指标（第 5–7 周）

完成状态（2026-07-15）：Phase 2 约定范围已经落地。PointMass-2D、带显式接触阶段的
BlockPush-2D、带闭合/附着语义的 Gripper-Catch 均可在 CPU 运行；后两者提供确定性/带噪声
状态 rollout 与 dependency-free RGB 观察。ADS permutation null、CDA、NOS、ADE/FDE、
四视角 CRC、Top-1 Regret 均先在 context 层计算，再做 context-block bootstrap 和严格
context-ID 对齐的 paired comparison；三个 benchmark 都能生成 JSON、Markdown 和 HTML。
8.1 节更广义 Toy tier 中的 Occluded-Object 仍是后续扩展，不属于 #10/Phase 2 退出条件。

任务：

- 实现 PointMass、BlockPush、Gripper-Catch；
- 生成 intervention groups；
- 实现 ADS、CDA、NOS、ADE/FDE、CRC、Top-1 Regret；
- context-level bootstrap；
- JSON/HTML 初版报告。

退出条件：

- reference baseline ordering 稳定；
- action shuffle/noise 消融符合预期；
- CPU smoke test 在 5 分钟内完成。

### Phase 3：LIBERO-CF-Mini（第 8–10 周）

当前进度（2026-07-15）：已固定 spatial/object/goal/long-horizon 四类任务的 BDDL、
init-state 与上游 commit，批量生成 4 task × 4 branch × 8 step 的真实模拟器数据。每个任务
均通过两次独立 restore、重复 no-op 与正反 branch order 检查，最大 integration-state 误差
为 `0.0`；第二次整套运行在校验 JSON、snapshot、sidecar 和全部 PNG 后得到 4/4 cache hit。
任务选择、MIT 许可证、完整 hash、零稀疏回报和适用边界见
[`docs/benchmarks/LIBERO_CF_MINI.md`](benchmarks/LIBERO_CF_MINI.md)。扩大 init-state 数量、
接入真实 WAM 预测与外部全新环境复现仍属于后续工作。

任务：

- simulator snapshot/restore；
- 合法 action branch generator；
- 选择 3–5 个任务；
- 生成 pilot 数据和 benchmark card；
- 接入关键点/状态提取；
- 数据校验和许可证说明。

退出条件：

- 每个 context 的 branch 初始状态 hash 一致；
- 数据可从全新环境复现至少一个小子集；
- oracle 与错误 baseline 在主要指标上明显可分。

### Phase 4：真实 WAM Adapter（第 11–13 周）

当前进度（2026-07-15）：StarWAM matrix runner 已在一次模型加载中完成 4 task × 3 seed ×
3 NFE 共 36 次真实推理，第二次运行得到 36/36 output-SHA-verified cache hit；随后从配对
snapshot 执行全部动作块，并在 horizon 8/16/32 记录状态、回报和成功。预测与执行失败率
均为 0，NFE 1/4/8 平均延迟为 0.780/0.972/1.216 秒，峰值约 11.39 GiB。所有短 horizon
稀疏成功均为 0，EEF 平均位移随 horizon 为 0.1716/0.1121/0.0000，保留为“更长 rollout
不单调改善控制”的负结果。候选 action mask/shuffle 因已验证 adapter 不接受候选 action
输入而结构化跳过。模型卡、实验报告和 opt-in self-hosted GPU nightly 已补齐。

任务：

- 完成 StarWAM 或其他首选 adapter；
- 锁定依赖和 checkpoint；
- 完成 pilot 推理缓存；
- 运行 action mask/shuffle、horizon、NFE 消融；
- 评估指标稳定性和计算预算。

退出条件：

- 一条公开命令可以重现实验；
- 至少 95% pilot 样本成功产生结构化结果；
- 失败样本和跳过原因全部进入报告。

### Phase 5：控制价值与 v0.1 发布（第 14–16 周）

当前进度（2026-07-15）：已在 BlockPush-2D 与 Gripper-Catch 上运行 12-context 的传统
视频指标/控制价值反例研究。`appearance-corrupted-oracle` 保持 FDE=0、CRC=1、Regret=0，
但 PSNR 约 0.59 dB；PSNR 与 regret 的跨 profile Pearson 约为 -0.16，且两个 benchmark
分别出现 3/9 和 5/9 个可比较排序冲突。最小 score-execute-observe 闭环也已落地：每次
只执行 1 步并重规划，oracle future scorer 两任务 success 均为 1，noisy future scorer
分别为 1.0/0.9167，三个 action-ignorance/wrong-direction 对照均为 0；离线 CRC 与闭环
return 的 5-profile 描述性 Pearson 分别为 0.9855/1.0。全部结果、context-block CI 和限制
见 [`examples/video-control-study/`](../examples/video-control-study/video-control-study.md)
与 [`docs/experiments/TOY_CLOSED_LOOP_V0.1.md`](experiments/TOY_CLOSED_LOOP_V0.1.md)。
release artifact 追溯、技术报告和外部复现仍待完成。

任务：

- candidate ranking 和最小 closed-loop utility；
- 离线指标与 return/success 的相关分析；
- 完整 README、教程、benchmark/model card；
- PyPI 发布、GitHub Release、演示报告；
- 技术报告初稿和上游 adapter/集成 PR。

v0.1 发布门槛：

- 1 个真实 WAM + 4 个 reference baselines；
- 2 个 benchmark tiers；
- 6 个以上核心指标；
- 端到端复现脚本；
- 结构化报告与统计置信区间；
- 一个外部用户成功复现 smoke test。

---

## 18. 首批 GitHub Issues

| Issue | 标题 | 优先级 | 估时 | 依赖 |
|---|---|---:|---:|---|
| #1 | RFC: WAM capability taxonomy and non-goals | P0 | 2 天 | 无 |
| #2 | Define `WAMAdapter` Protocol and core typed outputs | P0 | 3 天 | #1 |
| #3 | Add capability v0.1 JSON Schema | P0 | 2 天 | #1 |
| #4 | Define intervention-group dataset schema | P0 | 3 天 | #1 |
| #5 | Implement config loader and compatibility doctor | P0 | 3 天 | #2–#4 |
| #6 | Implement content-addressed prediction cache | P1 | 3 天 | #2 |
| #7 | Add CopyLastFrame and ActionAgnostic baselines | P0 | 2 天 | #2 |
| #8 | Add WrongDirection and NoisyLinear baselines | P0 | 2 天 | #2 |
| #9 | Build PointMass-2D intervention benchmark | P0 | 3 天 | #4 |
| #10 | Build BlockPush/Gripper-Catch benchmark | P1 | 5 天 | #9 |
| #11 | Implement Action Dependence Score + permutation null | P0 | 4 天 | #9 |
| #12 | Implement Counterfactual Direction Accuracy | P0 | 3 天 | #9 |
| #13 | Implement No-Op Stability and state ADE/FDE | P0 | 3 天 | #9 |
| #14 | Implement candidate ranking and top-1 regret | P0 | 3 天 | #9 |
| #15 | Add context-block bootstrap and paired comparison | P0 | 4 天 | #11–#14 |
| #16 | Generate JSON and HTML report | P1 | 4 天 | #15 |
| #17 | Build LIBERO snapshot/branch prototype | P0 | 5 天 | #4 |
| #18 | Add first real WAM adapter | P0 | 7–10 天 | #2、#5 |
| #19 | Add GPU nightly smoke workflow | P1 | 2 天 | #18 |
| #20 | Write benchmark card and v0.1 reproducibility guide | P0 | 4 天 | 全部 |

代码落地状态（2026-07-15）：已补齐并验证 #6、#8、#10、#11、#13、#15、#16、#19
以及 CRC；
此前已完成 #1–#5、#7、#9、#12、#14、#17 的当前 v0.1 切片。#18 已有可运行的 StarWAM
prediction artifact/adapter 切片，但真实 WAM 反事实控制评测仍需继续扩展。

建议 labels：

```text
area:api
area:adapter
area:benchmark
area:metric
area:reporting
area:stats
good-first-issue
needs-rfc
needs-gpu
priority:p0
priority:p1
```

---

## 19. 风险登记表

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---:|---:|---|
| 不同 WAM 形态差异过大 | 高 | 高 | capability manifest；按能力分组，不强制单一接口输出 |
| 指标被随机视觉变化“刷高” | 高 | 高 | 联合 ADS、方向性、ground truth alignment；加入噪声作弊基线 |
| 反事实数据生成成本高 | 中 | 高 | 先 Toy/mini；保存 simulator snapshot；限制 branch/horizon |
| 视频指标与控制无关 | 高 | 中 | 不设为主分；重点验证与 return 的相关性 |
| 真实 checkpoint/代码不可用 | 中 | 高 | Phase 0 核实；首版只承诺一个真实 adapter；保留 baseline 完整路径 |
| 模型依赖冲突严重 | 高 | 中 | optional extras、锁定 commit；v0.2 remote adapter |
| stochastic WAM 结果不稳定 | 高 | 中 | 多 seed、分层方差、风险覆盖曲线和缓存 |
| LIBERO 版本导致结果漂移 | 中 | 高 | 固定镜像/commit、资产 hash、benchmark card |
| 单一总分误导用户 | 中 | 高 | v0.1 禁止综合分，使用 metric profile 和 Pareto 图 |
| 算力不足拖慢开发 | 中 | 中 | CPU-first 核心；prediction cache；pilot 后设置 GPU 小时上限 |
| 指标与闭环成功率不相关 | 中 | 高 | 这是需要公开报告的研究结果；调整指标但不隐藏负结果 |
| 项目范围膨胀 | 高 | 高 | 以 v0.1 发布门槛为准；真实机器人、全模型支持延后 |

---

## 20. 开源治理与社区策略

### 20.1 仓库基础设施

首日建立：

- Apache-2.0 `LICENSE`；
- `CONTRIBUTING.md`；
- `CODE_OF_CONDUCT.md`；
- `SECURITY.md`；
- `CITATION.cff`；
- bug/benchmark/adapter issue templates；
- PR template，要求附 smoke test 和结果变化；
- GitHub Discussions：Ideas、Adapters、Benchmarks、Reproductions；
- 公开 roadmap 和 RFC 流程。

### 20.2 贡献边界

- 新指标必须提交 metric card、适用能力、reference baseline 测试和失败案例；
- 新 adapter 必须锁定上游版本并提供最小 smoke config；
- 新 benchmark 必须提交数据许可证、split 规则、生成代码和 benchmark card；
- 排行结果必须可追溯到 config、checkpoint hash 和结构化原始输出；
- 不接受只给截图、无法复现的排行榜提交。

### 20.3 采用策略

1. 首先发布一个能在 CPU 运行的漂亮 Toy demo；
2. 用真实 WAM 展示“视频看起来相似但 causal/control 指标不同”的案例；
3. 向 StarWAM/FastWAM/LeRobot 或通用评测框架提交 adapter/链接 PR；
4. 提供 Colab 或最小容器，但不让 notebook 成为唯一入口；
5. 每个 release 发布一份固定的 reproduction report；
6. 优先吸引外部 benchmark/model adapter，而不是自己维护所有模型。

---

## 21. 技术报告/论文规划

### 21.1 可能的论文主张

谨慎的主张应是：

> 我们提出一个 capability-aware、counterfactual-first 的 WAM 评测框架，并证明常见视频指标不足以识别 action grounding 与控制价值差异；所提出的反事实指标能区分明确的失败基线，并与候选动作排序或闭环收益建立更强联系。

不要在早期声称“首次”“全面”或“统一所有 WAM”，除非系统检索和实验确实支持。

### 21.2 必要实验

- reference baseline sanity checks；
- 至少一个真实 WAM；最好两个不同范式 WAM；
- action mask/shuffle 消融；
- horizon/NFE/未来表示消融；
- ID/OOD 对比；
- traditional video metrics 与 causal/control metrics 相关性；
- offline ranking 与 closed-loop return 相关性；
- feature extractor 和 metric 选择敏感性；
- 计算成本/控制收益 Pareto 分析。

### 21.3 推荐图表

1. WAM capability taxonomy 与评测路由图；
2. 共享初始状态、多 action branch 的 intervention 示意图；
3. baseline sanity ranking；
4. 视频质量与 control utility 的散点相关图；
5. action shuffle 前后指标变化；
6. utility-latency Pareto frontier；
7. 典型失败案例的多分支未来可视化。

### 21.4 负结果政策

如果某个因果指标与闭环收益无相关性，应保留并分析，而不是从最终报告中删除。WAMProbe 的可信度取决于它能否揭示指标限制，而不只是制造新的排行榜。

---

## 22. v0.1 验收清单

### 功能

- [ ] `pip install wamprobe` 可以安装核心包；
- [x] `wamprobe doctor` 能检查 capability/benchmark 兼容性；
- [x] Toy benchmark 可在 CPU 完整运行；
- [x] 至少 4 个 reference baselines；
- [x] 至少 1 个真实 WAM adapter；
- [x] 至少 6 个核心指标；
- [x] prediction cache 可恢复中断运行；
- [x] JSONL/JSON/HTML 输出齐全；
- [x] paired comparison 和 bootstrap CI 可用。

### 研究有效性

- [x] oracle 与错误 baseline 能被稳定区分；
- [x] action shuffle/permutation 产生预期指标下降；
- [x] 噪声增加时准确性指标总体退化；
- [x] 至少一个 causal/ranking 指标与 simulator return 相关；
- [x] 报告传统视频指标与控制指标的差异；
- [x] 公开所有主要失败率和 skipped metrics。

### 工程质量

- [x] 核心 coverage ≥ 85%；
- [x] schema 有版本和兼容策略；
- [ ] 所有 release artifact 可追溯；
- [x] README 15 分钟 quickstart 可执行；
- [x] benchmark/model/metric cards 完整；
- [ ] 至少一个外部用户复现 smoke test。

---

## 23. 立即开始时的第一周任务

如果现在启动项目，第一周只做以下事情：

1. 创建仓库骨架和 Apache-2.0 许可证；
2. 写一页 README，清楚展示“三个动作却预测同一个未来”的失败示例；
3. 提交 capability taxonomy RFC；
4. 定义 `ContextBatch`、`ActionBatch`、`FuturePrediction`；
5. 实现 `CopyLastFrame` 和 `WrongDirectionDynamics`；
6. 实现 PointMass-2D 的 20 个 intervention groups；
7. 只做两个指标：CDA 和 Top-1 Regret；
8. 生成第一份 HTML/Markdown 示例报告；
9. 找一位 WAM/VLA 研究者看 README，确认其能理解项目价值；
10. 根据反馈再决定首个真实 adapter，不提前扩展范围。

第一周的成功标准不是代码量，而是任何访问仓库的人能在 5 分钟内看到：

```text
一个模型可以拥有不错的视频相似度，
同时完全不理解“向左”和“向右”会造成不同未来；
WAMProbe 能稳定检测出这个问题。
```

---

## 24. 参考项目与资料

以下资料用于理解现有生态和确定 WAMProbe 的差异化定位：

- [From World Models to World Action Models: A Concise Tutorial for Robotics](https://arxiv.org/abs/2607.00836)
- [From World Action Models to Embodied Brains: A Roadmap for Open-World Physical Intelligence](https://arxiv.org/abs/2607.11689)
- [vla-evaluation-harness](https://github.com/allenai/vla-evaluation-harness)
- [StarWAM](https://github.com/shaohua-pan/StarWAM)
- [FastWAM](https://github.com/yuantianyuan01/FastWAM)
- [FastWAM issue: predicted future video and action trajectory inconsistency](https://github.com/yuantianyuan01/FastWAM/issues/62)
- [LeRobot](https://github.com/huggingface/lerobot)

引用这些项目不代表其作者认可 WAMProbe。正式发布前应再次核实接口、许可证、checkpoint 和 benchmark 设置。

---

## 25. 最终建议

WAMProbe 最容易失败的方式，是一开始就变成“支持十个模型、二十个指标、五个模拟器”的巨大工程。更可靠的顺序是：

```text
先用 Toy benchmark 证明指标不是假的
→ 再用配对模拟数据证明动作因果差异可测
→ 再接一个真实 WAM
→ 最后验证指标是否与控制收益相关
```

如果这四步能够完成，即使 v0.1 只支持一个真实 WAM，项目也已经具备明确的开源价值和研究价值。
