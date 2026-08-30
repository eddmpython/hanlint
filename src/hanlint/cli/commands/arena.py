"""`hanlint arena`. 작법 전략의 안전과 블라인드 선호를 분리해 기록한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ...arena import (
    EVALUATOR_GROUPS,
    adjudicatePanel,
    aggregateResults,
    evaluatePanelJudge,
    loadJson,
    loadPanelTrialSet,
    loadWritingTrial,
    prepareBlind,
    preparePanelAssignment,
    preparePanelJudgeCases,
    preparePanelSuite,
    recordEvaluation,
    recordPanelAssignmentReview,
    recordPanelReviewBatch,
    renderPanelReviewHtml,
    revealPanel,
    revealTrial,
    summarizePanelJudgeConsistency,
)
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
    panel = commands.add_parser("panel", help="같은 전략의 trial set을 맥락 있는 사람용 블라인드 suite로 만든다")
    panel.add_argument("trialSet", type=Path)
    panel.add_argument("--seed", type=int, required=True)
    panel.add_argument("--voice-references", dest="voiceReferences", type=Path)
    outputOptions(panel)
    panelRecord = commands.add_parser("panel-record", help="사람 한 명의 독립 평가 묶음을 검증하고 잠근다")
    panelRecord.add_argument("suite", type=Path)
    panelRecord.add_argument("reviewBatch", type=Path)
    outputOptions(panelRecord)
    panelAdjudicate = commands.add_parser("panel-adjudicate", help="세 명 이상 평가의 합의와 불일치를 계산한다")
    panelAdjudicate.add_argument("suite", type=Path)
    panelAdjudicate.add_argument("reviewBatches", type=Path, nargs="+")
    outputOptions(panelAdjudicate)
    panelReveal = commands.add_parser("panel-reveal", help="사람 합의의 가린 좌우를 후보와 기준으로 되돌린다")
    panelReveal.add_argument("trialSet", type=Path)
    panelReveal.add_argument("suite", type=Path)
    panelReveal.add_argument("adjudication", type=Path)
    outputOptions(panelReveal)
    judgeCases = commands.add_parser("judge-cases", help="자동 심사기 위치 편향을 재는 양방향 사례를 만든다")
    judgeCases.add_argument("suite", type=Path)
    outputOptions(judgeCases)
    judgeConsistency = commands.add_parser(
        "judge-consistency",
        help="사람 정답 없이 자동 심사기의 양방향 일관성만 계산한다",
    )
    judgeConsistency.add_argument("suite", type=Path)
    judgeConsistency.add_argument("judgeCases", type=Path)
    judgeConsistency.add_argument("predictions", type=Path)
    outputOptions(judgeConsistency)
    judgeEvaluate = commands.add_parser("judge-evaluate", help="자동 심사기를 사람 패널 합의에 보정한다")
    judgeEvaluate.add_argument("suite", type=Path)
    judgeEvaluate.add_argument("adjudication", type=Path)
    judgeEvaluate.add_argument("judgeCases", type=Path)
    judgeEvaluate.add_argument("predictions", type=Path)
    outputOptions(judgeEvaluate)
    assignment = commands.add_parser("assign", help="평가자 한 명에게 내부 순서를 숨긴 독립 case를 배정한다")
    assignment.add_argument("suite", type=Path)
    assignment.add_argument("--evaluator-id", dest="evaluatorId", required=True)
    assignment.add_argument("--group", choices=EVALUATOR_GROUPS, required=True)
    outputOptions(assignment)
    reviewPage = commands.add_parser("review-page", help="평가자 배정을 네트워크 없는 단일 HTML 화면으로 만든다")
    reviewPage.add_argument("suite", type=Path)
    reviewPage.add_argument("assignment", type=Path)
    reviewPage.add_argument("--output", type=Path, required=True)
    assignmentRecord = commands.add_parser("assignment-record", help="배정 화면의 좌우 선택을 suite 방향으로 되돌려 잠근다")
    assignmentRecord.add_argument("suite", type=Path)
    assignmentRecord.add_argument("assignment", type=Path)
    assignmentRecord.add_argument("review", type=Path)
    outputOptions(assignmentRecord)


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


def renderPanelSuite(data: dict) -> str:
    source = data["source"]
    return "\n".join(
        (
            f"suite: {data['suiteId']}",
            f"사람 평가 대상 {source['eligibleCases']}개, 자동 제외 {source['excludedCases']}개",
            data["claimBoundary"],
            f"suite SHA256: {data['suiteSha256']}",
        )
    )


def renderPanelBatch(data: dict) -> str:
    return "\n".join(
        (
            f"평가자: {data['evaluator']['id']} ({data['evaluator']['group']})",
            f"독립 평가 {len(data['reviews'])}개",
            data["meaning"],
            f"batch SHA256: {data['batchSha256']}",
        )
    )


def renderAssignment(data: dict) -> str:
    return "\n".join(
        (
            f"평가자: {data['evaluator']['id']} ({data['evaluator']['group']})",
            f"독립 배정 {len(data['cases'])}개",
            data["claimBoundary"],
            f"assignment SHA256: {data['assignmentSha256']}",
        )
    )


def renderAdjudication(data: dict) -> str:
    lines = [f"평가자 {data['evaluators']}명, 사례 {len(data['cases'])}개"]
    for dimension, metric in data["agreement"]["preferences"].items():
        lines.append(f"{dimension} alpha: {metric['alpha']}")
    lines.extend((data["claimBoundary"], f"adjudication SHA256: {data['adjudicationSha256']}"))
    return "\n".join(lines)


def renderPanelResult(data: dict) -> str:
    lines = [f"후보 전략: {data['candidateStrategyId']}"]
    for dimension, result in data["dimensions"].items():
        lines.append(
            f"{dimension}: 후보 {result['candidate']}, 기준 {result['baseline']}, "
            f"무승부 {result['tie']}, 선호 비율 {result['candidatePreferenceShare']}"
        )
    lines.extend((data["claimBoundary"], f"result SHA256: {data['resultSha256']}"))
    return "\n".join(lines)


def renderJudgeCases(data: dict) -> str:
    return "\n".join(
        (
            f"양방향 presentation {len(data['presentations'])}개",
            data["claimBoundary"],
            f"judge cases SHA256: {data['judgeCasesSha256']}",
        )
    )


def renderJudgeConsistency(data: dict) -> str:
    lines = [f"자동 심사기: {data['evaluatorId']}"]
    for dimension, metric in data["positionConsistency"]["preferences"].items():
        lines.append(f"{dimension}: 순서 일관성 {metric['consistency']}, 사용 가능 범위 {metric['usableCoverage']}")
    lines.extend((data["claimBoundary"], f"consistency SHA256: {data['consistencySha256']}"))
    return "\n".join(lines)


def renderJudgeEvaluation(data: dict) -> str:
    lines = [f"자동 심사기: {data['evaluatorId']}"]
    for dimension, metric in data["preferences"].items():
        lines.append(
            f"{dimension}: coverage {metric['coverage']}, selected accuracy {metric['selectedAccuracy']}, "
            f"macro F1 {metric['macroF1']}"
        )
    lines.extend((data["claimBoundary"], f"evaluation SHA256: {data['evaluationSha256']}"))
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
    elif args.arenaCommand == "aggregate":
        result = aggregateResults([loadJson(path) for path in args.results])
        emitData(result, args.format, args.output, renderAggregate)
    elif args.arenaCommand == "panel":
        trialSet = loadPanelTrialSet(args.trialSet)
        voiceReferences = loadJson(args.voiceReferences) if args.voiceReferences else None
        if voiceReferences is not None and not isinstance(voiceReferences, dict):
            raise ValueError("--voice-references는 caseId를 키로 둔 JSON 객체다")
        result = preparePanelSuite(trialSet["trials"], trialSet["studyId"], args.seed, voiceReferences)
        emitData(result, args.format, args.output, renderPanelSuite)
    elif args.arenaCommand == "panel-record":
        result = recordPanelReviewBatch(loadJson(args.suite), loadJson(args.reviewBatch))
        emitData(result, args.format, args.output, renderPanelBatch)
    elif args.arenaCommand == "panel-adjudicate":
        result = adjudicatePanel(loadJson(args.suite), [loadJson(path) for path in args.reviewBatches])
        emitData(result, args.format, args.output, renderAdjudication)
    elif args.arenaCommand == "panel-reveal":
        trialSet = loadPanelTrialSet(args.trialSet)
        result = revealPanel(trialSet["trials"], loadJson(args.suite), loadJson(args.adjudication))
        emitData(result, args.format, args.output, renderPanelResult)
    elif args.arenaCommand == "judge-cases":
        result = preparePanelJudgeCases(loadJson(args.suite))
        emitData(result, args.format, args.output, renderJudgeCases)
    elif args.arenaCommand == "judge-consistency":
        result = summarizePanelJudgeConsistency(
            loadJson(args.suite),
            loadJson(args.judgeCases),
            loadJson(args.predictions),
        )
        emitData(result, args.format, args.output, renderJudgeConsistency)
    elif args.arenaCommand == "judge-evaluate":
        result = evaluatePanelJudge(
            loadJson(args.suite),
            loadJson(args.adjudication),
            loadJson(args.judgeCases),
            loadJson(args.predictions),
        )
        emitData(result, args.format, args.output, renderJudgeEvaluation)
    elif args.arenaCommand == "assign":
        result = preparePanelAssignment(loadJson(args.suite), args.evaluatorId, args.group)
        emitData(result, args.format, args.output, renderAssignment)
    elif args.arenaCommand == "review-page":
        suite = loadJson(args.suite)
        emit(renderPanelReviewHtml(suite, loadJson(args.assignment)), args.output)
    else:
        result = recordPanelAssignmentReview(
            loadJson(args.suite),
            loadJson(args.assignment),
            loadJson(args.review),
        )
        emitData(result, args.format, args.output, renderPanelBatch)
    return 0
