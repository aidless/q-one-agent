"""Evidence records carried alongside a recommendation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceItem:
    kind: str
    locator: str
    excerpt: str = ""
    observed_at: str = ""
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBundle:
    items: tuple[EvidenceItem, ...] = ()
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "limitations": list(self.limitations),
        }


def local_context(text: str, source: str = "user_context") -> EvidenceBundle:
    """Represent supplied context without pretending it is independently verified."""
    if not text.strip():
        return EvidenceBundle(limitations=("empty_context",))
    return EvidenceBundle(
        items=(EvidenceItem(kind="user_supplied", locator=source, excerpt=text.strip()),),
        limitations=("user_supplied_context_not_independently_verified",),
    )
