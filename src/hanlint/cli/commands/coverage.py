"""`hanlint coverage review.json 글.md`. 사람 평가자의 지적 가운데 hanlint 가 같은 자리를 집은 비율.

규칙을 더하는 근거가 이 숫자다. 못 집은 지적은 유형별로 모아 다음 규칙 후보로 보인다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...coverage import coverageDict, coverageOf, loadReview, renderCoverage
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...rules import runAll
from .shared import addCommonOptions, configFrom, emit, readFile, startFolder

HELP = "평가자 지적과 hanlint 지적의 겹침 비율을 잰다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("review", type=Path, help="평가자 지적 파일 (review.json)")
    parser.add_argument("file", help="같은 글의 마크다운 파일")
    addCommonOptions(parser, ("text", "json"))


def run(args: argparse.Namespace) -> int:
    config = configFrom(args, start=startFolder([args.file]))
    text = readFile(Path(args.file))
    doc = buildFingerprint(parseMarkdown(text, path=args.file), config)
    coverage = coverageOf(text, runAll(doc, config), loadReview(args.review))
    if args.format == "json":
        emit(json.dumps(coverageDict(coverage), ensure_ascii=False, indent=2), args.output)
    else:
        emit(renderCoverage(coverage), args.output)
    return 0
