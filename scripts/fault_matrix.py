#!/usr/bin/env python3
"""Print the adapter × fault matrix and optionally compare it to the committed file."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from fault_matrix_lib import REPORT_PATH, build_report, dump_report, render_matrix


def main(argv: list[str]) -> int:
    report = build_report()
    text = dump_report(report)
    print(render_matrix(report))
    if "--write" in argv:
        REPORT_PATH.write_text(text, encoding="utf-8")
        print(f"wrote {REPORT_PATH}")
    if "--check" in argv:
        if not REPORT_PATH.is_file():
            print(f"missing {REPORT_PATH}", file=sys.stderr)
            return 1
        if REPORT_PATH.read_text(encoding="utf-8") != text:
            print("fault matrix drift: eval/fault-matrix.json does not match a fresh run", file=sys.stderr)
            return 1
        print("fault matrix ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
