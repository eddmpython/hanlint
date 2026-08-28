"""`hanlint audit 글.md`. 지문 지도와 분포."""

from __future__ import annotations

import argparse
from pathlib import Path

from ... import analyzerFor
from ...audit import auditDocument
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...report import renderAudit, renderJson, renderMapHtml
from ...rules import runAll
from .shared import addCommonOptions, colorEnabled, configFrom, emit, readFile

HELP = "지문 지도와 분포를 낸다. 점수는 없다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", type=Path, help="분석할 마크다운 파일")
    addCommonOptions(parser, ("text", "html", "json"))


def run(args: argparse.Namespace) -> int:
    config = configFrom(args, start=args.file.resolve().parent)
    doc = buildFingerprint(parseMarkdown(readFile(args.file), path=str(args.file)), analyzerFor(config), config)
    findings = runAll(doc, config)
    audit = auditDocument(doc, config)
    if args.format == "json":
        emit(
            renderJson(
                {str(args.file): findings},
                {str(args.file): audit},
                registers={str(args.file): doc.register},
            ),
            args.output,
        )
    elif args.format == "html":
        emit(renderMapHtml(doc, findings), args.output)
    else:
        emit(renderAudit(doc, findings, audit, colorEnabled(args)), args.output)
    return 0
