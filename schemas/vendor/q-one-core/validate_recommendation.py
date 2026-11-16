# Vendored excerpt from aidless/q-one-core src/qone_core/models.py
# commit 2d243b33c0beede7cf05d1ab2212f5fb45d39c6a (2026-11-14T09:08:04Z)
# blob 23fb7248e3c2623ba79e5d4762403abe8545a590
# symbols: ValidationError, _text, _probability, validate_recommendation
# q-one-core does not publish a recommendation JSON Schema file.
# The lines below are the validator, copied without behavior changes.
# Header comments are not part of the upstream file.

from __future__ import annotations

from typing import Any


class ValidationError(ValueError):
    """Raised when a decision or event payload violates the protocol."""


def _text(value: Any, field: str, *, required: bool = True) -> str | None:
    if not required and (value is None or (isinstance(value, str) and not value.strip())):
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _probability(value: Any, field: str, *, required: bool = True) -> float | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field} must be a number between 0 and 1")
    result = float(value)
    if not 0 <= result <= 1:
        raise ValidationError(f"{field} must be a number between 0 and 1")
    return result


def validate_recommendation(raw: Any, option_ids: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValidationError("recommendation must be an object")
    option_id = _text(raw.get("option_id"), "recommendation.option_id")
    if option_id not in option_ids:
        raise ValidationError("recommendation.option_id is not a decision option")
    confidence = _probability(raw.get("confidence"), "recommendation.confidence")
    success_probability = _probability(
        raw.get("success_probability"),
        "recommendation.success_probability",
        required=False,
    )
    return {
        "option_id": option_id,
        "confidence": confidence,
        "success_probability": success_probability,
        "rationale": _text(raw.get("rationale"), "recommendation.rationale"),
        "source": _text(raw.get("source"), "recommendation.source"),
        "gate_reasons": list(raw.get("gate_reasons", [])),
        "requires_human": True,
        "auto_eligible": False,
    }
