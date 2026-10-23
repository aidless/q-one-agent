"""Recommendation orchestration and provider routing."""

from __future__ import annotations

from typing import Any

from .contracts import DecisionContext, Recommendation, make_recommendation
from .evidence import EvidenceBundle, local_context
from .policy import evaluate
from .providers import CostHeuristicProvider, Provider


class AgentEngine:
    def __init__(self, providers: dict[str, Provider] | None = None):
        self.providers = providers or {CostHeuristicProvider.name: CostHeuristicProvider()}

    def recommend(
        self,
        raw_decision: dict[str, Any],
        provider_name: str = CostHeuristicProvider.name,
        personal_calibration_n: int = 0,
        evidence: EvidenceBundle | None = None,
    ) -> tuple[Recommendation, EvidenceBundle]:
        decision = DecisionContext.from_dict(raw_decision)
        try:
            provider = self.providers[provider_name]
        except KeyError as exc:
            raise ValueError(f"unknown provider: {provider_name}") from exc
        bundle = evidence or local_context(decision.context)
        result = provider.recommend(decision, bundle)
        policy = evaluate(decision, result.confidence, personal_calibration_n)
        recommendation = make_recommendation(
            decision=decision,
            option_id=result.option_id,
            confidence=result.confidence,
            success_probability=result.success_probability,
            rationale=result.rationale,
            source=result.source,
            gate_reasons=policy.reasons,
        )
        return recommendation, bundle
