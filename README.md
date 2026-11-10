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

Run contract checks with `python -m pytest -q`. They use mock HTTP transport and a mocked truncation result, not real accuracy data.

## Privacy and evidence

Provider adapters must not log raw private context by default. Evidence records should identify a source and its limitations; a generated rationale is not independent verification. Keep credentials in the runtime environment and keep `agent-runs/` out of Git.

## Limits

- **No capability numbers.** The committed test suite uses mock HTTP transport and a mocked truncation result — it verifies the contract, not model quality. There are no accuracy, calibration, or latency numbers for any provider.
- The CLI's default `cost-heuristic-v0.1` provider is a deterministic wiring demo with zero calibration evidence (its own rationale says so).
- Laya/Ollama connectivity receipts are synthetic; cloud transport is fixture-tested, not live-provider verified.
- All runtime outputs leave `success_probability=null`; no confidence value in this repo is validated against personal outcomes.

This repository is MIT licensed.
