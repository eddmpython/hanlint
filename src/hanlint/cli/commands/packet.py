"""`hanlint packet 글.md`. AI가 같은 근거로 쓰고 고치게 하는 작문 패킷."""

from __future__ import annotations

import argparse
from pathlib import Path

from ...audit import auditDocument
from ...blueprint import STRATEGIES
from ...config import loadWritingBrief
from ...document import parseMarkdown
from ...fingerprint import buildFingerprint
from ...report import PURPOSES, buildBriefWritingPacket, buildWritingPacket, renderWritingPacket
from ...rules import runAll
from .shared import addCommonOptions, configFrom, emit, readFile

HELP = "초안과 대조 자료와 고침 근거를 AI용 JSON 한 덩어리로 만든다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", type=Path, help="요구사항이나 고칠 마크다운 파일")
    parser.add_argument("--purpose", choices=PURPOSES, default="revise", help="draft는 요구사항에서 초안, revise는 초안 고침")
    parser.add_argument("--no-source", dest="includeSource", action="store_false", help="JSON에서 원문 전문을 뺀다")
    parser.add_argument("--strategy", choices=STRATEGIES, help="구조화 brief에만 넣을 opt-in 작법 전략")
    addCommonOptions(parser, ("json",))


def run(args: argparse.Namespace) -> int:
    if args.file.suffix.lower() == ".json":
        if args.purpose != "draft":
            raise ValueError("writing brief JSON은 --purpose draft 에서만 쓴다")
        brief = loadWritingBrief(args.file)
        if args.preset and args.preset != brief.preset:
            raise ValueError(f"--preset {args.preset} 과 brief preset {brief.preset} 이 다르다")
        config = configFrom(args, start=args.file.resolve().parent)
        packet = buildBriefWritingPacket(brief, str(args.file), args.includeSource, args.strategy)
        if config.source:
            packet["verify"]["argv"].extend(("--config", config.source))
        for ruleName in sorted(args.disable):
            packet["verify"]["argv"].extend(("--disable", ruleName))
        emit(renderWritingPacket(packet), args.output)
        return 0
    if args.strategy:
        raise ValueError("--strategy는 구조화 writing brief JSON에서만 쓴다")
    config = configFrom(args, start=args.file.resolve().parent)
    text = readFile(args.file)
    doc = buildFingerprint(parseMarkdown(text, path=str(args.file)), config)
    findings = runAll(doc, config)
    audit = auditDocument(doc, config)
    packet = buildWritingPacket(text, doc, findings, audit, config, args.purpose, args.includeSource)
    emit(renderWritingPacket(packet), args.output)
    return 0
