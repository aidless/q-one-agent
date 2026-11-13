# Q-One Agent

[![CI](https://github.com/aidless/q-one-agent/actions/workflows/checks.yml/badge.svg)](https://github.com/aidless/q-one-agent/actions/workflows/checks.yml)

**English documentation: [README.md](README.md)**（本文件为完整中文版）

Q-One Agent 是 Q-One 系统的第二仓：把一个结构化决策路由给某个 provider，捕获证据局限，产出一条可被 `q-one-core` 记录的推荐。它按设计做到 provider 无关：本地规则、开源模型或 Laya/Jev 风格适配器都能实现同一接口，而不改动账本。

原 CLI 默认仍用确定性成本启发式做接线演示。应用层使用 `qone_agent.runtime.run_model`，它调用真实的 Ollama/Laya 或显式配置的云端端点，绝不用启发式静默顶替。Laya 与 Ollama 有真实的合成连通性回执；云端传输是 fixture 测试过的，未做真实 provider 验证。

> 中文研究入口：[多学科融合实现路线](docs/SYNTHESIS_IMPLEMENTATION.zh-CN.md)。v0.2 已接入真实 Laya、Ollama 与云端兼容适配器；[完整个人应用与验收](https://github.com/aidless/q-one-life)。

## 三个仓库的关系

- [`q-one-core`](https://github.com/aidless/q-one-core) 拥有决策与事件协议。
- `q-one-agent` 拥有路由、provider 适配器、证据捕获与推荐格式化。
- `q-one-life` 拥有个人本体、复盘与本地用户界面。

agent 收到的是带已记录基线的 core 决策投影。它从不写人的决定，也从不把任何推荐标记为「可自动执行」。

## 快速开始

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .

qone-agent providers
qone-agent recommend --decision-file examples/agent_input.json
```

### 2026-11-10 实测输出（全新 venv，`pip install -e .`）

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

输出含 `recommendation` 与 `evidence` 两个对象。只有在调用方复核之后，才把推荐载荷发给 `q-one-core` 的 `recommendation_made` 事件。

## Results（真实数字）

| 检查 | 数字 | 命令（2026-11-10） |
|---|---|---|
| 测试套件 | **7 passed + 6 subtests**（0.06 s） | `pip install pytest && python -m pytest -q` |
| Quickstart | `providers` 列出 `cost-heuristic-v0.1`；`recommend` 产出带门禁的推荐（`requires_human: true`、`auto_eligible: false`、`success_probability: null`） | 上面两条 `qone-agent` 命令 |

## 适配器契约

一个 provider 实现：

```python
recommend(decision: DecisionContext, evidence: EvidenceBundle) -> ProviderResult
```

`ProviderResult` 必须包含所选选项、置信度、可选成功概率、理由与来源标识。`AgentEngine` 应用人工复核策略，在输出契约里强制 `requires_human=true`、`auto_eligible=false`。

新增模型接入前先读 [docs/ADAPTER_CONTRACT.md](docs/ADAPTER_CONTRACT.md)；开源模型论文的证据与可复现计划见 [docs/MODEL_RESEARCH.md](docs/MODEL_RESEARCH.md)。

## 真实运行时 API（v0.2）

`run_model(decision, provider, config, evidence=(), remote_confirmed=False)` 返回带校验推荐与调用回执的 `RunResult`。`provider` 取 `ollama`、`laya` 或 `cloud`。远程端点要求显式确认；应用层还会把确认绑定到内容、端点与模型预览。输入使用字段白名单。

可选 Laya 依赖用 `pip install '.[laya]'` 安装；权重与 PyTorch 不包含在基础包内。多语 checkpoint 钉在 `1720e3e3357cfe1e281542e223f8273b0890ca34`。超长/截断的 Laya 输入会被拒绝。Laya 产出的是选项选择，不是生成的解释。所有运行时输出的 `success_probability=null`；其置信度未在个人结果上做过验证。

契约检查：`python -m pytest -q`。它们用 mock HTTP 传输与 mock 截断结果，不是真实精度数据。

## 隐私与证据

Provider 适配器默认不得记录原始私密上下文。证据记录应标明来源及其局限；生成的理由不是独立验证。凭证放在运行环境里，`agent-runs/` 不进 Git。

## Limits（限制）

- **无能力数字**：已提交的测试套件用 mock HTTP 传输与 mock 截断结果——验证的是契约，不是模型质量。没有任何 provider 的精度/校准/延迟数字。
- CLI 默认的 `cost-heuristic-v0.1` provider 是确定性接线演示，零校准证据（它自己的 rationale 就这么写）。
- Laya/Ollama 连通性回执是合成的；云端传输仅 fixture 测试，未做真实 provider 验证。
- 所有运行时输出 `success_probability=null`；本仓没有任何置信度值在个人结果上验证过。

本项目以 MIT 许可发布。
