<p align="right">
  <a href="README.md">English</a> · <strong>简体中文</strong>
</p>

<p align="center">
  <img src="docs/assets/wamprobe-hero.png" alt="WAMProbe——面向世界动作模型的反事实评测工具" width="100%">
</p>

<h1 align="center">WAMProbe</h1>

<p align="center">
  <strong>面向世界动作模型的反事实评测工具。</strong><br>
  检查预测未来是否真正响应动作、是否遵循正确动力学，以及能否帮助机器人选出更好的动作。
</p>

<p align="center">
  <a href="https://github.com/myheart521/WAMProbe/actions/workflows/ci.yml"><img src="https://github.com/myheart521/WAMProbe/actions/workflows/ci.yml/badge.svg" alt="CI 状态"></a>
  <a href="https://github.com/myheart521/WAMProbe/actions/workflows/docs.yml"><img src="https://github.com/myheart521/WAMProbe/actions/workflows/docs.yml/badge.svg" alt="文档状态"></a>
  <a href="https://pypi.org/project/wamprobe/"><img src="https://img.shields.io/pypi/v/wamprobe?include_prereleases&amp;label=PyPI" alt="PyPI 版本"></a>
  <a href="https://github.com/myheart521/WAMProbe/releases"><img src="https://img.shields.io/github/v/release/myheart521/WAMProbe?include_prereleases&amp;label=release" alt="GitHub 发行版"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11--3.13-3776AB.svg" alt="支持 Python 3.11 至 3.13"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-0f766e.svg" alt="Apache-2.0 许可证"></a>
</p>

<p align="center">
  <a href="https://myheart521.github.io/WAMProbe/"><strong>在线文档</strong></a> ·
  <a href="#60-秒上手"><strong>快速开始</strong></a> ·
  <a href="#查看结果"><strong>结果示例</strong></a> ·
  <a href="docs/metrics/CORE_METRICS.md"><strong>指标卡</strong></a> ·
  <a href="CONTRIBUTING.md"><strong>参与贡献</strong></a>
</p>

