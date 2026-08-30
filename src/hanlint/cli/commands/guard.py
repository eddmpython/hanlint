"""`hanlint guard brief.json 글.md`. 생성 전 사실 계약과 결과 글의 결정적 표면을 대조한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...config import loadWritingBrief
from ...guard import guardText, renderGuard
from .shared import addCommonOptions, configFrom, emit, readFile, startFolder

HELP = "구조화 brief와 결과 글의 사실 표면·숫자·코드·error를 대조한다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("brief", type=Path, help="writing brief JSON")
    parser.add_argument("file", type=Path, help="대조할 한국어 마크다운")
    addCommonOptions(parser, ("text", "json"))


def run(args: argparse.Namespace) -> int:
    brief = loadWritingBrief(args.brief)
    if args.preset and args.preset != brief.preset:
        raise ValueError(f"--preset {args.preset} 과 brief preset {brief.preset} 이 다르다")
    config = configFrom(args, start=startFolder([args.file]))
    config.preset = brief.preset
    text = readFile(args.file)
    result = guardText(brief, text, config, str(args.file))
    rendered = json.dumps(result.asDict(), ensure_ascii=False, indent=2) if args.format == "json" else renderGuard(result)
    emit(rendered, args.output)
    return 0 if result.contractSatisfied else 1
