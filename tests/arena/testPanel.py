import json
from copy import deepcopy
from hashlib import sha256

import pytest

from hanlint.arena import WritingTrial, candidateIsLeft, stableDigest
from hanlint.arena.panel import (
    PANEL_DIMENSIONS,
    PANEL_PROTOCOL_REVISION,
    PANEL_RUBRIC_SHA256,
    adjudicatePanel,
    checkedAdjudication,
    checkedJudgePredictions,
    checkedPanelSuite,
    checkedPanelTrialSet,
    evaluatePanelJudge,
    preparePanelJudgeCases,
    preparePanelSuite,
    preparePanelTrialSet,
    recordPanelReviewBatch,
    revealPanel,
    summarizePanelJudgeConsistency,
)

BASELINE = (
    "# 해솔 계획\n\n해솔 계획은 2026년 8월 31일 시작하며 예산은 380,000원이다. 운영자는 두 값을 보고 다음 확인 순서를 정한다.\n"
)
CANDIDATE = "# 해솔 계획\n\n운영자는 해솔 계획의 시작일인 2026년 8월 31일과 예산 380,000원을 확인한 뒤 다음 확인 순서를 정한다.\n"


def generation(strategyId: str, text: str) -> dict:
    return {
        "strategyId": strategyId,
        "modelId": "qwen3:8b",
        "modelSha256": "a" * 64,
        "promptSha256": "b" * 64,
        "outputSha256": sha256(text.encode()).hexdigest(),
        "text": text,
    }


def trialMapping(identifier: str, preset: str = "report", candidate: str = CANDIDATE) -> dict:
    return {
        "version": 1,
        "id": identifier,
        "brief": {
            "version": 1,
            "preset": preset,
            "reader": "다음 확인 순서를 정할 운영자",
            "task": "해솔 계획의 두 관찰값을 읽고 다음 확인 순서를 정한다",
            "facts": [
                {"id": "F1", "statement": "해솔 계획은 2026년 8월 31일 시작한다."},
                {"id": "F2", "statement": "해솔 계획의 예산은 380,000원이다."},
            ],
            "mustInclude": ["해솔 계획", "2026년 8월 31일", "380,000원"],
            "allowedNumbers": ["2026", "31", "380000", "8"],
            "forbidden": ["효과가 입증됐다"],
            "length": {"min": 70, "max": 300},
        },
        "baseline": generation("plainBrief", BASELINE),
        "candidate": generation("panelStrategyV1", candidate),
    }


def candidateChoice(trial: WritingTrial, panelCase: dict) -> str:
    return "left" if candidateIsLeft(trial, panelCase["seed"]) else "right"


def opposite(choice: str) -> str:
    return "right" if choice == "left" else "left"


def rawBatch(suite: dict, evaluatorId: str, choices: dict[str, dict[str, str]]) -> dict:
    cases = {item["caseId"]: item for item in suite["cases"]}
    reviews = []
    for caseId, preferences in choices.items():
        reviews.append(
            {
                "caseId": caseId,
                "caseSha256": cases[caseId]["caseSha256"],
                "contentChecks": {"left": "pass", "right": "pass"},
                "preferences": preferences,
                "reasons": {
                    "content": "두 글의 사실과 숫자를 요구와 대조했다.",
                    "naturalness": "문장 흐름이 덜 걸리는 쪽을 골랐다.",
                    "clarity": "대상과 행동의 관계를 비교했다.",
                    "taskUtility": "운영자가 다음 순서를 정할 수 있는지 봤다.",
                    "voice": "표본이 없으면 판단하지 않았고 있으면 종결과 밀도를 비교했다.",
                },
            }
        )
    return {
        "version": 1,
        "kind": "hanlint.panelReviewBatch",
        "suiteSha256": suite["suiteSha256"],
        "rubricSha256": PANEL_RUBRIC_SHA256,
        "evaluator": {
            "id": evaluatorId,
            "group": "targetReader",
            "protocolRevision": PANEL_PROTOCOL_REVISION,
        },
        "reviews": reviews,
    }


