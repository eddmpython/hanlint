"""`hanlint explain <규칙>`. 규칙의 기술서. docstring 을 그대로 보여 준다.

이름을 안 주면 어디서 목록을 보는지 알려 주고, 오타면 가까운 이름을 먼저 보인다. 규칙 이름을 외우고
있어야 쓸 수 있는 도구는 처음 쓰는 사람에게 닫혀 있다.
"""

from __future__ import annotations

import argparse
import json

from ...analysis.grammar import HAPNIDA, REGISTERS
from ...data import exemplarFor, patternsAvoiding
from ...report import exemplarInRegister, patternInRegister
from ...rules import CATEGORY_TITLES, ruleCategory, ruleDoc, ruleNames
from .shared import addOutputOption, emit

ISSUES = "github.com/eddmpython/hanlint/issues"
"""오탐과 미탐을 받는 자리. 끄는 것은 그 저장소에서만 조용해지고 규칙은 그대로 틀린 채 남는다."""

HELP = "규칙 하나의 기술서를 보여 준다. 왜 나쁜지, 어디서 왔는지, 어떻게 고치는지"
NEAR_LIMIT = 3
"""가까운 이름을 몇 개까지 보이는가. 넷을 넘으면 목록을 보는 것이 낫다."""
PREFIX = 3
"""앞 몇 글자가 같으면 가까운 이름으로 보는가."""


def indent(text: str, label: str) -> str:
    """여러 줄짜리 본보기를 첫 줄에만 표를 달고 나머지는 맞춰 들여쓴다."""
    pad = " " * len(label)
    lines = text.rstrip("\n").split("\n")
    return "\n".join((label if index == 0 else pad) + line for index, line in enumerate(lines))


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("rule", nargs="?", help="규칙 이름. hanlint rules 로 목록을 본다")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="출력 꼴. 기본 text")
    parser.add_argument("--register", choices=REGISTERS, default=HAPNIDA, help="본보기 문체. 기본 합니다체")
    addOutputOption(parser)


def asJson(rule: str, register: str = HAPNIDA) -> str:
    """규칙 하나를 기계가 읽는 꼴로. 기술서와 본보기와 다시 쓸 틀을 한 덩어리로 준다."""
    exemplar = exemplarFor(rule)
    data: dict = {
        "version": 1,
        "rule": rule,
        "category": ruleCategory(rule),
        "doc": ruleDoc(rule),
    }
    if exemplar:
        data["exemplar"] = exemplarInRegister(exemplar, register).asDict()
    patterns = [patternInRegister(pattern, register) for pattern in patternsAvoiding(rule)]
    if patterns:
        data["patterns"] = [p.asDict() for p in patterns]
    return json.dumps(data, ensure_ascii=False, indent=2)


def nearNames(query: str, names: list[str]) -> list[str]:
    """오타에 가까운 이름. 부분 문자열이 먼저, 앞 글자가 같은 것이 다음이다. 이름 순으로 끊는다."""
    lowered = query.lower()
    scored: list[tuple[int, str]] = []
    for name in names:
        low = name.lower()
        if lowered in low or low in lowered:
            scored.append((0, name))
        elif low[:PREFIX] == lowered[:PREFIX]:
            scored.append((1, name))
    return [name for _, name in sorted(scored)][:NEAR_LIMIT]


def run(args: argparse.Namespace) -> int:
    names = ruleNames()
    if not args.rule:
        print("규칙 이름 하나가 필요하다. 예: hanlint explain doublePassive")
        print(f"\n규칙 {len(names)}개를 부류로 묶어 보려면 hanlint rules, 이름만 보려면 hanlint rules --names")
        return 2
    if args.rule not in names:
        near = nearNames(args.rule, names)
        hint = f" 이것을 찾았나: {', '.join(near)}" if near else " hanlint rules 로 목록을 본다"
        raise KeyError(f"모르는 규칙: {args.rule}.{hint}")
    if args.format == "json":
        emit(asJson(args.rule, args.register), args.output)
        return 0
    category = ruleCategory(args.rule)
    print(f"{args.rule}  ({CATEGORY_TITLES[category]})\n")
    print(ruleDoc(args.rule))
    exemplar = exemplarFor(args.rule)
    if exemplar:
        exemplar = exemplarInRegister(exemplar, args.register)
        print("\n본보기")
        print(indent(exemplar.before, "  전  "))
        print(indent(exemplar.after, "  후  "))
        print(f"  달라진 것: {exemplar.moved}")
    print(f"\n같은 부류: {', '.join(n for n in names if ruleCategory(n) == category and n != args.rule)}")
    print(f"끄려면 hanlint.toml 의 disable 에 {args.rule} 를 넣는다. 한 자리만 끄려면 <!-- hanlint-disable {args.rule} -->")
    print(f"정당한 문장인데 잡혔으면 끄고 끝내지 말고 알려 준다: {ISSUES}")
    return 0
