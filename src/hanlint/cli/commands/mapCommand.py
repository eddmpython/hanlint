"""`hanlint map 글.md`. 지문 지도만."""

from __future__ import annotations

import argparse
from pathlib import Path

from ... import analyzerFor
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...report import renderMap, renderMapHtml
from ...rules import runAll
from .shared import addCommonOptions, colorEnabled, configFrom, emit, readFile

HELP = "지문 지도만 낸다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", type=Path, help="마크다운 파일")
    addCommonOptions(parser, ("text", "html"))


def run(args: argparse.Namespace) -> int:
    config = configFrom(args, start=args.file.resolve().parent)
    doc = buildFingerprint(parseMarkdown(readFile(args.file), path=str(args.file)), analyzerFor(config), config)
    findings = runAll(doc, config)
    if args.format == "html":
        emit(renderMapHtml(doc, findings), args.output)
    else:
        emit(renderMap(doc, findings, colorEnabled(args)), args.output)
    return 0