def reviewedSuite() -> tuple[list[WritingTrial], dict, list[dict]]:
    trials = [
        WritingTrial.fromMapping(trialMapping("report-01")),
        WritingTrial.fromMapping(trialMapping("report-02")),
    ]
    suite = preparePanelSuite(trials, "panel-test", 42)
    first, second = suite["cases"]
    firstCandidate = candidateChoice(trials[0], first)
    secondCandidate = candidateChoice(trials[1], second)
    firstOther = opposite(firstCandidate)
    secondOther = opposite(secondCandidate)
    batches = []
    for index in range(3):
        firstChoice = firstCandidate if index < 2 else firstOther
        secondChoice = secondOther if index < 2 else secondCandidate
        choices = {
            "report-01": {
                "naturalness": firstChoice,
                "clarity": "tie",
                "taskUtility": firstChoice,
                "voice": "cannotJudge",
            },
            "report-02": {
                "naturalness": secondChoice,
                "clarity": secondChoice,
                "taskUtility": "tie",
                "voice": "cannotJudge",
            },
        }
        batches.append(recordPanelReviewBatch(suite, rawBatch(suite, f"reviewer-{index + 1}", choices)))
    return trials, suite, batches


def testPanelSuiteAddsEvaluationContextHidesIdentityAndBalancesSides():
    trials = [
        WritingTrial.fromMapping(trialMapping("report-01")),
        WritingTrial.fromMapping(trialMapping("report-02")),
    ]
    suite = preparePanelSuite(trials, "panel-test", 42)
    assert checkedPanelSuite(suite) == suite
    assert sum(candidateIsLeft(trial, case["seed"]) for trial, case in zip(trials, suite["cases"], strict=True)) == 1
    assert len(suite["cases"]) == 2 and not suite["excluded"]
    assert len(suite["reviewTemplate"]["reviews"]) == 2
    assert suite["reviewTemplate"]["reviews"][0]["caseId"] == suite["cases"][0]["caseId"]
    shown = json.dumps(suite, ensure_ascii=False)
    assert "qwen3:8b" not in shown and "panelStrategyV1" not in shown and "plainBrief" not in shown
    context = suite["cases"][0]["context"]
    assert context["reader"] and context["task"] and len(context["facts"]) == 2
    assert context["voiceReference"] is None and suite["source"]["containsReferenceText"] is False


def testPanelTrialSetPinsProvenanceWithoutInventingQualityLabels():
    data = preparePanelTrialSet(
        "writing-arena-test",
        [trialMapping("report-01")],
        {
            "origin": "syntheticProtocolFixture",
            "license": "MIT",
            "containsExternalReferenceText": False,
            "qualityLabels": False,
        },
    )
    assert checkedPanelTrialSet(data) == data
    assert data["provenance"]["qualityLabels"] is False
    broken = deepcopy(data)
    broken["provenance"]["qualityLabels"] = True
    with pytest.raises(ValueError, match="품질 label"):
        checkedPanelTrialSet(broken)


def testPanelSuiteExcludesUnsafeTrialBeforePeopleSeeTheText():
    unsafe = "# 해솔 계획\n\n해솔 계획을 확인한다.\n"
    suite = preparePanelSuite([trialMapping("unsafe-01", candidate=unsafe)], "unsafe-suite", 8)
    assert not suite["cases"] and len(suite["excluded"]) == 1
    shown = json.dumps(suite, ensure_ascii=False)
    assert unsafe not in shown and suite["excluded"][0]["safetyOutcome"] == "baselineSafeWin"


