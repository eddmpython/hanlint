"""`hanlint arena`. 작법 전략의 안전과 블라인드 선호를 분리해 기록한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...arena import aggregateResults, loadJson, loadWritingTrial, prepareBlind, recordEvaluation, revealTrial
from .shared import addCommonOptions, addOutputOption, configFrom, emit

HELP = "기준 글과 후보 글의 안전 계약과 블라인드 선호를 따로 비교한다"


def outputOptions(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json"), default="json", help="출력 꼴. 기본 json")
    addOutputOption(parser)


def addParser(parser: argparse.ArgumentParser) -> None:
    commands = parser.add_subparsers(dest="arenaCommand", required=True)
    blind = commands.add_parser("blind", help="두 결과를 guard로 검사하고 안전할 때만 A/B를 만든다")
    blind.add_argument("trial", type=Path)
    blind.add_argument("--seed", type=int, required=True)
    addCommonOptions(blind, ("json", "text"))
    record = commands.add_parser("record", help="작성한 블라인드 평가를 검증하고 해시로 잠근다")
    record.add_argument("blind", type=Path)
    record.add_argument("evaluation", type=Path)
    outputOptions(record)
    reveal = commands.add_parser("reveal", help="가린 좌우를 기준과 후보 전략으로 되돌린다")
    reveal.add_argument("trial", type=Path)
    reveal.add_argument("blind", type=Path)
    reveal.add_argument("evaluation", type=Path, nargs="?")
    addCommonOptions(reveal, ("json", "text"))
    aggregate = commands.add_parser("aggregate", help="여러 reveal 결과의 안전과 선호를 집계한다")
    aggregate.add_argument("results", type=Path, nargs="+")
    outputOptions(aggregate)


def renderBlind(data: dict) -> str:
    lines = [f"안전 결과: {data['safetyOutcome']}"]
    if data["eligibleForPreference"]:
        lines.extend(("", "## 왼쪽", "", data["comparison"]["left"], "", "## 오른쪽", "", data["comparison"]["right"]))
    else:
        lines.append("자동 계약을 함께 통과하지 않아 선호 평가를 만들지 않았다.")
    lines.extend(("", data["meaning"], f"blind SHA256: {data['blindSha256']}"))
    return "\n".join(lines)


def renderResult(data: dict) -> str:
    lines = [f"{data['trialId']}: 안전 결과 {data['safetyOutcome']}"]
    if data.get("preference"):
        decisions = data["preference"]["decisions"]
        lines.append("선호: " + ", ".join(f"{dimension}={choice}" for dimension, choice in decisions.items()))
        lines.append(f"평가자 종류: {data['preference']['evaluatorKind']}")
    lines.extend((data["meaning"], f"result SHA256: {data['resultSha256']}"))
    return "\n".join(lines)


def renderEvaluation(data: dict) -> str:
    return "\n".join(
        (
            f"평가자: {data['evaluatorId']} ({data['evaluatorKind']})",
            "선택: " + ", ".join(f"{dimension}={choice}" for dimension, choice in data["decisions"].items()),
            data["meaning"],
            f"evaluation SHA256: {data['evaluationSha256']}",
        )
    )


def renderAggregate(data: dict) -> str:
    safety = data["safety"]
    lines = [
        f"trial {data['trials']}개",
        "안전: " + ", ".join(f"{name}={count}" for name, count in safety.items()),
    ]
    for kind, preferences in data["preferences"].items():
        lines.append(f"{kind} 평가 {preferences['evaluations']}개")
        for dimension in ("naturalness", "taskUtility", "voice"):
            counts = preferences[dimension]
            lines.append(f"- {dimension}: 후보 {counts['candidate']}, 기준 {counts['baseline']}, 무승부 {counts['tie']}")
    lines.extend((data["claimBoundary"], f"aggregate SHA256: {data['aggregateSha256']}"))
    return "\n".join(lines)


def emitData(data: dict, formatName: str, output: Path | None, renderer) -> None:
    rendered = json.dumps(data, ensure_ascii=False, indent=2) if formatName == "json" else renderer(data)
    emit(rendered, output)


def run(args: argparse.Namespace) -> int:
    if args.arenaCommand == "blind":
        trial = loadWritingTrial(args.trial)
        if args.preset and args.preset != trial.brief.preset:
            raise ValueError(f"--preset {args.preset} 과 brief preset {trial.brief.preset} 이 다르다")
        config = configFrom(args, start=args.trial.resolve().parent)
        emitData(prepareBlind(trial, args.seed, config), args.format, args.output, renderBlind)
    elif args.arenaCommand == "record":
        emitData(recordEvaluation(loadJson(args.blind), loadJson(args.evaluation)), args.format, args.output, renderEvaluation)
    elif args.arenaCommand == "reveal":
        trial = loadWritingTrial(args.trial)
        if args.preset and args.preset != trial.brief.preset:
            raise ValueError(f"--preset {args.preset} 과 brief preset {trial.brief.preset} 이 다르다")
        config = configFrom(args, start=args.trial.resolve().parent)
        evaluation = loadJson(args.evaluation) if args.evaluation else None
        emitData(revealTrial(trial, loadJson(args.blind), evaluation, config), args.format, args.output, renderResult)
    else:
        result = aggregateResults([loadJson(path) for path in args.results])
        emitData(result, args.format, args.output, renderAggregate)
    return 0
