"""`hanlint contract init 글.md`. 원문에서 version 1 Reader Contract 초안을 만든다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...guard import contractFromText, contractFromTextV2
from .shared import emit, readFile

HELP = "원문의 보호 표면을 모두 담은 Reader Contract 초안을 만든다"


def addParser(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="contractAction", required=True)
    initParser = actions.add_parser("init", help="원문에서 version 1 Contract 초안을 만든다")
    initParser.add_argument("file", type=Path, help="계약 초안을 만들 한국어 마크다운")
    initParser.add_argument("--reader", required=True, help="이 글을 읽고 결정하거나 행동할 독자")
    initParser.add_argument("--goal", required=True, help="독자가 이 글로 달성할 목표")
    initParser.add_argument(
        "--outline",
        choices=("h1", "h2", "h3", "h4", "h5", "h6"),
        help="이 제목 수준의 순서를 잠근 version 2 계약. 없으면 호환되는 version 1",
    )
    initParser.add_argument("--fact", action="append", default=[], help="사람이 승인한 사실. 여러 번 줄 수 있다")
    initParser.add_argument("--output", type=Path, help="JSON을 파일로 쓴다. 없으면 stdout")
    initParser.add_argument("--force", action="store_true", help="출력 파일이 이미 있으면 덮어쓴다")


def run(args: argparse.Namespace) -> int:
    if args.output is not None and args.output.exists() and not args.force:
        raise ValueError(f"{args.output} 가 이미 있다. 덮어쓰려면 --force")
    text = readFile(args.file)
    if args.outline:
        contract = contractFromTextV2(text, args.reader, args.goal, int(args.outline[1]), args.fact)
    else:
        if args.fact:
            raise ValueError("--fact는 --outline과 함께 version 2 계약에서 쓴다")
        contract = contractFromText(text, args.reader, args.goal)
    emit(json.dumps(contract.asDict(), ensure_ascii=False, indent=2), args.output)
    return 0
