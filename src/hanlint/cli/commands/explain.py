"""`hanlint explain <규칙>`. 규칙의 기술서. docstring 을 그대로 보여 준다.

이름을 안 주면 어디서 목록을 보는지 알려 주고, 오타면 가까운 이름을 먼저 보인다. 규칙 이름을 외우고
있어야 쓸 수 있는 도구는 처음 쓰는 사람에게 닫혀 있다.
"""

from __future__ import annotations

import argparse

from ...rules import CATEGORY_TITLES, ruleCategory, ruleDoc, ruleNames

HELP = "규칙 하나의 기술서를 보여 준다. 왜 나쁜지, 어디서 왔는지, 어떻게 고치는지"
NEAR_LIMIT = 3
"""가까운 이름을 몇 개까지 보이는가. 넷을 넘으면 목록을 보는 것이 낫다."""
PREFIX = 3
"""앞 몇 글자가 같으면 가까운 이름으로 보는가."""


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("rule", nargs="?", help="규칙 이름. hanlint rules 로 목록을 본다")


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
    category = ruleCategory(args.rule)
    print(f"{args.rule}  ({CATEGORY_TITLES[category]})\n")
    print(ruleDoc(args.rule))
    print(f"\n같은 부류: {', '.join(n for n in names if ruleCategory(n) == category and n != args.rule)}")
    print(f"끄려면 hanlint.toml 의 disable 에 {args.rule} 를 넣는다. 한 자리만 끄려면 <!-- hanlint-disable {args.rule} -->")
    return 0
