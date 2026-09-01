"""`hanlint check contract.json 글.md`. 최소 Reader Contract와 결과 글을 대조한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...config import loadContract
from ...guard import check, renderCheck
from .shared import addCommonOptions, configFrom, emit, readFile, startFolder

HELP = "Reader Contract 보호 원자와 hanlint 지적의 결정적 JSON 영수증을 낸다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("contract", type=Path, help="Reader Contract JSON")
    parser.add_argument("file", type=Path, help="검사할 한국어 마크다운")
    addCommonOptions(parser, ("json", "text"))


def run(args: argparse.Namespace) -> int:
    contract = loadContract(args.contract)
    config = configFrom(args, start=startFolder([args.file]))
    result = check(readFile(args.file), contract, config, str(args.file))
    rendered = renderCheck(result) if args.format == "text" else json.dumps(result.asDict(), ensure_ascii=False, indent=2)
    emit(rendered, args.output)
    return 0 if result.violationCount == 0 else 1
