"""`hanlint blueprint brief.json`. 원문 없는 수사 구조 예산을 컴파일한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...blueprint import STRATEGIES, blueprintFor
from ...config import loadWritingBrief
from .shared import addOutputOption, emit

HELP = "구조화 brief에 맞는 원문 없는 절·문단·문장 예산을 만든다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", type=Path, help="writing brief JSON")
    parser.add_argument("--strategy", choices=STRATEGIES, default=STRATEGIES[0], help="구조 전략")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="출력 꼴. 기본 text")
    addOutputOption(parser)


def renderText(data: dict) -> str:
    budget = data["budget"]
    reference = data["reference"]
    lines = [
        f"{data['input']['preset']} 구조 청사진: 목표 {data['input']['targetCharacters']}자",
        f"{budget['sections']}절, {budget['paragraphs']}문단, {budget['sentences']}문장",
    ]
    for role in budget["roles"]:
        lines.append(
            f"- {role['role']} ({role['startPermille'] / 10:g}~{role['endPermille'] / 10:g}%): "
            f"{role['characters']}자, {role['paragraphs']}문단, {role['sentences']}문장"
        )
    lines.extend(
        (
            f"참조: {reference['kind']} {reference['documents']}편, 고정 말뭉치 {reference['corpus']['documents']}편",
            *data["limits"],
        )
    )
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    data = blueprintFor(loadWritingBrief(args.file), args.strategy)
    rendered = json.dumps(data, ensure_ascii=False, indent=2) if args.format == "json" else renderText(data)
    emit(rendered, args.output)
    return 0
