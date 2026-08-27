"""`hanlint rules`. 규칙 이름과 한 줄 설명. 규칙 목록의 정본이다.

부류로 묶어 보인다. 쉰 줄을 한 덩어리로 쏟으면 무엇을 고를지 정할 수 없다. 부류는 규칙 파일이 사는
폴더가 정본이고 (`ruleCategory`) 이름은 `CATEGORY_TITLES` 가 든다.
"""

from __future__ import annotations

import argparse
import json

from ...config import PRESETS
from ...data import exemplarFor
from ...rules import CATEGORY_TITLES, ruleCategories, ruleDoc, ruleNames, ruleSummary
from .shared import addCommonOptions, configFrom, emit

HELP = "규칙 이름과 한 줄 설명을 부류별로 나열한다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--names", action="store_true", help="이름만. 스크립트가 읽는 꼴이다")
    addCommonOptions(parser, ("text", "json"))


def asJson(names: list[str], off: set[str]) -> str:
    """규칙 전부를 기계가 읽는 꼴로. 기술서와 본보기까지 든다. 에이전트가 규칙을 훑을 때 쓴다."""
    categories = ruleCategories()
    rules = []
    for name in names:
        exemplar = exemplarFor(name)
        entry: dict = {
            "name": name,
            "category": categories[name],
            "summary": ruleSummary(name),
            "doc": ruleDoc(name),
            "enabled": name not in off,
        }
        if exemplar:
            entry["exemplar"] = exemplar.asDict()
        rules.append(entry)
    return json.dumps({"version": 1, "rules": rules}, ensure_ascii=False, indent=2)


def run(args: argparse.Namespace) -> int:
    names = ruleNames()
    if args.names:
        emit("\n".join(names), args.output)
        return 0
    config = configFrom(args)
    if args.format == "json":
        emit(asJson(names, set(config.offRules())), args.output)
        return 0
    off = set(config.offRules())
    categories = ruleCategories()
    width = max(len(name) for name in names)
    lines: list[str] = []
    for category, title in CATEGORY_TITLES.items():
        inside = [name for name in names if categories[name] == category]
        if not inside:
            continue
        lines.append(f"{title} ({len(inside)})")
        for name in inside:
            mark = " (꺼짐)" if name in off else ""
            lines.append(f"  {name:<{width}}  {ruleSummary(name)}{mark}")
        lines.append("")
    tail = f"규칙 {len(names)}개"
    if off:
        byPreset = len(PRESETS[config.preset])
        source = f"preset {config.preset} 이 {byPreset}개, disable 이 {len(off) - byPreset}개"
        tail += f", 그중 {len(off)}개가 꺼져 있다 ({source})"
    lines.append(f"{tail}. 하나를 자세히 보려면 hanlint explain <규칙>")
    lines.append(f"프리셋은 {', '.join(PRESETS)} 이고 hanlint init --preset <이름> 이 설정에 적는다")
    emit("\n".join(lines), args.output)
    return 0