> **发行状态：**[`v0.1.0rc1`](https://github.com/myheart521/WAMProbe/releases/tag/v0.1.0rc1)
> 已作为候选版本发布到 [PyPI](https://pypi.org/project/wamprobe/0.1.0rc1/)。
> 无依赖的 CPU 核心已经可以直接使用；目前仍在
> [Issue #2](https://github.com/myheart521/WAMProbe/issues/2) 等待独立外部用户复现报告。

## WAMProbe 要解决的问题

世界动作模型可能生成一段看起来很成功的视频，却悄悄忽略了输入的候选动作。模型也可能
对动作反应很强烈，但把运动方向预测得完全相反。单独使用视频质量或任务成功率，无法区分
这些本质不同的失败。

WAMProbe 会在每条动作分支开始前恢复到**完全相同的初始状态**，然后分别回答三个问题：

| 问题 | 检查内容 | 能发现的典型问题 |
|---|---|---|
| **动作真的有影响吗？** | 不同动作下预测未来的分离程度与几何关系 | 所有动作都得到同一个“看似合理”的未来 |
| **模型响应正确吗？** | 方向、状态误差、无操作行为及参考动力学一致性 | 模型发生了运动，但方向完全相反 |
| **预测有控制价值吗？** | 候选动作排序、Top-1 遗憾和闭环回报 | 预测看起来准确，却选出了更差的动作 |

WAMProbe 始终输出一组可解释的**指标剖面**，不会把不同问题压缩成一个不透明的综合分数。

<p align="center">
  <img src="docs/assets/evaluation-pipeline.png" alt="WAMProbe 从共享初始状态生成动作分支，对比模型未来和参考未来，再评测控制价值" width="100%">
</p>

## 60 秒上手

核心包没有运行时依赖，内置基准可以直接在 CPU 上执行。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install wamprobe

wamprobe demo \
  --benchmark pointmass \
  --contexts 12 \
  --seed 7 \
  --output runs/pointmass-demo
```

你可以直接在浏览器中打开 `runs/pointmass-demo/report.html`，也可以检查版本化的 JSON 和
Markdown 结果：

```text
runs/pointmass-demo/
├── summary.json   # 机器可读的指标、区间和配对差值
├── results.jsonl  # 每个模型、每个共享上下文对应一条稳定记录
├── report.md      # 便于代码审阅的指标表和解释
└── report.html    # 无需服务器即可打开的独立报告
```

如果需要固定到完全一致的候选版本：

```bash
python -m pip install wamprobe==0.1.0rc1
```

## 查看结果

仓库中提交的 PointMass 实验同时包含正确的 oracle 和刻意设计的错误基线。下面三行已经能
说明为什么不能单独解释 Action Dependence：

| 模型 | Action Dependence ↑ | 方向一致性 ↑ | Top-1 遗憾 ↓ | 诊断 |
|---|---:|---:|---:|---|
| `oracle-pointmass` | 1.00 | 1.00 | 0.00 | 动力学和动作选择均正确 |
| `wrong-direction` | 1.00 | **−1.00** | **2.00** | 响应动作，但方向相反 |
| `action-agnostic` | **0.00** | 0.00 | **1.00** | 完全忽略候选动作 |

<p align="center">
  <img src="docs/assets/diagnostic-profile.png" alt="PointMass 中 oracle、错误方向和动作无关基线的诊断剖面对比" width="100%">
</p>

<p align="center">
  <img src="docs/assets/pointmass-report-preview.png" alt="WAMProbe 根据仓库内 PointMass 实验真实生成的独立 HTML 报告" width="100%">
  <br>
  <sub>上图是仓库内 PointMass 实验实际生成的独立 HTML 报告截图。</sub>
</p>

图中的数值来自已提交的
[12 上下文 PointMass 报告](examples/pointmass-demo/report.md)，不是手写的界面样例。仓库还
提交了 [BlockPush](examples/blockpush-demo/report.md)、
[Gripper-Catch](examples/gripper-catch-demo/report.md)、
[视频质量/控制价值反例](examples/video-control-study/video-control-study.md)和
[闭环实验](examples/closed-loop-study/closed-loop-study.md)的预期结果。

## 已实现能力

### 评测核心

- 类型明确、与模型无关的 `WAMAdapter` 和 `ActionPredictorAdapter` 协议；
- 能力声明机制，防止系统悄悄输出模型不支持的指标；
- 从严格恢复的共享上下文生成配对干预；
- 以完整上下文为单位的 bootstrap 区间和精确上下文配对比较；
- 可检测损坏、按内容寻址的预测缓存，支持断点续跑；
- 确定性的 JSON/JSONL、Markdown 和独立 HTML 报告；
- 面向解析基准的纯 CPU、无依赖运行时核心。

### 基准与模型集成

| 组件 | 范围 | 验证内容 | 运行环境 |
|---|---|---|---|
| **PointMass-2D** | 内置解析基准 | 方向、动作依赖、候选排序和遗憾 | 无依赖 CPU |
| **BlockPush-2D** | 接触感知的操作玩具环境 | 接近、接触、物体运动和渲染观测 | 无依赖 CPU |
| **Gripper-Catch** | 附着感知的操作玩具环境 | 对齐、闭合命令、下落物体和抓取附着 | 无依赖 CPU |
| **LIBERO-CF-Mini** | 四类任务 × 四条分支 × 八步 | 模拟器精确恢复、可重复性和分支顺序无关性 | 可选隔离环境 |
| **StarWAM 路径** | 固定版本的观测到动作集成 | 类型化动作块推理及多 seed/NFE 执行证据 | 可选 GPU 环境 |

解析基准用于验证评测器本身，并不能证明能力可以迁移到真实机器人。LIBERO-CF-Mini 当前
验证的是配对数据生成，而不是策略质量。精确声明与限制记录在
[玩具基准卡](docs/benchmarks/TOY_BENCHMARKS.md)、
[LIBERO-CF-Mini 基准卡](docs/benchmarks/LIBERO_CF_MINI.md)和
[StarWAM 模型卡](docs/models/STARWAM.md)中。

## 指标剖面

| 指标 | 核心问题 | 期望方向 |
|---|---|---|
| **Action Dependence** | 不同候选动作下的预测终点是否分离？ | 结合其他检查时越高越好 |
| **Permutation Effect / p-value** | 预测分支几何关系是否超越标签置换并匹配真实动作几何？ | Effect 越大、p-value 越小 |
| **Counterfactual Direction** | 预测位移与真实位移是否对齐？ | `1` 为同向，`−1` 为反向 |
| **No-op Stability** | 无操作预测是否与真实无操作未来一致？ | 越高越好 |
| **State ADE / FDE** | 预测轨迹/终态与参考动力学相差多远？ | 越低越好 |
| **Candidate Ranking Correlation** | 模型给候选动作的排序是否与模拟器一致？ | 越高越好 |
| **Top-1 Regret** | 选择模型最看好的动作会损失多少真实回报？ | 越低越好 |
| **闭环回报/成功率** | 评分—执行—观测—重规划能否真正完成任务？ | 越高越好 |

完整定义、能力要求、并列值处理、反作弊说明和参考基线见
[核心指标卡](docs/metrics/CORE_METRICS.md)。传统 RGB PSNR 和全局 SSIM 可以作为诊断项，
但不会与状态准确度或控制价值混成一个分数。

## CLI 命令一览

| 命令 | 用途 |
|---|---|
| `wamprobe demo` | 运行 PointMass、BlockPush 或 Gripper-Catch 基线诊断 |
| `wamprobe report` | 不执行模型推理，直接从 `summary.json` 重建报告 |
| `wamprobe compare` | 在完全对齐的共享上下文上比较两个模型 |
| `wamprobe dataset-export` | 导出确定性的干预 JSONL 数据集 |
| `wamprobe dataset-validate` | 验证数据集记录及校验和 |
| `wamprobe video-control-study` | 对比渲染视频质量与控制指标 |
| `wamprobe closed-loop-study` | 运行最小评分—执行—观测重规划实验 |
| `wamprobe experiment-report` | 分析缓存的真实模型预测/执行矩阵 |
| `wamprobe doctor` | 检查固定版本的模型文件、大小、修订和哈希 |
| `wamprobe release-audit` | 审计发行包和可复现性证据 |

运行 `wamprobe <command> --help` 可以查看完整参数。
[15 分钟快速入门](docs/QUICKSTART.md)涵盖全部 CPU 工作流。

## 不重新运行模型也能复用结果

```bash
# 从按内容寻址的预测缓存恢复完全相同的请求。
wamprobe demo --contexts 12 --seed 7 \
  --cache-dir runs/cache --output runs/resumed

# 导出并验证完全一致的干预数据集。
wamprobe dataset-export --benchmark pointmass --contexts 12 \
  --output data/pointmass.jsonl
wamprobe dataset-validate data/pointmass.jsonl

# 比较完全一致的共享上下文，然后重建展示文件。
wamprobe compare runs/pointmass-demo runs/resumed \
  --left-model oracle-pointmass \
  --right-model copy-last-frame \
  --metric state_fde \
  --output runs/comparison.json
wamprobe report runs/pointmass-demo --output runs/rebuilt-report
```

## 接入自己的模型

WAMProbe 有意保持适配器接口精简。预测状态未来的模型实现 `WAMAdapter`；直接预测机器人
动作块的模型实现 `ActionPredictorAdapter`。二者都必须暴露类型化能力声明，评测器才能
区分模型直接支持、可推导和无法提供的证据。

```python
from wamprobe.api.capabilities import ModelCapabilities
from wamprobe.api.model import WAMAdapter


class MyWorldModel:
    @property
    def capabilities(self) -> ModelCapabilities:
        ...

    def predict_future(self, context, action, *, horizon: int, seed: int):
        ...

    def close(self) -> None:
        ...
```

发布新适配器前，请完成以下工作：

1. 如实声明输出能力和运行要求；
2. 固定上游模型版本与预处理契约；
3. 从完全一致的 context ID 运行配对动作；
4. 加入预期基线排序和至少一个失败模式测试；
5. 明确记录不支持的指标，不要悄悄换用代理指标。

建议先阅读[范围与能力 RFC](docs/rfcs/0001-scope-and-capabilities.md)、
[反事实指标 RFC](docs/rfcs/0002-counterfactual-metrics.md)和
[适配器选择记录](docs/research/ADAPTER_SELECTION.md)。

## 真实模型文件

模型权重永远不会提交到 Git。第一个 StarWAM 验证需要约 46.3 GB 固定版本的 StarWAM 和
Wan2.2 文件。请先按照[模型目录与下载规则](checkpoints/README.md)准备文件，再在不导入
PyTorch 或上游模型代码的情况下完成检查：

```bash
wamprobe doctor
wamprobe doctor --verify-hashes
```

StarWAM 和 LIBERO 的隔离环境、GPU 预检、预处理来源及 smoke 命令记录在
[`environments/starwam/README.md`](environments/starwam/README.md)和
[`environments/libero/README.md`](environments/libero/README.md)中。

## 可复现性设计

- 固定 seed 的确定性套件和稳定的上下文/动作标识；
- 带校验和的干预数据集与预测产物；
- 以完整上下文为单位进行 bootstrap，绝不把相关帧或动作分支视为独立样本；
- 配对比较前严格对齐 context ID；
- 版本化公共 JSON Schema 和证据清单；
- 字节级可复现的 wheel/sdist 构建与压缩包审计；
- 离线干净 wheel smoke test 和 GitHub 构建来源证明；
- Python 3.11–3.13 CI、代码格式、严格类型、覆盖率、Schema、链接、CodeQL 和严格文档检查。

比较或发布结果前，请阅读[可复现性指南](docs/reproducibility/REPRODUCIBILITY.md)和
[候选版本发布流程](release/README.md)。

## 文档导航

| 如果你想…… | 从这里开始 |
|---|---|
| 运行 CPU 演示 | [快速开始](docs/QUICKSTART.md) |
| 理解项目的研究动机 | [WAM/VLA 失败案例证据图谱](docs/research/WAM_VLA_FAILURE_CASES.md) |
| 正确解释指标 | [核心指标卡](docs/metrics/CORE_METRICS.md) |
| 接入一个新模型 | [范围与能力 RFC](docs/rfcs/0001-scope-and-capabilities.md) |
| 复现 LIBERO-CF-Mini | [基准卡](docs/benchmarks/LIBERO_CF_MINI.md) |
| 检查闭环实验协议 | [实验卡](docs/experiments/TOY_CLOSED_LOOP_V0.1.md) |
| 审计发行版 | [可复现性指南](docs/reproducibility/REPRODUCIBILITY.md) |
| 阅读完整实施计划 | [WAMProbe 中文规划文档](docs/WAMProbe_PLAN.md) |
| 浏览全部文档 | [在线文档站](https://myheart521.github.io/WAMProbe/) |

## 项目状态与路线图

`v0.1.0rc1` 工程范围已经实现并发布。正式验收目前只剩一项：由真实独立用户在
[Issue #2](https://github.com/myheart521/WAMProbe/issues/2) 提交干净环境安装复现报告。

下一阶段研究计划：

1. 扩展 LIBERO 初始状态覆盖；
2. 在适配器真正暴露对应能力后，评测动作条件真实 WAM 未来；
3. 在更完整的 Toy 层加入“遮挡物体记忆”诊断；
4. 审查外部复现证据，并发布正式 `v0.1.0`。

## 参与贡献

欢迎提交适配器、配对基准生成器、指标反作弊测试和独立复现报告。新增指标必须说明它要
发现的失败模式，并包含相对参考基线的 sanity check。

```bash
python -m pip install -e '.[dev]'
ruff format --check .
ruff check .
mypy
python scripts/validate_repository.py
mkdocs build --strict
pytest --cov=wamprobe --cov-report=term-missing --cov-fail-under=85
```

提交 Pull Request 前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 引用

如果 WAMProbe 对你的研究有帮助，请使用 [`CITATION.cff`](CITATION.cff) 或以下条目引用
对应软件版本：

```bibtex
@software{wamprobe_2026,
  title   = {WAMProbe: Counterfactual Evaluation for World Action Models},
  author  = {{WAMProbe contributors}},
  year    = {2026},
  version = {0.1.0rc1},
  url     = {https://github.com/myheart521/WAMProbe}
}
```

## 许可证

WAMProbe 使用 [Apache License 2.0](LICENSE) 开源。
