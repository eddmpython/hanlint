import json
from hashlib import sha256
from pathlib import Path

import pytest

from hanlint.arena import WritingTrial, aggregateResults, prepareBlind, recordEvaluation, revealTrial

ROOT = Path(__file__).resolve().parents[2]

BASELINE = """# 운영 결정

해솔 계획은 2026년 8월 31일 시작하며 예산은 380,000원이다. 운영자는 이 두 관찰값으로 다음 확인 순서를 정한다.
"""
CANDIDATE = """# 운영 결정

운영자는 해솔 계획의 시작일인 2026년 8월 31일과 예산 380,000원을 확인한 뒤 다음 확인 순서를 정한다.
"""


def generation(strategyId: str, text: str) -> dict:
    return {
        "strategyId": strategyId,
        "modelId": "qwen3:8b",
        "modelSha256": "a" * 64,
        "promptSha256": "b" * 64,
        "outputSha256": sha256(text.encode()).hexdigest(),
        "text": text,
    }


def mapping(candidate: str = CANDIDATE) -> dict:
    return {
        "version": 1,
        "id": "report-haesol-001",
        "brief": {
            "version": 1,
            "preset": "report",
            "reader": "결정할 운영자",
            "task": "관찰값을 읽고 다음 확인 순서를 정한다",
            "facts": [
                {"id": "F1", "statement": "해솔 계획은 2026년 8월 31일 시작한다."},
                {"id": "F2", "statement": "예산은 380,000원이다."},
            ],
            "mustInclude": ["해솔 계획", "2026년 8월 31일", "380,000원"],
            "allowedNumbers": ["2026", "8", "31", "380000"],
            "forbidden": ["효과가 입증됐다"],
            "length": {"min": 70, "max": 300},
        },
        "baseline": generation("plainBrief", BASELINE),
        "candidate": generation("rhetoricalPlanV1", candidate),
    }


def evaluation(blind: dict, choice: str = "left", kind: str = "human") -> dict:
    return {
        "version": 1,
        "kind": "hanlint.blindEvaluation",
        "blindSha256": blind["blindSha256"],
        "evaluatorId": "reviewer-01",
        "evaluatorKind": kind,
        "decisions": {"naturalness": choice, "taskUtility": "tie", "voice": choice},
        "note": "두 글을 요구와 나란히 읽고 판단했다.",
    }


def testTrialBindsEveryGenerationHashAndRejectsAnAmbiguousBaseline():
    trial = WritingTrial.fromMapping(mapping())
    assert trial.baseline.strategyId == "plainBrief" and len(trial.digest) == 64
    broken = mapping()
    broken["candidate"]["outputSha256"] = "0" * 64
    with pytest.raises(ValueError, match="text와 다르다"):
        WritingTrial.fromMapping(broken)
    broken = mapping()
    broken["baseline"]["strategyId"] = "other"
    with pytest.raises(ValueError, match="plainBrief"):
        WritingTrial.fromMapping(broken)


def testBlindPacketHidesStrategiesAndIsDeterministic():
    trial = WritingTrial.fromMapping(mapping())
    blind = prepareBlind(trial, 42)
    assert blind == prepareBlind(trial, 42)
    assert blind["eligibleForPreference"] and blind["safetyOutcome"] == "bothSafe"
    assert blind["comparison"]["left"] in (BASELINE, CANDIDATE)
    shown = json.dumps(blind, ensure_ascii=False)
    assert "plainBrief" not in shown and "rhetoricalPlanV1" not in shown and "qwen3:8b" not in shown
    assert blind["evaluationTemplate"]["blindSha256"] == blind["blindSha256"]


def testUnsafePairGetsAnAutomaticOutcomeAndNoPreferencePacket():
    unsafe = "# 운영 결정\n\n해솔 계획의 시작일과 예산을 확인한다.\n"
    blind = prepareBlind(WritingTrial.fromMapping(mapping(unsafe)), 42)
    assert blind["safetyOutcome"] == "baselineSafeWin"
    assert not blind["eligibleForPreference"] and blind["comparison"] is None
    with pytest.raises(ValueError, match="통과한"):
        recordEvaluation(blind, evaluation(blind))


def testEvaluationRecordsKindAndRevealMapsTheHiddenSide():
    trial = WritingTrial.fromMapping(mapping())
    blind = prepareBlind(trial, 42)
    candidateSide = "left" if blind["comparison"]["left"] == CANDIDATE else "right"
    recorded = recordEvaluation(blind, evaluation(blind, candidateSide))
    assert recorded["evaluatorKind"] == "human" and len(recorded["evaluationSha256"]) == 64
    revealed = revealTrial(trial, blind, recorded)
    assert revealed["preference"]["decisions"] == {
        "naturalness": "candidate",
        "taskUtility": "tie",
        "voice": "candidate",
    }
    assert revealed["safetyOutcome"] == "bothSafe"


def testAggregateSeparatesHumanAndLlmAndRejectsTampering():
    trial = WritingTrial.fromMapping(mapping())
    blind = prepareBlind(trial, 8)
    first = revealTrial(trial, blind, recordEvaluation(blind, evaluation(blind, "left", "human")))
    secondData = mapping()
    secondData["id"] = "report-haesol-002"
    second = WritingTrial.fromMapping(secondData)
    secondBlind = prepareBlind(second, 9)
    secondResult = revealTrial(
        second,
        secondBlind,
        recordEvaluation(secondBlind, evaluation(secondBlind, "tie", "llm")),
    )
    aggregate = aggregateResults([first, secondResult])
    assert aggregate["preferences"]["human"]["evaluations"] == 1
    assert aggregate["preferences"]["llm"]["evaluations"] == 1
    assert "30개 미만" in aggregate["claimBoundary"] and "진실" in aggregate["claimBoundary"]
    first["safetyOutcome"] = "candidateSafeWin"
    with pytest.raises(ValueError, match="digest"):
        aggregateResults([first])


def testRequiredPlaceholdersAndMixedStrategiesCannotBecomeEvidence():
    trial = WritingTrial.fromMapping(mapping())
    blind = prepareBlind(trial, 3)
    with pytest.raises(ValueError, match="실제 값"):
        recordEvaluation(blind, blind["evaluationTemplate"])
    first = revealTrial(trial, blind, recordEvaluation(blind, evaluation(blind, "tie")))
    otherData = mapping()
    otherData["id"] = "report-haesol-other"
    otherData["candidate"]["strategyId"] = "differentStrategy"
    other = WritingTrial.fromMapping(otherData)
    otherBlind = prepareBlind(other, 4)
    second = revealTrial(other, otherBlind, recordEvaluation(otherBlind, evaluation(otherBlind, "tie")))
    with pytest.raises(ValueError, match="같은 candidateStrategyId"):
        aggregateResults([first, second])


def testPublishedSchemasNameTheClosedTrialAndEvaluationSurfaces():
    data = ROOT / "src" / "hanlint" / "data"
    trialSchema = json.loads((data / "writingTrial.schema.json").read_text(encoding="utf-8"))
    evaluationSchema = json.loads((data / "blindEvaluation.schema.json").read_text(encoding="utf-8"))
    assert set(trialSchema["required"]) == {"version", "id", "brief", "baseline", "candidate"}
    assert trialSchema["properties"]["brief"]["$ref"] == "writingBrief.schema.json"
    assert evaluationSchema["properties"]["evaluatorKind"]["enum"] == ["human", "llm"]
    assert set(evaluationSchema["properties"]["decisions"]["required"]) == {
        "naturalness",
        "taskUtility",
        "voice",
    }
