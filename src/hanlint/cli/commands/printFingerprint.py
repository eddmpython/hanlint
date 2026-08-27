"""`hanlint print 글.md`. 지문 계층을 JSON 으로 그대로 낸다. 다른 도구가 지문 위에 무엇을 얹을 때 쓴다."""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

from ... import analyzerFor
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from .shared import addCommonOptions, configFrom, emit, readFile

HELP = "지문 계층을 JSON 으로 낸다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", type=Path, help="마크다운 파일")
    addCommonOptions(parser, ("json",))


def plain(value):
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(f"JSON 으로 못 바꾼다: {type(value).__name__}")


def run(args: argparse.Namespace) -> int:
    config = configFrom(args, start=args.file.resolve().parent)
    doc = buildFingerprint(parseMarkdown(readFile(args.file), path=str(args.file)), analyzerFor(config), config)
    data = dataclasses.asdict(doc)
    data.pop("blocks", None)
    emit(json.dumps({"version": 1, "fingerprint": data}, ensure_ascii=False, indent=2, default=plain), args.output)
    return 0
