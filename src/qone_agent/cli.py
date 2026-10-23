"""CLI for provider-neutral Q-One recommendations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .engine import AgentEngine
from .providers import CostHeuristicProvider


def _load(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("decision file must contain a JSON object")
    return value


def cmd_providers(args: argparse.Namespace) -> int:
    del args
    print(CostHeuristicProvider.name)
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    decision = _load(args.decision_file)
    recommendation, evidence = AgentEngine().recommend(
        raw_decision=decision,
        provider_name=args.provider,
        personal_calibration_n=args.personal_calibration_n,
    )
    print(
        json.dumps(
            {"recommendation": recommendation.to_dict(), "evidence": evidence.to_dict()},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="qone-agent", description="Q-One provider-neutral agent")
    commands = root.add_subparsers(dest="command", required=True)

    command = commands.add_parser("providers", help="list local providers")
    command.set_defaults(handler=cmd_providers)

    command = commands.add_parser("recommend", help="emit a core-compatible recommendation")
    command.add_argument("--decision-file", required=True)
    command.add_argument("--provider", default=CostHeuristicProvider.name)
    command.add_argument("--personal-calibration-n", type=int, default=0)
    command.set_defaults(handler=cmd_recommend)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
