import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from hanlint import (
    PANEL_DIMENSIONS,
    checkedPanelAssignment,
    loadPanelTrialSet,
    preparePanelAssignment,
    preparePanelReviewHtml,
    preparePanelSuite,
    recordPanelAssignmentReview,
    renderPanelReviewHtml,
)
from hanlint.arena.review import scriptJson

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "src" / "hanlint" / "data" / "writingArenaPilotV1.json"


def pilotSuite() -> dict:
    trialSet = loadPanelTrialSet(PILOT)
    return preparePanelSuite(trialSet["trials"], trialSet["studyId"], 20260831)


def filledReview(assignment: dict, preference: str = "left") -> dict:
    data = deepcopy(assignment["reviewTemplate"])
    for review in data["reviews"]:
        review["contentChecks"] = {"left": "pass", "right": "pass"}
        review["preferences"] = {
            "naturalness": preference,
            "clarity": "right",
            "taskUtility": "tie",
            "voice": "cannotJudge",
        }
        review["reasons"] = {
            "content": "두 글을 원자 사실과 수치에 각각 대조했다.",
            "naturalness": "문장 흐름이 덜 걸리는 자리를 비교했다.",
            "clarity": "대상과 행동의 관계가 드러나는 쪽을 골랐다.",
            "taskUtility": "독자가 과업을 끝낼 수 있는지 비교했다.",
            "voice": "목소리 표본이 없어 판단하지 않았다.",
        }
    return data


def testAssignmentShowsOneBalancedOrderWithoutIdentityOrInternalOrderMetadata():
    suite = pilotSuite()
    first = preparePanelAssignment(suite, "reviewer-1", "targetReader")
    assert checkedPanelAssignment(suite, first) == first
    shown = json.dumps(first, ensure_ascii=False).casefold()
    for hidden in ("contextfirstv1", "plainbrief", "hanlint.protocolfixture", "candidate", "forward", "reversed"):
        assert hidden not in shown
    # 재야 할 것은 suite 대비 뒤집힌 사례 수가 아니라 **후보가 왼쪽에 온 사례 수** 다. suite 가 이미
    # 좌우를 번갈아 놓으므로 하나 걸러 뒤집으면 뒤집힌 수는 3이나 4로 나오면서 후보 위치는 상수가 된다.
    # 그 구멍으로 한 평가자가 모든 사례에서 후보를 같은 쪽으로만 보던 결함이 초록으로 지나갔다 (2026-08-31).
    trialSet = loadPanelTrialSet(PILOT)
    candidateText = {trial["id"]: trial["candidate"]["text"] for trial in trialSet["trials"]}
    for evaluator in ("reviewer-1", "reviewer-2", "reviewer-3", "reviewer-4"):
        assignment = preparePanelAssignment(suite, evaluator, "targetReader")
        onLeft = [
            assigned["comparison"]["left"] == candidateText[source["caseId"]]
            for assigned, source in zip(assignment["cases"], suite["cases"], strict=True)
        ]
        assert 0 < sum(onLeft) < len(onLeft), f"{evaluator} 가 후보를 한쪽에서만 본다: {onLeft}"
    assert [item["caseId"] for item in first["cases"]] == [f"case-{index:03d}" for index in range(1, 8)]
    assert first["studyCode"] == f"panel-{suite['suiteSha256'][:12]}"
    variants = {
        preparePanelAssignment(suite, f"reviewer-{index}", "professionalEditor")["cases"][0]["comparison"]["left"]
        for index in range(1, 9)
    }
    assert len(variants) == 2
    assert len(first["reviewTemplate"]["reviews"]) == 7


def testAssignmentReviewReturnsToSuiteSidesBeforeExistingBatchIsLocked():
    suite = pilotSuite()
    assignment = preparePanelAssignment(suite, "reviewer-map", "koreanExpert")
    raw = filledReview(assignment)
    recorded = recordPanelAssignmentReview(suite, assignment, raw)
    assert recorded["kind"] == "hanlint.recordedPanelReviewBatch" and len(recorded["reviews"]) == 7
    for panelCase, assignedCase, review in zip(suite["cases"], assignment["cases"], recorded["reviews"], strict=True):
        wasReversed = panelCase["comparison"]["left"] != assignedCase["comparison"]["left"]
        assert review["preferences"]["naturalness"] == ("right" if wasReversed else "left")
        assert review["preferences"]["clarity"] == ("left" if wasReversed else "right")
        assert review["preferences"]["taskUtility"] == "tie"


def testAssignmentReviewRejectsTamperingMissingCasesAndContentPreferenceConflict():
    suite = pilotSuite()
    assignment = preparePanelAssignment(suite, "reviewer-guard", "generalReader")
    brokenAssignment = deepcopy(assignment)
    brokenAssignment["cases"][0]["comparison"]["left"] += " 변조"
    with pytest.raises(ValueError, match="고정 결과"):
        checkedPanelAssignment(suite, brokenAssignment)
    raw = filledReview(assignment)
    raw["reviews"].pop()
    with pytest.raises(ValueError, match="빠진 case"):
        recordPanelAssignmentReview(suite, assignment, raw)
    raw = filledReview(assignment)
    raw["reviews"][0]["contentChecks"]["left"] = "fail"
    with pytest.raises(ValueError, match="모든 선호"):
        recordPanelAssignmentReview(suite, assignment, raw)


def testReviewHtmlIsDeterministicSelfContainedAndCarriesNoAnswers():
    suite = pilotSuite()
    assignment = preparePanelAssignment(suite, "reviewer-page", "targetReader")
    html = renderPanelReviewHtml(suite, assignment)
    assert html == preparePanelReviewHtml(suite, "reviewer-page", "targetReader")
    assert html.startswith("<!doctype html>") and html.endswith("</html>\n")
    assert "Content-Security-Policy" in html and "connect-src 'none'" in html
    assert "<script src=" not in html and "fetch(" not in html and "XMLHttpRequest" not in html
    assert "localStorage" in html and 'aria-live="polite"' in html and 'role="progressbar"' in html
    assert "hanlint.panelAssignmentReview" in html and "assignmentCaseSha256" in html
    assert "contextFirstV1" not in html and "plainBrief" not in html and "panelReviewBatch" not in html
    assert suite["suiteId"] not in html and all(panelCase["caseId"] not in html for panelCase in suite["cases"])
    for panelCase in assignment["cases"]:
        assert panelCase["comparison"]["left"].splitlines()[0] in html
        assert panelCase["comparison"]["right"].splitlines()[0] in html


def testReviewHtmlEscapesClosingScriptFromAssignmentText():
    rendered = scriptJson({"text": "</script><img src=x>&"})
    assert "</script>" not in rendered and "<img" not in rendered and "&" not in rendered
    assert "\\u003c/script\\u003e" in rendered and "\\u0026" in rendered


def testAssignmentRejectsSuiteWithNoSafeComparison():
    trialSet = loadPanelTrialSet(PILOT)
    trials = deepcopy(trialSet["trials"])
    for trial in trials:
        text = trial["candidate"]["text"] + "\n요구 밖 수치 999999"
        trial["candidate"]["text"] = text
        trial["candidate"]["outputSha256"] = sha256(text.encode()).hexdigest()
    suite = preparePanelSuite(trials, "empty-review-suite", 3)
    assert suite["cases"] == []
    with pytest.raises(ValueError, match="case가 하나 이상"):
        preparePanelAssignment(suite, "reviewer-empty", "targetReader")


def testPanelDimensionsStayExactlyAlignedWithReviewPageContract():
    assert PANEL_DIMENSIONS == ("naturalness", "clarity", "taskUtility", "voice")
