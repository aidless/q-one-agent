#!/usr/bin/env python3
"""Fail when README copies, version pins, or CI drift apart. Offline."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SHARED = (
    "STATUS: WORK-IN-PROGRESS — not A yet",
    "cost-heuristic-v0.1",
    "2d243b33c0beede7cf05d1ab2212f5fb45d39c6a",
    "1720e3e3357cfe1e281542e223f8273b0890ca34",
    "qwen3:8b",
    "make check",
    "RunResult.receipt()",
    "httpx.MockTransport",
    "eval/fault-matrix.json",
    "D-20261023-example",
    "About replacement: Routes one structured decision to a provider and returns a human-reviewed recommendation for q-one-core. It does not write the human decision or mark a recommendation safe for automatic execution. The CLI demo is cost-heuristic-v0.1. No live-provider result is stored in this repository.",
)
EN_ONLY = (
    "This repository contains no saved receipt.",
    "Nothing in this repository records a request that was sent",
    "has not been live-verified",
    "does not publish a recommendation JSON Schema",
    "default model name in code",
)
ZH_ONLY = (
    "本仓库没有保存任何回执。",
    "本仓库没有记录任何一次已经发出的请求",
    "没有做过线上验证",
    "没有发布推荐的 JSON Schema 文件",
    "代码里的默认名字",
)
FORBIDDEN = (
    "real synthetic connectivity receipts",
    "真实的合成连通性",
    "9 passed",
    "no real provider has been integrated",
)


def fail(errors: list[str]) -> int:
    for item in errors:
        print(f"drift: {item}", file=sys.stderr)
    if errors:
        return 1
    print("drift ok")
    return 0


def problem_lines(text: str, heading: str) -> list[str] | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != heading:
            continue
        body: list[str] = []
        for next_line in lines[index + 1 :]:
            if not next_line.strip():
                if body:
                    break
                continue
            if next_line.startswith("#"):
                break
            body.append(next_line)
        return body
    return None


def main() -> int:
    errors: list[str] = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    for needle in SHARED:
        if needle not in readme:
            errors.append(f"README.md missing {needle!r}")
        if needle not in zh:
            errors.append(f"README.zh-CN.md missing {needle!r}")
    for needle in EN_ONLY:
        if needle not in readme:
            errors.append(f"README.md missing {needle!r}")
    for needle in ZH_ONLY:
        if needle not in zh:
            errors.append(f"README.zh-CN.md missing {needle!r}")
    for needle in FORBIDDEN:
        if needle in readme or needle in zh:
            errors.append(f"forbidden phrase still present: {needle!r}")

    for path, heading in ((readme, "## Problem"), (zh, "## 问题")):
        body = problem_lines(path, heading)
        if body is None:
            errors.append(f"missing heading {heading}")
        elif len(body) != 3:
            errors.append(f"{heading} has {len(body)} lines, want 3")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'(?m)^version = "([^"]+)"', pyproject)
    if version_match is None:
        errors.append("pyproject.toml has no version")
        return fail(errors)
    version = version_match.group(1)
    init_text = (ROOT / "src" / "qone_agent" / "__init__.py").read_text(encoding="utf-8")
    if f'__version__ = "{version}"' not in init_text:
        errors.append(f"__init__ version is not {version}")
    manifest = json.loads((ROOT / "research-manifest.json").read_text(encoding="utf-8"))
    if manifest["project"]["version"] != version:
        errors.append(
            f"research-manifest version {manifest['project']['version']} != pyproject {version}"
        )
    prereg = (ROOT / "PREREG.md").read_text(encoding="utf-8")
    for item in manifest["hypotheses"]:
        if item["text"] not in prereg:
            errors.append(f"PREREG.md missing hypothesis {item['id']}")
    if manifest["experiments"]:
        errors.append("research-manifest experiments is not empty; C1–C3 have not been run")
    artifacts = {item["id"]: item for item in manifest["artifacts"]}
    matrix = artifacts.get("A-fault-matrix")
    if not matrix or matrix.get("live_provider") is not False or matrix.get("supports_hypothesis") is not None:
        errors.append("research-manifest artifact A-fault-matrix must be live_provider false and supports_hypothesis null")
    if "STATUS: WORK-IN-PROGRESS — not A yet" not in prereg:
        errors.append("PREREG.md missing STATUS line")

    for relative in (".github/workflows/checks.yml", ".github/workflows/pr-checks.yml"):
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        if "make check" not in workflow:
            errors.append(f"{relative} does not run make check")
        if "|| true" in workflow:
            errors.append(f"{relative} swallows failures with || true")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    if "scripts/check_drift.py" not in makefile or "scripts/fault_matrix.py --check" not in makefile:
        errors.append("Makefile check target is missing drift or fault-matrix")

    modes = (ROOT / "FAILURE_MODES.md").read_text(encoding="utf-8")
    for needle in ("ConnectionRefusedError", "decision_id", "gate_reasons", "About replacement:"):
        if needle not in modes:
            errors.append(f"FAILURE_MODES.md missing {needle}")

    research = (ROOT / "docs" / "MODEL_RESEARCH.md").read_text(encoding="utf-8")
    if "No committed artifact records a live call" not in research:
        errors.append("MODEL_RESEARCH.md does not state that no live call is recorded")
    if "no real provider has been integrated" in research:
        errors.append("MODEL_RESEARCH.md still says no provider has been integrated")
    synthesis = (ROOT / "docs" / "SYNTHESIS_IMPLEMENTATION.zh-CN.md").read_text(encoding="utf-8")
    if "当前运行接口仅包含本地成本启发式" in synthesis:
        errors.append("SYNTHESIS doc still says the runtime is only the cost heuristic")

    report = json.loads((ROOT / "eval" / "run-report.json").read_text(encoding="utf-8"))
    case_lines = [
        line for line in (ROOT / "eval" / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if report.get("passed") != report.get("total") or report.get("total") != len(case_lines):
        errors.append(
            f"eval/run-report.json {report.get('passed')}/{report.get('total')} "
            f"does not match {len(case_lines)} cases"
        )
    return fail(errors)


if __name__ == "__main__":
    raise SystemExit(main())
