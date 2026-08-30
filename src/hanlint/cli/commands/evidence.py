"""`hanlint evidence brief.json`. 사실별 고정 근거 원장을 검사한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...evidence import evidenceLedger
from .shared import addOutputOption, emit

HELP = "v2 writing brief의 사실별 출처 판·인용 조각 해시·라이선스를 검사한다"


def addParser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", type=Path, help="근거 원장이 든 writing brief v2 JSON")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="출력 꼴. 기본 text")
    addOutputOption(parser)


def renderText(data: dict) -> str:
    if not data["ledgerValid"]:
        return "근거 원장 위반\n" + "\n".join(f"- {item}" for item in data["violations"]) + "\n\n" + data["meaning"]
    lines = [
        f"근거 원장 충족: fact {len(data['factEvidence'])}개, evidence {data['evidenceRecords']}개",
        f"사람 검토 기록: {data['humanVerifiedRecords']}개",
    ]
    lines.extend(f"- {factId}: {', '.join(evidenceIds)}" for factId, evidenceIds in data["factEvidence"].items())
    lines.extend(("", data["meaning"]))
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    try:
        raw = json.loads(args.file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"writing brief JSON을 읽지 못했다: {error.msg}, {error.lineno}줄") from error
    result = evidenceLedger(raw).asDict()
    rendered = json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else renderText(result)
    emit(rendered, args.output)
    return 0 if result["ledgerValid"] else 1