def testPanelSuiteBalancesOnlyCasesThatPeopleCanActuallySee():
    unsafe = trialMapping("unsafe-01", candidate="# 해솔 계획\n\n해솔 계획을 확인한다.\n")
    mappings = [unsafe, trialMapping("report-01"), trialMapping("report-02")]
    trials = [WritingTrial.fromMapping(item) for item in mappings]
    suite = preparePanelSuite(trials, "visible-balance", 8)
    visible = {trial.id: trial for trial in trials if trial.id != "unsafe-01"}
    assert len(suite["cases"]) == 2 and len(suite["excluded"]) == 1
    assert sum(candidateIsLeft(visible[case["caseId"]], case["seed"]) for case in suite["cases"]) == 1


def testReviewBatchRequiresContextSafeChoicesAndRealReasons():
    trial = WritingTrial.fromMapping(trialMapping("report-01"))
    suite = preparePanelSuite([trial], "panel-test", 42)
    side = candidateChoice(trial, suite["cases"][0])
    choices = {
        "report-01": {
            "naturalness": side,
            "clarity": "tie",
            "taskUtility": side,
            "voice": "cannotJudge",
        }
    }
    recorded = recordPanelReviewBatch(suite, rawBatch(suite, "reviewer-1", choices))
    assert len(recorded["batchSha256"]) == 64
    broken = rawBatch(suite, "reviewer-2", choices)
    broken["reviews"][0]["contentChecks"]["left"] = "fail"
    with pytest.raises(ValueError, match="모든 선호"):
        recordPanelReviewBatch(suite, broken)
    broken = rawBatch(suite, "reviewer-2", choices)
    broken["reviews"][0]["reasons"]["clarity"] = "<required>"
    with pytest.raises(ValueError, match="실제 근거"):
        recordPanelReviewBatch(suite, broken)


def testAdjudicationKeepsConsensusCountsAndAgreementSeparate():
    _, suite, batches = reviewedSuite()
    adjudication = adjudicatePanel(suite, batches)
    assert adjudication["evaluators"] == 3
    assert adjudication["cases"][0]["preferences"]["counts"]["naturalness"]
    assert adjudication["cases"][0]["preferences"]["consensus"]["clarity"] == "tie"
    assert adjudication["agreement"]["method"] == "KrippendorffAlphaNominal"
    assert adjudication["agreement"]["preferences"]["naturalness"]["ratings"] == 6
    with pytest.raises(ValueError, match="evaluator id"):
        adjudicatePanel(suite, [batches[0], batches[0]])
    with pytest.raises(ValueError, match="최소 3명"):
        adjudicatePanel(suite, batches[:2])
    broken = deepcopy(adjudication)
    broken["cases"][0]["preferences"]["counts"]["naturalness"]["left"] += 1
    broken["adjudicationSha256"] = stableDigest({key: value for key, value in broken.items() if key != "adjudicationSha256"})
    with pytest.raises(ValueError, match="humanReviews"):
        checkedAdjudication(suite, broken)


def testRevealMapsHiddenSidesAndReturnsBootstrapIntervalsWithoutACompositeScore():
    trials, suite, batches = reviewedSuite()
    adjudication = adjudicatePanel(suite, batches)
    result = revealPanel(trials, suite, adjudication)
    assert result["dimensions"]["naturalness"]["candidate"] == 1
    assert result["dimensions"]["naturalness"]["baseline"] == 1
    assert result["dimensions"]["naturalness"]["candidatePreferenceShare"] == 0.5
    assert result["dimensions"]["naturalness"]["candidatePreferenceShareCi95"]["iterations"] == 5000
    assert "overall" not in result and "score" not in result


