"""`hanlint diff 전.md 후.md`. 두 초안의 지문 차이. 고침이 구조를 바꿨는지 낱말만 바꿨는지 본다."""

from __future__ import annotations

import argparse
from pathlib import Path

from ... import analyzerFor
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...report import renderDiff
from ...rules import runAll
from .shared import addCommonOptions, configFrom, emit, readFile, startFolder

HELP = "두 초안의 지문 차이를 숫자로 보인다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("before", type=Path, help="앞선 초안")
    parser.add_argument("after", type=Path, help="고친 초안")
    addCommonOptions(parser, ("text",))


def run(args: argparse.Namespace) -> int:
    config = configFrom(args, start=startFolder([args.after]))
    analyzer = analyzerFor(config)
    beforeDoc = buildFingerprint(parseMarkdown(readFile(args.before), path=str(args.before)), analyzer, config)
    afterDoc = buildFingerprint(parseMarkdown(readFile(args.after), path=str(args.after)), analyzer, config)
    emit(renderDiff(beforeDoc, afterDoc, runAll(beforeDoc, config), runAll(afterDoc, config)), args.output)
    return 0
