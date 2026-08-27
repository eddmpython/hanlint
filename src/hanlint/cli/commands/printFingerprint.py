"""`hanlint print 글.md`. 지문 계층을 JSON 으로 낸다. 다른 도구가 지문 위에 무엇을 얹을 때 쓴다.

`--layer` 로 문장, 문단, 절, 글 가운데 한 층만 고른다. 위층은 아래층을 index 로 가리킨다.
"""

from __future__ import annotations

import argparse

from ... import analyzerFor
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...report import LAYERS, renderFingerprintJson
from .shared import addCommonOptions, configFrom, emit, readInput, startFolder

HELP = "지문 계층을 JSON 으로 낸다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", help="마크다운 파일. `-` 는 stdin")
    parser.add_argument("--layer", choices=LAYERS, default="all", help="낼 층. 기본 all")
    parser.add_argument("--path", dest="stdinPath", default="<stdin>", help="stdin 으로 넣은 글의 이름")
    addCommonOptions(parser, ("json",))


def run(args: argparse.Namespace) -> int:
    config = configFrom(args, start=startFolder([args.file]))
    name, text = readInput(args.file, args.stdinPath)
    doc = buildFingerprint(parseMarkdown(text, path=name), analyzerFor(config), config)
    emit(renderFingerprintJson(doc, args.layer), args.output)
    return 0
