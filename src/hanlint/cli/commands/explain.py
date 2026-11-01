"""`hanlint explain <규칙>`. 규칙의 기술서. docstring을 그대로 보여 준다.

이름을 안 주면 어디서 목록을 보는지 알려 주고, 오타면 가까운 이름을 먼저 보인다. 규칙 이름을 외우고
있어야 쓸 수 있는 도구는 처음 쓰는 사람에게 닫혀 있다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...analysis.grammar import HAPNIDA, REGISTERS
from ...config import PRESET_NAMES
from ...data import exemplarFor, patternsAvoiding
from ...report import exemplarInRegister, patternInRegister
from ...rules import CATEGORY_TITLES, MECHANISMS, ruleCategory, ruleDoc, ruleMechanism, ruleNames
from .shared import addOutputOption, configFrom, emit

ISSUES = "github.com/eddmpython/hanlint/issues"
"""오탐과 미탐을 받는 자리. 끄는 것은 그 저장소에서만 조용해지고 규칙은 그대로 틀린 채 남는다."""

HELP = "규칙 하나의 설명을 보여 준다. 왜 나쁜지, 어디서 왔는지, 어떻게 고치는지"
NEAR_LIMIT = 3
"""가까운 이름을 몇 개까지 보이는가. 넷을 넘으면 목록을 보는 것이 낫다."""
PREFIX = 3
"""앞 몇 글자가 같으면 가까운 이름으로 보는가."""


def indent(text: str, label: str) -> str:
    """여러 줄짜리 예시를 첫 줄에만 표를 달고 나머지는 맞춰 들여쓴다."""
    pad = " " * len(label)
    lines = text.rstrip("\n").split("\n")
    return "\n".join((label if index == 0 else pad) + line for index, line in enumerate(lines))


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("rule", nargs="?", help="규칙 이름. hanlint rules로 목록을 본다")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="출력 형식. 기본 text")
    parser.add_argument("--register", choices=REGISTERS, default=HAPNIDA, help="예시 문체. 기본 합니다체")
    parser.add_argument("--config", type=Path, help="설정 파일. 프로젝트 예시를 함께 읽는다")
    parser.add_argument("--preset", choices=PRESET_NAMES, help="예시의 글 종류. 기본은 설정이나 blog")
    addOutputOption(parser)


def asJson(rule: str, register: str = HAPNIDA, preset: str = "blog", customExemplars=()) -> str:
    """규칙 하나를 기계가 읽는 형식으로. 기술서와 예시와 다시 쓸 틀을 한 덩어리로 준다."""
    exemplar = exemplarFor(rule, preset, customExemplars)
    data: dict = {
        "version": 1,
        "rule": rule,
        "category": ruleCategory(rule),
        "mechanism": ruleMechanism(rule),
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
        print(f"\n규칙 {len(names)}개를 묶음별로 보려면 hanlint rules, 이름만 보려면 hanlint rules --names")
        return 2
    if args.rule not in names:
        near = nearNames(args.rule, names)
        hint = f" 비슷한 이름: {', '.join(near)}" if near else " 목록은 hanlint rules"
        raise KeyError(f"없는 규칙: {args.rule}.{hint}")
    config = configFrom(args)
    if args.format == "json":
        emit(asJson(args.rule, args.register, config.preset, config.exemplars), args.output)
        return 0
    category = ruleCategory(args.rule)
    mechanism = ruleMechanism(args.rule)
    print(f"{args.rule}  ({CATEGORY_TITLES[category]})")
    print(f"찾는 방법: {MECHANISMS[mechanism]} ({mechanism})\n")
    print(ruleDoc(args.rule))
    exemplar = exemplarFor(args.rule, config.preset, config.exemplars)
    if exemplar:
        exemplar = exemplarInRegister(exemplar, args.register)
        print("\n예시")
        print(indent(exemplar.before, "  전  "))
        print(indent(exemplar.after, "  후  "))
        print(f"  달라진 것: {exemplar.moved}")
    print(f"\n같은 묶음: {', '.join(n for n in names if ruleCategory(n) == category and n != args.rule)}")
    print(f"끄려면 hanlint.toml의 disable 목록에 넣는다: {args.rule}. 한 곳만 끄려면 <!-- hanlint-disable {args.rule} -->")
    print(f"맞는 문장인데 잡혔다면 끄기만 하지 말고 여기에 알린다: {ISSUES}")
    return 0
