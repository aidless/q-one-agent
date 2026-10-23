"""Small, dependency-free contract shared with q-one-core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ContractError(ValueError):
    """Raised when an agent input or output is not protocol-compatible."""


@dataclass(frozen=True)
class Option:
    id: str
    label: str
    expected_cost_hours: float = 0.0
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Option":
        option_id = raw.get("id")
        label = raw.get("label")
        if not isinstance(option_id, str) or not option_id.strip():
            raise ContractError("option.id must be a non-empty string")
        if not isinstance(label, str) or not label.strip():
            raise ContractError("option.label must be a non-empty string")
        cost = raw.get("expected_cost_hours", 0)
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
            raise ContractError("option.expected_cost_hours must be non-negative")
        return cls(option_id.strip(), label.strip(), float(cost), str(raw.get("notes", "")))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "expected_cost_hours": self.expected_cost_hours,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class DecisionContext:
    decision_id: str
    question: str
    domain: str
    success_criterion: str
    deadline: str
    reversible: bool
    risk: str
    options: tuple[Option, ...]
    baseline_option_id: str
    baseline_note: str = ""
    context: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DecisionContext":
        if not isinstance(raw, dict) or not isinstance(raw.get("options"), list):
            raise ContractError("decision.options must be a list of option objects")
        try:
            options = tuple(Option.from_dict(item) for item in raw["options"])
        except (KeyError, TypeError, AttributeError) as exc:
            raise ContractError("decision.options must be a list of option objects") from exc
        ids = {option.id for option in options}
        if len(options) < 2 or len(options) > 8 or len(ids) != len(options):
            raise ContractError("decision must have 2-8 unique options")
        baseline = raw.get("baseline") or {}
        if not isinstance(baseline, dict):
            raise ContractError("decision.baseline must be an object")
        baseline_id = baseline.get("option_id")
        if baseline_id not in ids:
            raise ContractError("a baseline option from the decision is required")
        required = ["decision_id", "question", "domain", "success_criterion", "deadline"]
        if any(not isinstance(raw.get(key), str) or not raw[key].strip() for key in required):
            raise ContractError("decision metadata fields must be non-empty strings")
        if raw.get("risk", "medium") not in {"low", "medium", "high"}:
            raise ContractError("decision.risk must be low, medium, or high")
        if not isinstance(raw.get("reversible"), bool):
            raise ContractError("decision.reversible must be boolean")
        return cls(
            decision_id=raw["decision_id"],
            question=raw["question"].strip(),
            domain=raw["domain"].strip(),
            success_criterion=raw["success_criterion"].strip(),
            deadline=raw["deadline"].strip(),
            reversible=raw["reversible"],
            risk=raw.get("risk", "medium"),
            options=options,
            baseline_option_id=baseline_id,
            baseline_note=str(baseline.get("note", "")),
            context=str(raw.get("context", "")),
        )


@dataclass(frozen=True)
class Recommendation:
    decision_id: str
    option_id: str
    confidence: float
    success_probability: float | None
    rationale: str
    source: str
    gate_reasons: tuple[str, ...]
    requires_human: bool = True
    auto_eligible: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "option_id": self.option_id,
            "confidence": self.confidence,
            "success_probability": self.success_probability,
            "rationale": self.rationale,
            "source": self.source,
            "gate_reasons": list(self.gate_reasons),
            "requires_human": self.requires_human,
            "auto_eligible": self.auto_eligible,
        }


def make_recommendation(
    decision: DecisionContext,
    option_id: str,
    confidence: float,
    success_probability: float | None,
    rationale: str,
    source: str,
    gate_reasons: tuple[str, ...],
) -> Recommendation:
    option_ids = {option.id for option in decision.options}
    if option_id not in option_ids:
        raise ContractError("recommendation.option_id is not a decision option")
    if not 0 <= confidence <= 1:
        raise ContractError("recommendation.confidence must be between 0 and 1")
    if success_probability is not None and not 0 <= success_probability <= 1:
        raise ContractError("recommendation.success_probability must be between 0 and 1")
    if not rationale.strip() or not source.strip():
        raise ContractError("recommendation rationale and source are required")
    return Recommendation(
        decision_id=decision.decision_id,
        option_id=option_id,
        confidence=float(confidence),
        success_probability=success_probability,
        rationale=rationale.strip(),
        source=source.strip(),
        gate_reasons=gate_reasons,
    )
