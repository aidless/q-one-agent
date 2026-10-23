"""A deterministic, deliberately uncalibrated local provider for smoke use."""

from __future__ import annotations

from ..contracts import DecisionContext
from ..evidence import EvidenceBundle
from .base import ProviderResult


class CostHeuristicProvider:
    name = "cost-heuristic-v0.1"

    def recommend(self, decision: DecisionContext, evidence: EvidenceBundle) -> ProviderResult:
        del evidence
        ordered = sorted(decision.options, key=lambda option: (option.expected_cost_hours, option.id))
        selected = ordered[0]
        tied = len(ordered) > 1 and ordered[0].expected_cost_hours == ordered[1].expected_cost_hours
        confidence = 0.50 if tied else 0.55
        rationale = (
            "Selected the option with the lowest declared expected cost. "
            "This provider is a deterministic heuristic and has no calibration evidence."
        )
        return ProviderResult(
            option_id=selected.id,
            confidence=confidence,
            success_probability=None,
            rationale=rationale,
            source=self.name,
        )
