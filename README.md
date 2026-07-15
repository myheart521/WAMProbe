# WAMProbe

WAMProbe 是一个面向 World Action Model（WAM）的开源评测工具箱，重点评估：

- 动作与预测未来之间的因果一致性；
- 动力学和时间一致性；
- 候选动作排序与闭环控制价值；
- 控制收益与推理成本之间的权衡。

项目当前处于规划与初始化阶段，尚未发布可用 API。

## 项目文档

- [详细开发规划](docs/WAMProbe_PLAN.md)

## 初始目录

```text
WAMProbe/
├── configs/          # 模型、benchmark 和实验配置
├── docs/             # 设计与规划文档
├── schemas/          # 能力、数据和结果 JSON Schema
├── src/wamprobe/     # Python 包
└── tests/            # 自动化测试
```

## 开发状态

第一阶段将实现 capability manifest、`WAMAdapter` 协议、Toy benchmark 和 reference baselines。具体范围与验收标准见详细规划文档。
