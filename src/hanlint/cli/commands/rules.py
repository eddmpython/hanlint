"""`hanlint rules`. 규칙 이름과 한 줄 설명. 규칙 목록의 정본이다."""

from __future__ import annotations

import argparse

from ...rules import ruleNames, ruleSummary

HELP = "규칙 이름과 한 줄 설명을 나열한다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--names", action="store_true", help="이름만")


def run(args: argparse.Namespace) -> int:
    names = ruleNames()
    if args.names:
        print("\n".join(names))
        return 0
    width = max(len(name) for name in names)
    for name in names:
        print(f"{name:<{width}}  {ruleSummary(name)}")
    print(f"\n규칙 {len(names)}개. 자세히 보려면 hanlint explain <규칙>")
    return 0
