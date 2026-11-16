# Q-One Agent

[![CI](https://github.com/aidless/q-one-agent/actions/workflows/checks.yml/badge.svg)](https://github.com/aidless/q-one-agent/actions/workflows/checks.yml)

**中文文档：[README.zh-CN.md](README.zh-CN.md)**

**Limits:** this repository stores no live-provider result. Cloud transport is fixture-tested and has not been live-verified. There is no saved connectivity receipt. No accuracy, user, or adoption number is claimed. STATUS: WORK-IN-PROGRESS — not A yet.

## Problem

Q-One Agent routes one structured decision to one provider and emits a recommendation that q-one-core can record.
It does not write the human's decision, and it never marks a recommendation safe for automatic execution.
The `qone-agent` CLI defaults to deterministic `cost-heuristic-v0.1`; `run_model` calls Ollama, Laya, or a configured cloud endpoint and raises on the faults in the offline matrix instead of substituting that demo.

## Connectivity receipts

`RunResult.receipt()` is an in-memory dict built only after `run_model` returns a recommendation. Its fields are `run_id`, `provider`, `model`, `duration_ms`, `input_sha256`, `usage`, and `evidence_ids`. It does not include the recommendation body.

This repository contains no saved receipt. Nothing in this repository records a request that was sent to Ollama, Laya, or a cloud host: no timestamp of a completed call, and no model revision that answered. The default Ollama URL in code is `http://127.0.0.1:11434`. The default model name in code is `qwen3:8b`. The Laya checkpoint string in code is `convaiinnovations/laya-multilingual` at revision `1720e3e3357cfe1e281542e223f8273b0890ca34`. Those strings are configuration defaults, not evidence that a process answered.

HTTP faults in the matrix use `httpx.MockTransport` or a closed loopback port. Cloud transport has not been live-verified.

## Safety matrix

`make check` recomputes `eval/fault-matrix.json` offline and fails if the committed file differs. The matrix is three adapters (Ollama, Laya, cloud) by five faults (connection refused, timeout, malformed JSON, schema-invalid output, empty content). Fourteen cells raise `ProviderError`. The Laya connection-refused cell raises `ConnectionRefusedError` because that adapter has no HTTP client. No cell returns `cost-heuristic-v0.1`. A separate fixture row shows that model JSON with `auto_eligible: true` still comes back `auto_eligible: false` and `requires_human: true`.

Details and the residuals are in [FAILURE_MODES.md](FAILURE_MODES.md).

## Schema pin

The recommendation check uses the validator vendored from [q-one-core](https://github.com/aidless/q-one-core) commit `2d243b33c0beede7cf05d1ab2212f5fb45d39c6a` (`schemas/vendor/q-one-core/`). q-one-core at that commit does not publish a recommendation JSON Schema file. The CLI engine output passes that validator and this repo's `schemas/recommendation.schema.json`. `run_model` output passes the validator and is rejected by the local schema because `decision_id` and `gate_reasons` are absent. This repository does not call core's `DecisionService`.

`examples/agent_input.json` uses decision id `D-20261023-example`, which does not match core's decision id pattern `^D-[0-9]{8}-[a-f0-9]{6}$`.

## Relationship

- [`q-one-core`](https://github.com/aidless/q-one-core) owns the decision and event protocol. Its honesty pull request [q-one-core#1](https://github.com/aidless/q-one-core/pull/1) was still open and unmerged on 2026-11-16.
- `q-one-agent` owns routing, provider adapters, evidence capture, and recommendation formatting.
- [`q-one-life`](https://github.com/aidless/q-one-life) owns the personal application. Its honesty pull request [q-one-life#1](https://github.com/aidless/q-one-life/pull/1) was still open and unmerged on 2026-11-16.

## Quick start

Python 3.10 or newer. The only install dependency is `httpx`. After that install, `make check` does not need network access. On Debian and Ubuntu, `python3 -m venv` needs the distro package `python3-venv` before the commands below work. GitHub Actions' `setup-python` image already provides it.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
qone-agent providers
qone-agent recommend --decision-file examples/agent_input.json
make check
```

Observed on 2026-11-16 on this change's machine (Python 3.12.3, fresh venv, `pip install -e .`). This is the deterministic CLI demo, not a model call:

```text
$ qone-agent providers
cost-heuristic-v0.1
```

`qone-agent recommend --decision-file examples/agent_input.json` printed a recommendation with `option_id` `meeting`, `source` `cost-heuristic-v0.1`, `requires_human` true, `auto_eligible` false, and `success_probability` null. Re-run the command to see the full JSON. The same shape is stored under `cli_heuristic_demo` in `eval/fault-matrix.json`.

## What this does not prove

Planned comparisons C1–C3 in [PREREG.md](PREREG.md) have not been run. [docs/MODEL_RESEARCH.md](docs/MODEL_RESEARCH.md) records no live call. There is no accuracy, calibration, user, or adoption number. Laya weights and PyTorch are not in the base install (`pip install '.[laya]'` only names the optional dependency).

`python3 eval/run_cases.py` recomputes the executable acceptance cases. `python3 eval/run_cases.py --selftest` must go red.

## GitHub About

This commit does not change the GitHub About field. On 2026-11-16 that field was: "Provider-neutral orchestration for the Q-One decision protocol". It does not state the limits above.

About replacement: Routes one structured decision to a provider and returns a human-reviewed recommendation for q-one-core. It does not write the human decision or mark a recommendation safe for automatic execution. The CLI demo is cost-heuristic-v0.1. No live-provider result is stored in this repository.

This repository is MIT licensed. Failure modes: [FAILURE_MODES.md](FAILURE_MODES.md).
