"""`hanlint primer`. 글을 쓰기 전에 읽는 한 장. 켜진 규칙마다 고치는 법과 본보기 전후 한 쌍.

`explain` 은 규칙 하나를 깊게, `rules` 는 목록을, `primer` 는 쓰기 전의 AI 와 사람이 한 번에 읽는 한 장을 준다.
손으로 쓴 문장은 없다. 규칙 docstring 의 고치기 절과 exemplars 를 등록부 순서대로 결정적으로 늘어놓는다. 그래서
규칙이 바뀌면 이 장도 같이 바뀐다. 후는 게이트가 error 0 을 보장한다 (tests/gates/testPrimer.py).

한 장은 세션 앞머리에 얹는 자리라 줄 수가 자리세다. 규칙 하나가 한 줄이고 어느 프리셋과 문체에서도 LINE_LIMIT
안이다. 문장 규칙의 본보기는 원래 한 줄이고 절과 문단을 보이는 본보기는 줄바꿈을 ¶ 로 눕혀 한 줄로 보인다. 항목과
JSON 은 본보기 원문을 그대로 들어 hanlint 가 보는 글과 같다.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from ...analysis.grammar import HAPNIDA, REGISTERS
from ...config import Config
from ...data import exemplarFor
from ...report import exemplarInRegister
from ...rules import CATEGORY_TITLES, ruleCategories, ruleFix, ruleNames
from .shared import addCommonOptions, configFrom, emit

HELP = "쓰기 전에 읽는 한 장. 켜진 규칙마다 고치는 법과 본보기 전후"
LINE_LIMIT = 100
"""한 장의 줄 수 상한. 규칙 50개가 전부 켜진 blog 도 이 안에 들어야 한다. 게이트가 모든 프리셋과 문체에서 잰다."""


@dataclass(frozen=True)
class PrimerEntry:
    """한 장의 한 줄. 규칙 하나와 그 고치는 법과 본보기 전후."""

    rule: str
    category: str
    fix: str
    """docstring 의 고치기 절을 한 줄로."""
    before: str
    """그 규칙에 잡히는 글. 본보기 원문 그대로다."""
    after: str
    """같은 뜻으로 통과하는 글."""

    def asDict(self) -> dict:
        """JSON 항목."""
        return {"rule": self.rule, "category": self.category, "fix": self.fix, "before": self.before, "after": self.after}


def flat(text: str) -> str:
    """여러 줄을 한 줄로. 줄 안의 공백은 하나로, 줄바꿈은 ¶ 로 보여 절과 문단을 보이는 본보기가 한 줄에서도 읽힌다."""
    return " ¶ ".join(" ".join(line.split()) for line in text.split("\n") if line.strip())


def addParser(parser: argparse.ArgumentParser) -> None:
    """본보기 문체와 공용 옵션."""
    parser.add_argument("--register", choices=REGISTERS, default=HAPNIDA, help="본보기 문체. 기본 합니다체")
    addCommonOptions(parser, ("text", "json"))


def primerEntries(config: Config, register: str = HAPNIDA) -> list[PrimerEntry]:
    """설정에서 켜진 규칙마다 항목 하나. 부류 순서, 그 안은 이름 순서다."""
    off = set(config.offRules())
    categories = ruleCategories()
    entries: list[PrimerEntry] = []
    for category in CATEGORY_TITLES:
        for name in ruleNames():
            if categories[name] != category or name in off:
                continue
            exemplar = exemplarFor(name, config.preset, config.exemplars)
            if exemplar is None:
                raise LookupError(f"본보기가 없는 규칙: {name}")
            shown = exemplarInRegister(exemplar, register)
            entries.append(PrimerEntry(name, category, ruleFix(name), shown.before, shown.after))
    return entries


def renderPrimer(entries: list[PrimerEntry], preset: str, register: str) -> str:
    """사람과 AI 가 읽는 한 장. 첫 줄이 읽는 법, 부류마다 제목 하나, 규칙 하나가 한 줄이다."""
    lines = [
        f"hanlint primer  {preset} 종류, {register}체, 규칙 {len(entries)}개. "
        "줄마다 규칙 이름, 고치는 법, 전 (그 규칙에 잡히는 글), 후 (같은 뜻으로 통과하는 글) 순서다. 본보기의 줄바꿈은 ¶ 다"
    ]
    for category, title in CATEGORY_TITLES.items():
        inside = [entry for entry in entries if entry.category == category]
        if not inside:
            continue
        lines.append("")
        lines.append(f"{title} ({len(inside)})")
        lines.extend(f"{entry.rule}  {entry.fix}  전: {flat(entry.before)}  후: {flat(entry.after)}" for entry in inside)
    lines.append("")
    lines.append("후는 전부 hanlint 를 error 0 으로 통과한다 (게이트가 확인한다). 규칙 하나를 깊게 보려면 hanlint explain <규칙>")
    return "\n".join(lines)


def asJson(entries: list[PrimerEntry], preset: str, register: str) -> str:
    """기계가 읽는 꼴. 항목마다 규칙, 부류, 고치는 법, 전, 후다."""
    data = {"version": 1, "preset": preset, "register": register, "rules": [entry.asDict() for entry in entries]}
    return json.dumps(data, ensure_ascii=False, indent=2)


def run(args: argparse.Namespace) -> int:
    """설정의 프리셋과 disable 에서 켜진 규칙으로 한 장을 낸다."""
    config = configFrom(args)
    entries = primerEntries(config, args.register)
    if args.format == "json":
        emit(asJson(entries, config.preset, args.register), args.output)
        return 0
    emit(renderPrimer(entries, config.preset, args.register), args.output)
    return 0
