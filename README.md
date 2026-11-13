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
