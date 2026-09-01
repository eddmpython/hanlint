"""`hanlint verify-patch contract.json 글.md patch.json`. 국소 치환을 적용하지 않고 검증한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...config import loadContract, loadPatch
from ...guard import verifyPatch
from .shared import addCommonOptions, configFrom, emit, readFile, startFolder

HELP = "Patch의 원문 한 자리, reason 감소, 새 보호 원자 위반과 새 error 부재를 검증한다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("contract", type=Path, help="Reader Contract JSON")
    parser.add_argument("file", type=Path, help="수정 전 한국어 마크다운")
    parser.add_argument("patch", type=Path, help="Patch JSON")
    addCommonOptions(parser, ("json",))


def run(args: argparse.Namespace) -> int:
    contract = loadContract(args.contract)
    patch = loadPatch(args.patch)
    config = configFrom(args, start=startFolder([args.file]))
    result = verifyPatch(readFile(args.file), patch, contract, config, str(args.file))
    emit(json.dumps(result.asDict(), ensure_ascii=False, indent=2), args.output)
    return 0 if result.verified else 1
