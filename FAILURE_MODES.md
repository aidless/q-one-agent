# Failure modes

These are limits of q-one-agent that the offline matrix does not remove. The same limits are summarized in [README.md](README.md) and [README.zh-CN.md](README.zh-CN.md).

## 1. Silent substitution of cost-heuristic-v0.1

`run_model` does not import the cost heuristic. `eval/fault-matrix.json` is recomputed by `make check`. It injects connection refused, timeout, malformed JSON, schema-invalid output, and empty content for Ollama, Laya, and cloud. Fourteen cells raise `ProviderError`. The Laya connection-refused cell raises `ConnectionRefusedError`, because that adapter has no HTTP client and `subprocess.run` does not catch `OSError`. No cell returns a recommendation, and `CostHeuristicProvider.recommend` is not called.

Residual: a caller that catches only `ProviderError` still sees that Laya `ConnectionRefusedError`. It is a propagated exception, not a heuristic recommendation. When the optional `laya` package is missing, the worker exits non-zero and `run_model` raises `ProviderError` (`Laya无法运行；请检查模型安装、权重路径和可用内存` on the machine used for this change). That observation depends on the environment, so it is not a frozen matrix cell.

## 2. Writing the human decision

CLI output and `run_model` recommendations do not contain `decided_by`, `human_decision`, `recommendation_overridden`, or `decided_option_id`. Fault injection does not mutate the input decision, including `baseline`. `option_id` on a recommendation is the provider's selection. A caller can still record that id as a human decision in q-one-core. This repository does not.

## 3. Marking a recommendation safe for automatic execution

`_validated` sets `requires_human` true and `auto_eligible` false. It does not copy those fields, or `decided_by`, from model JSON. A fixture that sends `auto_eligible: true` still returns `auto_eligible: false`, `requires_human: true`, and `success_probability` null. The source is `provider:model`, not a source string inside the model JSON.

The vendored q-one-core `validate_recommendation` at commit `2d243b33c0beede7cf05d1ab2212f5fb45d39c6a` also overwrites those two flags. It does not reject a payload that asked for automatic execution. Overwrite is not a recorded refusal.

## 4. Local schema versus the core validator

q-one-core at that commit publishes `schemas/decision.schema.json` and does not publish a recommendation JSON Schema file. The pin is the Python function in `schemas/vendor/q-one-core/validate_recommendation.py`. This repo's `schemas/recommendation.schema.json` requires `decision_id` and `gate_reasons`. CLI engine output satisfies the local schema and the vendored validator. `run_model` output satisfies the vendored validator and is rejected by the local schema because those two keys are absent. Core's `DecisionService.recommend` adds `decision_id` after validation and replaces `gate_reasons`. This repository does not call it.

## 5. Connectivity receipts

`RunResult.receipt()` is built in memory only after `run_model` returns. Fields: `run_id`, `provider`, `model`, `duration_ms`, `input_sha256`, `usage`, `evidence_ids`. The recommendation body is omitted.

No file in this repository is such a receipt. Nothing recorded here was sent to Ollama, Laya, or a cloud host. The default Ollama URL in code is `http://127.0.0.1:11434` and the default model name in code is `qwen3:8b`. The Laya checkpoint string is `convaiinnovations/laya-multilingual` at revision `1720e3e3357cfe1e281542e223f8273b0890ca34`. Those are defaults, not a completed call.

Cloud cells use `httpx.MockTransport` or a closed loopback port. Cloud has not been live-verified. Loopback cloud skips the HTTPS and remote-confirmation gates; `tests/test_runtime.py` covers the unconfirmed-remote refusal separately.

## 6. The matrix is not a model evaluation

The HTTP client timeout is hard-coded at 120 seconds and the Laya worker timeout at 150 seconds. The matrix injects those timeouts; it does not wait them out. Connection refused for Ollama and cloud is a real TCP refusal on an ephemeral `127.0.0.1` port. Comparisons C1–C3 in `PREREG.md` have not been run. There is no accuracy, calibration, user, or adoption number.

## 7. Pin rot and the example decision id

`make check` hashes the vendored file against `PIN.json`. It does not fetch q-one-core. The copy stays at the pinned commit until a person updates it.

`examples/agent_input.json` uses `D-20261023-example`. Core's decision schema pattern is `^D-[0-9]{8}-[a-f0-9]{6}$`. The example does not match. Core's Python `validate_decision` does not enforce that pattern. This repository does not claim the example is core-schema-valid.

## GitHub About

This commit does not edit the GitHub About field. Text observed on 2026-11-16: "Provider-neutral orchestration for the Q-One decision protocol".

About replacement: Routes one structured decision to a provider and returns a human-reviewed recommendation for q-one-core. It does not write the human decision or mark a recommendation safe for automatic execution. The CLI demo is cost-heuristic-v0.1. No live-provider result is stored in this repository.
