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

The terms “Laya” and “Jev” are treated as user-provided model or workflow labels until a primary paper, model card, or repository is attached. An adapter should record the exact source rather than inferring identity from a nickname.
