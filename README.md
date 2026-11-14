# Q-One Agent

[![CI](https://github.com/aidless/q-one-agent/actions/workflows/checks.yml/badge.svg)](https://github.com/aidless/q-one-agent/actions/workflows/checks.yml)

**中文文档：[README.zh-CN.md](README.zh-CN.md)**（完整中文版）

Q-One Agent is the second repository in the Q-One system. It routes a structured decision to a provider, captures evidence limitations, and emits a recommendation that `q-one-core` can record. It is provider-neutral by design: a local rule, an open-source model, or a Laya/Jev-style adapter can implement the same interface without changing the ledger.

The original CLI still defaults to a deterministic cost heuristic for wiring demonstrations. The application uses `qone_agent.runtime.run_model`, which calls real Ollama/Laya or an explicitly configured cloud endpoint. It never silently substitutes that heuristic. Laya and Ollama have real synthetic connectivity receipts; cloud transport is fixture-tested, not live-provider verified.

> Research entry: [multi-discipline implementation route](docs/SYNTHESIS_IMPLEMENTATION.zh-CN.md). v0.2 connects real Laya, Ollama, and cloud-compatible adapters; [full personal application and acceptance](https://github.com/aidless/q-one-life).

## Relationship to the other repositories

- [`q-one-core`](https://github.com/aidless/q-one-core) owns the decision and event protocol.
- `q-one-agent` owns routing, provider adapters, evidence capture, and recommendation formatting.
- `q-one-life` owns the personal ontology, reviews, and local user interface.

The agent receives a core decision projection containing a recorded baseline. It never writes the human decision and it never marks a recommendation as safe for automatic execution.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .

qone-agent providers
qone-agent recommend --decision-file examples/agent_input.json
```

### Captured output (2026-11-10, fresh venv, `pip install -e .`)

```text
$ qone-agent providers
cost-heuristic-v0.1

$ qone-agent recommend --decision-file examples/agent_input.json
{
  "recommendation": {
    "decision_id": "D-20261023-example",
    "option_id": "meeting",
    "confidence": 0.55,
    "success_probability": null,
    "rationale": "Selected the option with the lowest declared expected cost. This provider is a deterministic heuristic and has no calibration evidence.",
    "source": "cost-heuristic-v0.1",
    "gate_reasons": ["low_confidence", "insufficient_personal_calibration"],
    "requires_human": true,
    "auto_eligible": false
  },
  "evidence": {
    "items": [{"kind": "user_supplied", "locator": "user_context", ...}],
    "limitations": ["user_supplied_context_not_independently_verified"]
  }
}
```

The output contains a `recommendation` object and an `evidence` object. Send the recommendation payload to the `recommendation_made` event in `q-one-core` only after the caller has reviewed it.

## Results

| Check | Number | Command (2026-11-10) |
|---|---|---|
| Test suite | **7 passed + 6 subtests** (0.06 s) | `pip install pytest && python -m pytest -q` |
| Quickstart | `providers` lists `cost-heuristic-v0.1`; `recommend` emits a gated recommendation (`requires_human: true`, `auto_eligible: false`, `success_probability: null`) | the two `qone-agent` commands above |

## Adapter contract

A provider implements:

```python
recommend(decision: DecisionContext, evidence: EvidenceBundle) -> ProviderResult
```

`ProviderResult` must include the selected option, confidence, optional success probability, rationale, and a source identifier. `AgentEngine` applies the human-review policy and sets `requires_human=true` and `auto_eligible=false` in the emitted contract.

Read [docs/ADAPTER_CONTRACT.md](docs/ADAPTER_CONTRACT.md) before adding a model connector. Read [docs/MODEL_RESEARCH.md](docs/MODEL_RESEARCH.md) for the evidence and reproducibility plan around open-source model papers.

## Real runtime API (v0.2)

`run_model(decision, provider, config, evidence=(), remote_confirmed=False)` returns a `RunResult` with a validated recommendation and call receipt. `provider` is `ollama`, `laya`, or `cloud`. Remote endpoints require explicit confirmation; the application additionally binds confirmation to the content, endpoint and model preview. Inputs use a field allowlist.

Install the optional Laya dependency with `pip install '.[laya]'`; weights and PyTorch are not included in the base package. The multilingual checkpoint is pinned to `1720e3e3357cfe1e281542e223f8273b0890ca34`. Oversized/truncated Laya inputs are rejected. Laya produces a choice, not a generated explanation. All runtime outputs leave `success_probability=null`; their confidence is not validated on personal outcomes.

Run contract checks with `python -m unittest discover -s tests -v`. They use mock HTTP transport and a mocked truncation result, not real accuracy data.

## 测试与复算

### 测试（2026-11-01 实测）

```bash
# 在仓库外建 venv（路径含字面反斜杠与冒号，`F:\deepseek`，venv 拒绝建在
# 含 `:` 的路径里——这是 Python venv 对 PATH 分隔符的硬性拒绝，不是本仓缺陷）
python3 -m venv /tmp/qone-venv
/tmp/qone-venv/bin/pip install -e .
/tmp/qone-venv/bin/python -m pytest tests/ -q     # 9 passed, 6 subtests passed
```

或按 README 顶部与 CI 的 unittest 方式：

```bash
python3 -m unittest discover -s tests -v
```

测试覆盖：云端契约（mock 传输）、远程未经确认拒绝发送、未知选项/非法强度
拒绝、错误不泄露服务体或密钥、Ollama 契约、内置本地 OpenAI 兼容契约、
Laya 截断 mock 等——均为**mock 传输，无真实准确率数据**。

## 证明什么 / 不证明什么

**证明什么**：`run_model` 对 provider 中性接口的契约正确性——云端/Ollama/Laya
适配器都走同一 `ProviderResult` 校验；远程端点绑定确认（内容+端点+模型预览）；
字段 allowlist 过滤；错误不泄露密钥；`success_probability=null` 契约。

**不证明什么**：
- 测试用 **mock HTTP 传输与 mock 截断结果**，**不含任何真实模型准确率**——
  本仓不声称对个人决策结果做经验验证（README 顶部已明确 "Laya and Ollama
  have real synthetic connectivity receipts; cloud transport is fixture-tested,
  not live-provider verified"）。
- 内置 CLI 的确定性成本启发式**不替代**真实 `run_model`（README 顶部已声明）。
- Laya 权重与 PyTorch **不在基础包**内（`pip install '.[laya]'` 只装依赖，
  权重/运行时需另行提供）；多语言 checkpoint 固定在
  `1720e3e3357cfe1e281542e223f8273b0890ca34`。
- 本仓是**决策路由/适配层**，**不写**人的决策、**不标**推荐可自动执行
  （`requires_human=true`, `auto_eligible=false` 强制）。

## 目录结构

```
q-one-agent/
├── src/qone_agent/          # 核心包：contracts / engine / evidence / policy
│   ├── cli.py               # qone-agent 命令行（默认成本启发式，仅演示）
│   ├── runtime.py           # run_model：真实 Ollama/Laya/云端 适配器
│   └── providers/           # base / rule 适配器契约
├── schemas/recommendation.schema.json
├── docs/                    # ADAPTER_CONTRACT / MODEL_RESEARCH / 中文实现路线
├── examples/agent_input.json
├── tests/test_runtime.py    # mock 传输契约测试（9 + 6 subtests）
└── pyproject.toml           # 入口 qone-agent = qone_agent.cli:main
```

## Privacy and evidence

Provider adapters must not log raw private context by default. Evidence records should identify a source and its limitations; a generated rationale is not independent verification. Keep credentials in the runtime environment and keep `agent-runs/` out of Git.

## Limits

- **No capability numbers.** The committed test suite uses mock HTTP transport and a mocked truncation result — it verifies the contract, not model quality. There are no accuracy, calibration, or latency numbers for any provider.
- The CLI's default `cost-heuristic-v0.1` provider is a deterministic wiring demo with zero calibration evidence (its own rationale says so).
- Laya/Ollama connectivity receipts are synthetic; cloud transport is fixture-tested, not live-provider verified.
- All runtime outputs leave `success_probability=null`; no confidence value in this repo is validated against personal outcomes.

This repository is MIT licensed.

## 验收题库与复算

`eval/cases.jsonl` 是 20 条可执行验收题，覆盖十二个口径（契约边界、policy 门、成本启发式、
engine 路由与端到端、evidence 局限、runtime 字段白名单与输出校验、schema 形状、`docs/` 契约
措辞、测试声明条数）。其中 **18 条是 `expr` / `raises`**，期望值不是抄文档，而是**真调本仓
API 或真解析本仓数据文件**现算 (`qone_agent.contracts` / `policy` / `providers.rule` /
`engine` / `evidence` / `runtime`，以及 `examples/agent_input.json`、
`schemas/recommendation.schema.json`、`tests/test_runtime.py`)；另 2 条 `doc` 题钉住
`docs/` 里写死的契约措辞。

| axis | 条数 | 题号 | 考什么 |
|---|---|---|---|
| contracts/option | 2 | CT-01、CT-02 | id/label 去空白 + 成本转 float；`expected_cost_hours=True` 必须拒（布尔不算数字） |
| contracts/decision | 2 | CT-03、CT-04 | 选项数上界（9 个即拒）；`baseline.option_id` 必须落在选项集内 |
| contracts/recommendation | 2 | CT-05、CT-06 | `confidence=1.5` 拒绝；`requires_human=True` / `auto_eligible=False` 默认组合 |
| policy/gates | 3 | PO-01–PO-03 | 0.55+未校准的 gate 组合与顺序；`0.70`/`n=20` 边界清零；high risk + 不可逆的 reason 顺序 |
| provider/cost-heuristic | 2 | PR-01、PR-02 | 成本并列时按 id 决胜、confidence=0.50；`examples/agent_input.json` 实选 `meeting`/0.55 |
| engine/pipeline | 2 | EN-01、EN-02 | 端到端选项+gate_reasons+evidence 局限；未注册 provider 抛 `ValueError` |
| evidence/limitations | 1 | EV-01 | 空白 context → 0 条目 + `empty_context` |
| runtime/allowlist | 1 | RT-01 | `public_context` 的 9 个白名单键（`events` 必须消失） |
| runtime/validation | 1 | RT-02 | provider 用 `confidence=True` 冒充数字必须被 `ProviderError` 拦下 |
| schemas/contract | 1 | SC-01 | `recommendation.schema.json` 的 8 个 `required` 字段与顺序 |
| docs/contract | 2 | DOC-01、DOC-02 | 适配器 `source` 不可变；模型凭证要冻结「输入哈希 + 输出推荐」 |
| tests/declared-count | 1 | TK-01 | `tests/test_runtime.py` 用 ast 数出 9 个 `test_` 方法（README 声称 9） |

```bash
python3 eval/run_cases.py            # 20/20 cases passed
python3 eval/run_cases.py --save     # 顺带把结果写进 eval/run-report.json
python3 eval/run_cases.py --selftest # 篡改第一条期望值，必须变红（19/20）
```

退出码：`0` 全过、`1` 有 case 失败、`2` 题库自身坏了（读不到/缺字段/重复 id）；
`--selftest` 的判据是**变红**（`19/20` + `contracts/option: 1 条 —— CT-01`），
它变红才说明这套题会失败，全绿反而是装饰。

**数字如何复算**：每题 `verify` 就是一段可执行 Python——`expr` 以 `result = ...` 收尾，
`raises` 要求抛出的异常类名等于 `expected`，`doc` 是 `相对路径::正则`。把某题的 `verify`
粘进 `python3` 即可复现该数字；`eval/run-report.json` 里每条 case 带 `id` / `axis` /
`detail`，`--save` 重跑一次就重建整份报告，不需要手工抄数。每题的 verify 头三行会把
`<repo>/src` 插进 `sys.path`，所以**裸克隆（未 `pip install -e .`）也能跑**；改了
`contracts.py` / `policy.py` / `rule.py` 里任一常量或边界，对应题立刻变红。

**失败归因**：`run_cases.py` 不只报通过率，失败时按 `axis` 汇总，例如
`policy/gates: 1 条 —— PO-02`，直接指出是哪个模块的哪个口径坏了，而不是只给一个 pass_rate。
