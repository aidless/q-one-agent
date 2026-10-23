# Adapter contract

The adapter boundary is intentionally small so providers can be replaced without rewriting the core ledger.

## Input

`DecisionContext` contains the question, domain, criterion, deadline, reversibility, risk, options, and the human baseline. The baseline is mandatory. A provider may use `context`, but the context is marked as user-supplied unless a separate evidence adapter verifies it.

## Output

`ProviderResult` contains:

- `option_id`: one of the declared option IDs
- `confidence`: preference strength in `[0, 1]`
- `success_probability`: optional probability for the declared criterion in `[0, 1]`
- `rationale`: a short, criterion-linked explanation
- `source`: immutable provider and version identifier

The engine adds gate reasons and the human-review flags. A provider cannot set `auto_eligible=true`.

## Failure behavior

Adapters should fail closed when the decision is malformed, the option is unknown, or evidence is unavailable. Do not substitute a guessed option silently. A failed run should be preserved by the caller as a run record with an error and provider version.

## Model providers

Hosted APIs and local open-source checkpoints belong in separate adapter modules. Store model name, revision or digest, prompt template version, sampling parameters, tool permissions, and retrieval sources in the run metadata. Never treat a model's self-reported confidence as calibration evidence.
