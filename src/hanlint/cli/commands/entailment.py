"""`hanlint entailment`. gold를 숨긴 함의 사례를 내고 외부 평가기 예측을 집계한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...entailment import entailmentCases, evaluateEntailment
from .shared import addOutputOption, emit

HELP = "사람 합의 한국어 근거 쌍으로 외부 평가기의 함의 판정과 기권을 집계한다"


def addParser(parser: argparse.ArgumentParser) -> None:
    commands = parser.add_subparsers(dest="entailmentCommand", required=True)
    cases = commands.add_parser("cases", help="gold를 뺀 고정 평가 사례 36개를 낸다")
    cases.add_argument("--format", choices=("json",), default="json", help="출력 꼴. json만 지원한다")
    addOutputOption(cases)
    evaluate = commands.add_parser("evaluate", help="36개 예측과 사람 합의 gold의 집계 지표를 낸다")
    evaluate.add_argument("file", type=Path, help="entailment predictions JSON")
    evaluate.add_argument("--format", choices=("text", "json"), default="text", help="출력 꼴. 기본 text")
    addOutputOption(evaluate)


def readJson(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"entailment predictions JSON을 읽지 못했다: {error.msg}, {error.lineno}줄") from error


def percent(value: float | None) -> str:
    return "없음" if value is None else f"{value * 100:.2f}%"


def renderText(data: dict) -> str:
    metrics = data["metrics"]
    lines = [
        f"함의 벤치마크 집계: {metrics['totalCases']}개",
        f"응답 {metrics['answered']}개, 기권 {metrics['abstained']}개, coverage {percent(metrics['coverage'])}",
        f"선택 정확도 {percent(metrics['selectedAccuracy']['ratio'])}",
        f"selective risk {percent(metrics['selectiveRisk']['ratio'])}",
        f"macro F1 {metrics['macroF1']:.4f}",
    ]
    lines.extend(f"- {label}: F1 {values['f1']:.4f}" for label, values in metrics["perClass"].items())
    lines.extend(("", data["meaning"]))
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    if args.entailmentCommand == "cases":
        rendered = json.dumps(entailmentCases(), ensure_ascii=False, indent=2)
    else:
        result = evaluateEntailment(readJson(args.file)).asDict()
        rendered = json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else renderText(result)
    emit(rendered, args.output)
    return 0
