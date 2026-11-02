# PREREG — Q-One Agent 预注册/规格说明

> 本文件是 Q-One Agent（provider-neutral 推荐编排）的预注册规格。它把仓库
> `research-manifest.json` 中已声明的假设与 `docs/MODEL_RESEARCH.md` 中的
> 计划比较固化为「可证伪的假设 + 评测方案 + 成功标准 + 明确边界」。
> 本文件**不**声称任何结果已达成——它只声明**将要/正在**检验什么、怎么检验、
> 以及哪些结论**明确不**由本仓产生。

## 1. 研究问题

来自 `research-manifest.json`：

> How can model and rule providers produce inspectable recommendations under one
> human-reviewed contract?

（在同一个「人审阅」契约下，模型与规则 provider 如何产出可检视的推荐？）

## 2. 假设（来自 research-manifest.json，逐条原样）

- **H1**：A narrow provider interface makes model routing replaceable without
  changing the decision ledger.
  （窄 provider 接口使得模型路由可在不改变决策账本的前提下替换。）
- **H2**：Explicit evidence limitations reduce the chance that generated rationale
  is mistaken for verified fact.
  （显式证据局限降低了「生成的理由被误当成已验证事实」的概率。）

## 3. 评测方案（来自 docs/MODEL_RESEARCH.md 的 Planned comparisons）

本仓的评测**计划**（不是结果）如下，均为契约/行为层评测，**不是模型准确率基准**：

| 编号 | 对比 | 固定项 | 指标 |
|---|---|---|---|
| C1 | 确定性本地规则 vs 本地开源指令模型 | 同一决策集、同一准则 | option accuracy, baseline agreement, override rate, latency, cost, abstention rate |
| C2 | 无检索证据 vs 有检索证据 | 决策集、准则、provider 固定 | 同上 + calibration（当提供概率时） |
| C3 | 单一推荐 vs 小型面板 + 显式裁决规则 | 决策集、准则 | 同上 |

数据记录需冻结（见 `docs/MODEL_RESEARCH.md` "Freeze" 段）：model/revision 摘要、
prompt/adapter 版本、解码参数与工具权限、检索源与时间戳、输入决策哈希与输出推荐、
失败/弃权/缺证据。

## 4. 成功标准

- **H1 支持判据**：在不改 `qone_agent.contracts` / 决策账本的前提下，新增一个
  provider 适配器（实现 `recommend(DecisionContext, EvidenceBundle) -> ProviderResult`）
  即被 `AgentEngine` 正确接纳；适配器替换后契约校验结果不变（`run_model` 对
  provider 中性接口的契约正确性，见 README「证明什么」）。
- **H2 支持判据**：当证据束明确标记局限（`EvidenceBundle` 的 limitation 字段非空）时，
  输出的 `rationale` 被策略层标记为「非独立验证」，而不是被当作已验证事实；
  测试断言该标记存在（`requires_human=true`, `auto_eligible=false`）。
- **判为「不支持」的条件**：若任一 provider 的契约校验在替换后失败、或
  `rationale` 在证据局限非空时仍被策略层当作已验证事实，则对应假设判定为
  不支持/需修正。

## 5. 明确边界（本仓**不**证明什么）

1. **不含任何真实模型准确率数据**：现有测试全部使用 mock HTTP 传输与 mock
   截断结果（README「不证明什么」第 1 条、`MODEL_RESEARCH.md` "not a model
   benchmark"）。C1–C3 是**计划**，尚未执行。
2. **没有已集成并评测的真实 provider**：`MODEL_RESEARCH.md` 明确写 "no real
   provider has been integrated or evaluated here yet"。Laya 的连通性收据是
   合成/模拟，云端传输是 fixture 测试，**不是**线上 provider 验证。
3. **内置 CLI 的确定性成本启发式不替代** `run_model`（README 已声明）。
4. **Laya 权重与 PyTorch 不在基础包**：`pip install '.[laya]'` 只装依赖，权重与
   运行时需另行提供；多语言 checkpoint 固定在
   `1720e3e3357cfe1e281542e223f8273b0890ca34`。
5. **本仓是决策路由/适配层**：不写人的决策、不标推荐可自动执行
   （`requires_human=true`, `auto_eligible=false` 强制）。
6. **未做校准声明**：`success_probability` 一律为 `null`，置信度不针对个人
   结果做经验验证（README「不证明什么」）。
