"""`hanlint rules`. 규칙 이름과 한 줄 설명. 규칙 목록의 정본이다.

부류로 묶어 보인다. 쉰 줄을 한 덩어리로 쏟으면 무엇을 고를지 정할 수 없다. 부류는 규칙 파일이 사는
폴더가 정본이고 (`ruleCategory`) 이름은 `CATEGORY_TITLES` 가 든다.
"""

from __future__ import annotations

import argparse

from ...config import PRESETS
from ...rules import CATEGORY_TITLES, ruleCategories, ruleNames, ruleSummary
from .shared import addCommonOptions, configFrom

HELP = "규칙 이름과 한 줄 설명을 부류별로 나열한다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--names", action="store_true", help="이름만. 스크립트가 읽는 꼴이다")
    addCommonOptions(parser, ("text",))


def run(args: argparse.Namespace) -> int:
    names = ruleNames()
    if args.names:
        print("\n".join(names))
        return 0
    config = configFrom(args)
    off = set(config.offRules())
    categories = ruleCategories()
    width = max(len(name) for name in names)
    for category, title in CATEGORY_TITLES.items():
        inside = [name for name in names if categories[name] == category]
        if not inside:
            continue
        print(f"{title} ({len(inside)})")
        for name in inside:
            mark = " (꺼짐)" if name in off else ""
            print(f"  {name:<{width}}  {ruleSummary(name)}{mark}")
        print()
    tail = f"규칙 {len(names)}개"
    if off:
        byPreset = len(PRESETS[config.preset])
        source = f"preset {config.preset} 이 {byPreset}개, disable 이 {len(off) - byPreset}개"
        tail += f", 그중 {len(off)}개가 꺼져 있다 ({source})"
    print(f"{tail}. 하나를 자세히 보려면 hanlint explain <규칙>")
    print(f"프리셋은 {', '.join(PRESETS)} 이고 hanlint init --preset <이름> 이 설정에 적는다")
    return 0
