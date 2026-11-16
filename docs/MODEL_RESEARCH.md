# Model research plan

The goal of this repository is to compare provider behavior under a stable decision contract. The first implementation uses a deterministic heuristic to validate wiring; it is not a model benchmark.

## Evidence record for each provider

Freeze:

- model and revision or image digest
- prompt and adapter version
- decoding parameters and tool permissions
- retrieved sources and timestamps
- input decision hash and output recommendation
- failures, abstentions, and missing evidence

## Planned comparisons

1. Deterministic local rule versus a local open-source instruction model.
2. With and without retrieved evidence, keeping the decision set and criterion fixed.
3. Single recommendation versus a small panel with an explicit adjudication rule.

Report option accuracy, baseline agreement, override rate, calibration when probabilities are supplied, latency, cost, and abstention rate. Separate descriptive replay results from any user-facing claim.

Laya has been identified as [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya), with a model card at [convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya). Jev is documented by [TypeSafe AI](https://docs.typesafe.ai/introduction). These primary sources were checked on 2026-10-23. Adapter code for Ollama, Laya, and an OpenAI-compatible cloud endpoint lives in `src/qone_agent/runtime.py`. No committed artifact records a live call to any of them, and comparisons 1–3 above have not been run. See the [Chinese synthesis implementation plan](SYNTHESIS_IMPLEMENTATION.zh-CN.md) for source-linked next steps.
