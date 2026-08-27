"""`hanlint explain <규칙>`. 규칙의 기술서. docstring 을 그대로 보여 준다."""

from __future__ import annotations

import argparse

from ...rules import ruleDoc, ruleNames

HELP = "규칙 하나의 기술서를 보여 준다. 왜 나쁜지, 어디서 왔는지, 어떻게 고치는지"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("rule", help="규칙 이름. hanlint rules 로 목록을 본다")


def run(args: argparse.Namespace) -> int:
    if args.rule not in ruleNames():
        raise KeyError(f"모르는 규칙: {args.rule}. hanlint rules 로 목록을 본다")
    print(f"{args.rule}\n")
    print(ruleDoc(args.rule))
    return 0