def oraclePredictions(suite: dict, adjudication: dict) -> tuple[dict, dict]:
    judgeCases = preparePanelJudgeCases(suite)
    human = {item["caseId"]: item for item in adjudication["cases"]}
    predictions = []
    for presentation in judgeCases["presentations"]:
        source = human[presentation["caseId"]]
        reversedOrder = presentation["order"] == "reversed"

        def shownSide(choice: str, isReversed: bool = reversedOrder) -> str:
            if not isReversed or choice not in ("left", "right"):
                return choice
            return opposite(choice)

        content = {}
        for side in ("left", "right"):
            sourceSide = opposite(side) if reversedOrder else side
            choice = source["content"]["consensus"][sourceSide]
            content[side] = {"choice": choice if choice in ("pass", "fail") else "abstain", "confidence": 1.0}
        preferences = {}
        for dimension in PANEL_DIMENSIONS:
            choice = source["preferences"]["consensus"][dimension]
            choice = shownSide(choice) if choice in ("left", "right", "tie") else "abstain"
            preferences[dimension] = {"choice": choice, "confidence": 0.0 if choice == "abstain" else 1.0}
        predictions.append(
            {
                "presentationId": presentation["presentationId"],
                "presentationSha256": presentation["presentationSha256"],
                "contentChecks": content,
                "preferences": preferences,
            }
        )
    payload = {
        "version": 1,
        "kind": "hanlint.panelJudgePredictions",
        "judgeCasesSha256": judgeCases["judgeCasesSha256"],
        "evaluatorId": "oracle-test",
        "evaluatorRevision": "c" * 64,
        "promptSha256": "d" * 64,
        "predictions": predictions,
    }
    return judgeCases, payload


def testJudgeCalibrationUsesBothOrdersAndHumanConsensusWithoutLeakingIt():
    _, suite, batches = reviewedSuite()
    adjudication = adjudicatePanel(suite, batches)
    judgeCases, predictions = oraclePredictions(suite, adjudication)
    assert "consensus" not in json.dumps(judgeCases, ensure_ascii=False)
    checkedJudgePredictions(judgeCases, predictions)
    result = evaluatePanelJudge(suite, adjudication, judgeCases, predictions)
    assert result["content"]["selectedAccuracy"] == 1.0
    assert result["preferences"]["naturalness"]["selectedAccuracy"] == 1.0
    assert result["preferences"]["naturalness"]["coverage"] == 1.0
    assert result["positionConsistency"]["preferences"]["naturalness"]["consistency"] == 1.0
    assert result["preferences"]["voice"]["total"] == 0
    consistency = summarizePanelJudgeConsistency(suite, judgeCases, predictions)
    assert consistency["positionConsistency"]["content"]["usableCoverage"] == 1.0
    assert consistency["positionConsistency"]["preferences"]["naturalness"]["consistency"] == 1.0
    assert "사람 합의 없이" in consistency["claimBoundary"]


def testPositionDisagreementBecomesAbstentionInsteadOfAHiddenVote():
    _, suite, batches = reviewedSuite()
    adjudication = adjudicatePanel(suite, batches)
    judgeCases, predictions = oraclePredictions(suite, adjudication)
    firstForward = next(item for item in predictions["predictions"] if item["presentationId"].endswith(":forward"))
    firstReversed = next(
        item
        for item in predictions["predictions"]
        if item["presentationId"] == firstForward["presentationId"].replace(":forward", ":reversed")
    )
    firstReversed["preferences"]["naturalness"] = deepcopy(firstForward["preferences"]["naturalness"])
    result = evaluatePanelJudge(suite, adjudication, judgeCases, predictions)
    assert result["preferences"]["naturalness"]["answered"] == 1
    assert result["preferences"]["naturalness"]["abstained"] == 1
    assert result["positionConsistency"]["preferences"]["naturalness"]["consistency"] == 0.5


def testPanelHashesRejectTamperingAndMovingJudgeIdentity():
    _, suite, batches = reviewedSuite()
    adjudication = adjudicatePanel(suite, batches)
    broken = deepcopy(suite)
    broken["cases"][0]["comparison"]["left"] += " 바꿈"
    with pytest.raises(ValueError, match="caseSha256"):
        checkedPanelSuite(broken)
    judgeCases, predictions = oraclePredictions(suite, adjudication)
    predictions["evaluatorRevision"] = "0" * 64
    with pytest.raises(ValueError, match="실제 고정 모델"):
        checkedJudgePredictions(judgeCases, predictions)
