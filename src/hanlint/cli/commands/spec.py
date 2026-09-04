"""`hanlint spec`. 현재 규칙판을 쓰기 전 숫자 사양으로 편다."""

from __future__ import annotations

import argparse
import json

from ...analysis.grammar import HAPNIDA, REGISTERS
from ...report import renderWritingSpec, writingSpec
from .shared import addCommonOptions, configFrom, emit

HELP = "현재 규칙판과 종류 프로파일을 쓰기 전 숫자 사양으로"


def positiveInt(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("1 이상이어야 한다")
    return number


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--register", choices=REGISTERS, default=HAPNIDA, help="목표 문체. 기본 합니다체")
    parser.add_argument("--chars", type=positiveInt, help="목표 분량. 공백을 포함한 글자 수")
    addCommonOptions(parser, ("text", "json"))


def run(args: argparse.Namespace) -> int:
    config = configFrom(args)
    result = writingSpec(config, args.register, args.chars)
    text = json.dumps(result.asDict(), ensure_ascii=False, indent=2) if args.format == "json" else renderWritingSpec(result)
    emit(text, args.output)
    return 0
