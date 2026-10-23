"""Provider interface; concrete model integrations belong behind this boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..contracts import DecisionContext
from ..evidence import EvidenceBundle


@dataclass(frozen=True)
class ProviderResult:
    option_id: str
    confidence: float
    success_probability: float | None
    rationale: str
    source: str


class Provider(Protocol):
    name: str

    def recommend(self, decision: DecisionContext, evidence: EvidenceBundle) -> ProviderResult:
        ...
