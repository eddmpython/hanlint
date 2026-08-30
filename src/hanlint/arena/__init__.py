"""작법 전략을 안전 계약과 블라인드 사람 선호로 나눠 비교한다."""

from __future__ import annotations

import json
from copy import copy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from ..config import Config, WritingBrief
from ..guard import guardText

ARENA_VERSION = 1
DIMENSIONS = ("naturalness", "taskUtility", "voice")
CHOICES = ("left", "right", "tie")
EVALUATOR_KINDS = ("human", "llm")


def stableDigest(value: dict) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode()).hexdigest()


def blindDigest(packet: dict) -> str:
    canonical = copy(packet)
    canonical.pop("blindSha256", None)
    if canonical.get("evaluationTemplate"):
        canonical["evaluationTemplate"] = copy(canonical["evaluationTemplate"])
        canonical["evaluationTemplate"]["blindSha256"] = "<blindSha256>"
    return stableDigest(canonical)


def candidateIsLeft(trial: WritingTrial, seed: int) -> bool:
    return int(sha256(f"{trial.digest}:{seed}".encode()).hexdigest(), 16) % 2 == 1


def checkedString(value: object, where: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{where} 는 양끝 공백 없는 문자열이다")
    return value


def checkedText(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} 는 내용이 있는 문자열이다")
    return value


def checkedSha(value: object, where: str) -> str:
    value = checkedString(value, where)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{where} 는 소문자 SHA256이다")
    return value


def exactKeys(data: object, expected: set[str], where: str) -> dict:
    if not isinstance(data, dict):
        raise ValueError(f"{where} 는 JSON 객체다")
    unknown = sorted(set(data) - expected)
    missing = sorted(expected - set(data))
    if unknown:
        raise ValueError(f"{where} 의 모르는 키: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{where} 의 빠진 키: {', '.join(missing)}")
    return data


@dataclass(frozen=True)
class GenerationRecord:
    strategyId: str
    modelId: str
    modelSha256: str
    promptSha256: str
    outputSha256: str
    text: str

    @classmethod
    def fromMapping(cls, data: object, where: str) -> GenerationRecord:
        data = exactKeys(
            data,
            {"strategyId", "modelId", "modelSha256", "promptSha256", "outputSha256", "text"},
            where,
        )
        text = checkedText(data["text"], f"{where}.text")
        outputSha = checkedSha(data["outputSha256"], f"{where}.outputSha256")
        if sha256(text.encode()).hexdigest() != outputSha:
            raise ValueError(f"{where}.outputSha256 가 text와 다르다")
        return cls(
            strategyId=checkedString(data["strategyId"], f"{where}.strategyId"),
            modelId=checkedString(data["modelId"], f"{where}.modelId"),
            modelSha256=checkedSha(data["modelSha256"], f"{where}.modelSha256"),
            promptSha256=checkedSha(data["promptSha256"], f"{where}.promptSha256"),
            outputSha256=outputSha,
            text=text,
        )

    def asDict(self) -> dict:
        return {
            "strategyId": self.strategyId,
            "modelId": self.modelId,
            "modelSha256": self.modelSha256,
            "promptSha256": self.promptSha256,
            "outputSha256": self.outputSha256,
            "text": self.text,
        }


@dataclass(frozen=True)
class WritingTrial:
    id: str
    brief: WritingBrief
    baseline: GenerationRecord
    candidate: GenerationRecord

    @classmethod
    def fromMapping(cls, data: object) -> WritingTrial:
        data = exactKeys(data, {"version", "id", "brief", "baseline", "candidate"}, "writing trial")
        if isinstance(data["version"], bool) or not isinstance(data["version"], int) or data["version"] != ARENA_VERSION:
            raise ValueError(f"writing trial version 은 {ARENA_VERSION}이다")
        baseline = GenerationRecord.fromMapping(data["baseline"], "baseline")
        candidate = GenerationRecord.fromMapping(data["candidate"], "candidate")
        if baseline.strategyId != "plainBrief":
            raise ValueError("baseline.strategyId 는 plainBrief 다")
        if candidate.strategyId == baseline.strategyId:
            raise ValueError("candidate.strategyId 는 plainBrief 와 달라야 한다")
        return cls(
            id=checkedString(data["id"], "writing trial id"),
            brief=WritingBrief.fromMapping(data["brief"]),
            baseline=baseline,
            candidate=candidate,
        )

    @property
    def digest(self) -> str:
        return stableDigest(self.asDict())

    def asDict(self) -> dict:
        return {
            "version": ARENA_VERSION,
            "id": self.id,
            "brief": self.brief.asDict(),
            "baseline": self.baseline.asDict(),
            "candidate": self.candidate.asDict(),
        }


@dataclass(frozen=True)
class BlindEvaluation:
    blindSha256: str
    evaluatorId: str
    evaluatorKind: str
    decisions: dict[str, str]
    note: str

    @classmethod
    def fromMapping(cls, data: object) -> BlindEvaluation:
        data = exactKeys(
            data,
            {"version", "kind", "blindSha256", "evaluatorId", "evaluatorKind", "decisions", "note"},
            "blind evaluation",
        )
        if (
            isinstance(data["version"], bool)
            or not isinstance(data["version"], int)
            or data["version"] != ARENA_VERSION
            or data["kind"] != "hanlint.blindEvaluation"
        ):
            raise ValueError("blind evaluation의 version 또는 kind가 다르다")
        decisions = exactKeys(data["decisions"], set(DIMENSIONS), "decisions")
        normalized = {}
        for dimension in DIMENSIONS:
            choice = decisions[dimension]
            if choice not in CHOICES:
                raise ValueError(f"decisions.{dimension} 은 {', '.join(CHOICES)} 가운데 하나다")
            normalized[dimension] = choice
        evaluatorKind = checkedString(data["evaluatorKind"], "evaluatorKind")
        if evaluatorKind not in EVALUATOR_KINDS:
            raise ValueError(f"evaluatorKind 는 {', '.join(EVALUATOR_KINDS)} 가운데 하나다")
        evaluatorId = checkedString(data["evaluatorId"], "evaluatorId")
        note = checkedString(data["note"], "note")
        if evaluatorId == "<required>" or note == "<required>":
            raise ValueError("evaluatorId와 note의 <required>를 실제 값으로 바꾼다")
        return cls(
            blindSha256=checkedSha(data["blindSha256"], "blindSha256"),
            evaluatorId=evaluatorId,
            evaluatorKind=evaluatorKind,
            decisions=normalized,
            note=note,
        )

    def asDict(self) -> dict:
        return {
            "version": ARENA_VERSION,
            "kind": "hanlint.blindEvaluation",
            "blindSha256": self.blindSha256,
            "evaluatorId": self.evaluatorId,
            "evaluatorKind": self.evaluatorKind,
            "decisions": self.decisions,
            "note": self.note,
        }


def loadJson(path: str | Path) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON을 읽지 못했다: {error.msg}, {error.lineno}줄") from error


def loadWritingTrial(path: str | Path) -> WritingTrial:
    return WritingTrial.fromMapping(loadJson(path))


def prepareBlind(trial: WritingTrial | dict, seed: int, config: Config | None = None) -> dict:
    if isinstance(trial, dict):
        trial = WritingTrial.fromMapping(trial)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed 는 0 이상의 정수다")
    selectedConfig = copy(config) if config is not None else Config()
    baselineGuard = guardText(trial.brief, trial.baseline.text, selectedConfig)
    candidateGuard = guardText(trial.brief, trial.candidate.text, selectedConfig)
    baselineSafe = baselineGuard.contractSatisfied
    candidateSafe = candidateGuard.contractSatisfied
    if baselineSafe and candidateSafe:
        safetyOutcome = "bothSafe"
    elif baselineSafe:
        safetyOutcome = "baselineSafeWin"
    elif candidateSafe:
        safetyOutcome = "candidateSafeWin"
    else:
        safetyOutcome = "bothUnsafe"
    candidateLeft = candidateIsLeft(trial, seed)
    left = trial.candidate if candidateLeft else trial.baseline
    right = trial.baseline if candidateLeft else trial.candidate
    packet = {
        "version": ARENA_VERSION,
        "kind": "hanlint.blindTrial",
        "trialId": trial.id,
        "trialSha256": trial.digest,
        "seed": seed,
        "eligibleForPreference": safetyOutcome == "bothSafe",
        "safetyOutcome": safetyOutcome,
        "automatic": {
            "left": candidateGuard.asDict() if candidateLeft else baselineGuard.asDict(),
            "right": baselineGuard.asDict() if candidateLeft else candidateGuard.asDict(),
        },
        "comparison": {"left": left.text, "right": right.text} if safetyOutcome == "bothSafe" else None,
        "evaluationTemplate": {
            "version": ARENA_VERSION,
            "kind": "hanlint.blindEvaluation",
            "blindSha256": "<blindSha256>",
            "evaluatorId": "<required>",
            "evaluatorKind": "human",
            "decisions": {dimension: "tie" for dimension in DIMENSIONS},
            "note": "<required>",
        }
        if safetyOutcome == "bothSafe"
        else None,
        "meaning": "자동 안전 계약과 블라인드 선호는 다른 결과다. LLM 평가는 사람 평가나 진실이 아니다",
    }
    packet["blindSha256"] = blindDigest(packet)
    if packet["evaluationTemplate"]:
        packet["evaluationTemplate"]["blindSha256"] = packet["blindSha256"]
    return packet


def recordEvaluation(blind: dict, data: BlindEvaluation | dict) -> dict:
    if blind.get("kind") != "hanlint.blindTrial" or not blind.get("eligibleForPreference"):
        raise ValueError("자동 계약을 통과한 blind trial만 평가한다")
    if blind.get("blindSha256") != blindDigest(blind):
        raise ValueError("blind trial의 digest가 다르다")
    evaluation = data if isinstance(data, BlindEvaluation) else BlindEvaluation.fromMapping(data)
    if evaluation.blindSha256 != blind.get("blindSha256"):
        raise ValueError("evaluation의 blindSha256가 blind trial과 다르다")
    result = evaluation.asDict()
    result["evaluationSha256"] = stableDigest(result)
    result["meaning"] = "evaluatorKind가 llm이면 사람 선호나 진실로 해석하지 않는다"
    return result


def revealTrial(
    trial: WritingTrial | dict,
    blind: dict,
    evaluation: dict | None = None,
    config: Config | None = None,
) -> dict:
    if isinstance(trial, dict):
        trial = WritingTrial.fromMapping(trial)
    expected = prepareBlind(trial, blind.get("seed"), config)
    if blind != expected:
        raise ValueError("blind trial이 원본 trial에서 만든 결과와 다르다")
    result = {
        "version": ARENA_VERSION,
        "kind": "hanlint.arenaResult",
        "trialId": trial.id,
        "trialSha256": trial.digest,
        "baselineStrategyId": trial.baseline.strategyId,
        "candidateStrategyId": trial.candidate.strategyId,
        "safetyOutcome": blind["safetyOutcome"],
        "preference": None,
    }
    if blind["eligibleForPreference"]:
        if evaluation is None:
            raise ValueError("둘 다 안전한 trial에는 evaluation이 필요하다")
        if "evaluationSha256" in evaluation:
            baseEvaluation = {key: value for key, value in evaluation.items() if key not in ("evaluationSha256", "meaning")}
            if evaluation["evaluationSha256"] != stableDigest(baseEvaluation):
                raise ValueError("evaluation의 digest가 다르다")
            recorded = recordEvaluation(blind, baseEvaluation)
        else:
            recorded = recordEvaluation(blind, evaluation)
        leftIsCandidate = candidateIsLeft(trial, blind["seed"])
        mapped = {}
        for dimension, choice in recorded["decisions"].items():
            if choice == "tie":
                mapped[dimension] = "tie"
            elif (choice == "left") == leftIsCandidate:
                mapped[dimension] = "candidate"
            else:
                mapped[dimension] = "baseline"
        result["preference"] = {
            "evaluatorId": recorded["evaluatorId"],
            "evaluatorKind": recorded["evaluatorKind"],
            "decisions": mapped,
            "note": recorded["note"],
            "evaluationSha256": recorded["evaluationSha256"],
        }
    result["meaning"] = "안전 승패와 선호는 별도다. 작은 표본이나 LLM 평가로 향상을 주장하지 않는다"
    result["resultSha256"] = stableDigest(result)
    return result


def aggregateResults(results: list[dict]) -> dict:
    if not results:
        raise ValueError("aggregate에는 arenaResult가 하나 이상 필요하다")
    ids = [item.get("trialId") for item in results]
    if len(set(ids)) != len(ids):
        raise ValueError("aggregate의 trialId가 겹친다")
    for item in results:
        if item.get("kind") != "hanlint.arenaResult" or item.get("resultSha256") != stableDigest(
            {key: value for key, value in item.items() if key != "resultSha256"}
        ):
            raise ValueError("arenaResult의 kind 또는 digest가 다르다")
    candidateStrategies = {item["candidateStrategyId"] for item in results}
    if len(candidateStrategies) != 1:
        raise ValueError("aggregate에는 같은 candidateStrategyId 결과만 넣는다")
    safetyNames = ("candidateSafeWin", "baselineSafeWin", "bothSafe", "bothUnsafe")
    safety = {name: sum(item["safetyOutcome"] == name for item in results) for name in safetyNames}
    preferences = {}
    for evaluatorKind in EVALUATOR_KINDS:
        selected = [
            item["preference"] for item in results if item["preference"] and item["preference"]["evaluatorKind"] == evaluatorKind
        ]
        preferences[evaluatorKind] = {
            dimension: {
                choice: sum(item["decisions"][dimension] == choice for item in selected)
                for choice in ("candidate", "baseline", "tie")
            }
            for dimension in DIMENSIONS
        } | {"evaluations": len(selected)}
    payload = {
        "version": ARENA_VERSION,
        "kind": "hanlint.arenaAggregate",
        "baselineStrategyId": "plainBrief",
        "candidateStrategyId": next(iter(candidateStrategies)),
        "trials": len(results),
        "safety": safety,
        "preferences": preferences,
        "claimBoundary": "사람 평가 30개 미만은 탐색 표본이다. LLM 평가는 별도이며 사람 선호나 진실이 아니다",
        "results": results,
    }
    payload["aggregateSha256"] = stableDigest(payload)
    return payload


__all__ = [
    "ARENA_VERSION",
    "BlindEvaluation",
    "GenerationRecord",
    "WritingTrial",
    "aggregateResults",
    "loadJson",
    "loadWritingTrial",
    "prepareBlind",
    "recordEvaluation",
    "revealTrial",
]

from .panel import (  # noqa: E402
    CONTENT_CHOICES,
    EVALUATOR_GROUPS,
    PANEL_DIMENSIONS,
    PANEL_PROTOCOL_REVISION,
    PANEL_RUBRIC,
    PANEL_RUBRIC_SHA256,
    PANEL_VERSION,
    adjudicatePanel,
    checkedAdjudication,
    checkedJudgePredictions,
    checkedPanelSuite,
    checkedPanelTrialSet,
    evaluatePanelJudge,
    loadPanelTrialSet,
    preparePanelJudgeCases,
    preparePanelSuite,
    preparePanelTrialSet,
    recordPanelReviewBatch,
    revealPanel,
    summarizePanelJudgeConsistency,
)

__all__ += [
    "CONTENT_CHOICES",
    "EVALUATOR_GROUPS",
    "PANEL_DIMENSIONS",
    "PANEL_PROTOCOL_REVISION",
    "PANEL_RUBRIC",
    "PANEL_RUBRIC_SHA256",
    "PANEL_VERSION",
    "adjudicatePanel",
    "checkedAdjudication",
    "checkedJudgePredictions",
    "checkedPanelSuite",
    "checkedPanelTrialSet",
    "evaluatePanelJudge",
    "loadPanelTrialSet",
    "preparePanelJudgeCases",
    "preparePanelSuite",
    "preparePanelTrialSet",
    "recordPanelReviewBatch",
    "revealPanel",
    "summarizePanelJudgeConsistency",
]

from .review import (  # noqa: E402
    ASSIGNMENT_KIND,
    ASSIGNMENT_REVIEW_KIND,
    checkedPanelAssignment,
    preparePanelAssignment,
    preparePanelReviewHtml,
    recordPanelAssignmentReview,
    renderPanelReviewHtml,
)

__all__ += [
    "ASSIGNMENT_KIND",
    "ASSIGNMENT_REVIEW_KIND",
    "checkedPanelAssignment",
    "preparePanelAssignment",
    "preparePanelReviewHtml",
    "recordPanelAssignmentReview",
    "renderPanelReviewHtml",
]
