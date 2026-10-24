# Q-One Agent

> 中文研究入口：[多学科融合实现路线](docs/SYNTHESIS_IMPLEMENTATION.zh-CN.md)。当前为初版原型，真实模型接入与端到端验收尚未完成。

Q-One Agent is the second repository in the Q-One system. It routes a structured decision to a provider, captures evidence limitations, and emits a recommendation that `q-one-core` can record. It is provider-neutral by design: a local rule, an open-source model, or a Laya/Jev-style adapter can implement the same interface without changing the ledger.

The included provider is a deterministic cost heuristic. It is a wiring example, not a capable general model and not a calibrated forecast.

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

The output contains a `recommendation` object and an `evidence` object. Send the recommendation payload to the `recommendation_made` event in `q-one-core` only after the caller has reviewed it.

## Adapter contract

A provider implements:

```python
recommend(decision: DecisionContext, evidence: EvidenceBundle) -> ProviderResult
```

`ProviderResult` must include the selected option, confidence, optional success probability, rationale, and a source identifier. `AgentEngine` applies the human-review policy and sets `requires_human=true` and `auto_eligible=false` in the emitted contract.

Read [docs/ADAPTER_CONTRACT.md](docs/ADAPTER_CONTRACT.md) before adding a model connector. Read [docs/MODEL_RESEARCH.md](docs/MODEL_RESEARCH.md) for the evidence and reproducibility plan around open-source model papers.

## Privacy and evidence

Provider adapters must not log raw private context by default. Evidence records should identify a source and its limitations; a generated rationale is not independent verification. Keep credentials in the runtime environment and keep `agent-runs/` out of Git.

This repository is MIT licensed.
