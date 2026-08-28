"""`hanlint patterns`. 문형 목록. 빈칸이 있는 문장 틀이다.

규칙은 무엇이 틀렸는지 말하고 본보기는 무엇이 맞는지 보이며 문형은 **다시 쓸 틀**을 준다. 셋이 한 줄에
있다. 지적을 받았는데 어떻게 다시 쓸지 모를 때 `--rule <규칙>` 으로 그 규칙을 피하는 틀만 고른다.

문형마다 `example` 이 error 0 으로 통과하는 것을 게이트가 매번 확인한다. 통과가 보장된 틀이라는 것이
이 명령이 파는 것이다.
"""

from __future__ import annotations

import argparse
import json

from ...analysis.grammar import HAPNIDA, REGISTERS
from ...data import patterns, patternsAvoiding
from ...report import patternInRegister
from .shared import addCommonOptions, emit

HELP = "문장 틀 목록. 지적을 받은 자리를 다시 쓸 때"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--rule", help="그 규칙을 피하는 문형만 보인다. hanlint rules 로 이름을 본다")
    parser.add_argument("--register", choices=REGISTERS, default=HAPNIDA, help="문형 문체. 기본 합니다체")
    addCommonOptions(parser, ("text", "json"))


def indent(text: str, label: str) -> str:
    """여러 줄짜리 예시를 첫 줄에만 표를 달고 나머지는 맞춰 들여쓴다."""
    pad = " " * len(label)
    lines = text.rstrip("\n").split("\n")
    return "\n".join((label if index == 0 else pad) + line for index, line in enumerate(lines))


def run(args: argparse.Namespace) -> int:
    chosen = patternsAvoiding(args.rule) if args.rule else patterns()
    if not chosen:
        raise KeyError(f"`{args.rule}` 을 피하는 문형이 없다. hanlint patterns 로 전부 본다")
    chosen = [patternInRegister(pattern, args.register) for pattern in chosen]
    if args.format == "json":
        emit(json.dumps({"version": 1, "patterns": [p.asDict() for p in chosen]}, ensure_ascii=False, indent=2), args.output)
        return 0
    lines: list[str] = []
    for pattern in chosen:
        lines.append(f"{pattern.name}  ({', '.join(pattern.avoids)} 를 피한다)")
        lines.append(f"  틀    {pattern.form}")
        lines.append(f"  언제  {pattern.when}")
        lines.append(indent(pattern.example, "  예시  "))
        lines.append(indent(pattern.instead, "  대신  "))
        lines.append(f"  출처  {pattern.source}")
        lines.append("")
    lines.append(f"문형 {len(chosen)}개. 예시는 전부 hanlint 를 error 0 으로 통과한다 (게이트가 확인한다)")
    if not args.rule:
        lines.append("지적을 받은 자리를 다시 쓰려면 hanlint patterns --rule <규칙>")
    emit("\n".join(lines), args.output)
    return 0
