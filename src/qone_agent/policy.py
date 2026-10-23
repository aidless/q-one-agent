"""Human-review policy applied before an agent recommendation is emitted."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import DecisionContext


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    reasons: tuple[str, ...]
    requires_human: bool = True


def evaluate(decision: DecisionContext, confidence: float, personal_calibration_n: int) -> PolicyResult:
    reasons: list[str] = []
    if confidence < 0.70:
        reasons.append("low_confidence")
    if decision.risk == "high":
        reasons.append("high_risk")
    if not decision.reversible:
        reasons.append("irreversible")
    if personal_calibration_n < 20:
        reasons.append("insufficient_personal_calibration")
    return PolicyResult(True, tuple(reasons))
