"""오프라인 사람 평가 작업대가 정체성·순서·네트워크와 가짜 label을 흘리지 않게 막는다."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from scripts.exportData import render as renderNpmData

from hanlint import checkedPanelAssignment, loadPanelTrialSet, preparePanelAssignment, preparePanelSuite, renderPanelReviewHtml

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "src" / "hanlint" / "data" / "writingArenaPilotV1.json"
PAGE = ROOT / "src" / "hanlint" / "data" / "panelReviewPage.html"


def pilotSuite() -> dict:
    trialSet = loadPanelTrialSet(PILOT)
    return preparePanelSuite(trialSet["trials"], trialSet["studyId"], 20260831)


def nestedKeys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(nestedKeys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(nestedKeys(item) for item in value))
    return set()


def testAssignmentHasNoIdentityOrderOrPrefilledQualityLabel():
    suite = pilotSuite()
    assignment = preparePanelAssignment(suite, "reviewer-gate", "targetReader")
    assert not (
        nestedKeys(assignment)
        & {
            "seed",
            "trialSha256",
            "sourceBlindSha256",
            "sourceCaseSha256",
            "candidateStrategyId",
            "internalOrder",
            "otherReviews",
        }
    )
    rendered = json.dumps(assignment, ensure_ascii=False)
    assert suite["suiteId"] not in rendered
    assert all(panelCase["caseId"] not in rendered for panelCase in suite["cases"])
    assert suite["cases"][0]["trialSha256"] not in rendered
    assert suite["cases"][0]["sourceBlindSha256"] not in rendered
    for review in assignment["reviewTemplate"]["reviews"]:
        assert set(review["contentChecks"].values()) == {""}
        assert set(review["preferences"].values()) == {""}


def testReviewPageAllowsNoExternalChannelOrUnsafeHtmlSink():
    source = PAGE.read_text(encoding="utf-8")
    assert source.count("__HANLINT_ASSIGNMENT__") == 1
    assert source.count("<script") == 2
    assert "connect-src 'none'" in source and "default-src 'none'" in source
    for forbidden in ("<script src=", "fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon", "innerHTML"):
        assert forbidden not in source
    assert "https://" not in source and "http://" not in source
    assert "localStorage" in source and "assignment.assignmentSha256" in source
    assert "Object.hasOwn" in source and 'aria-live="polite"' in source
    assert 'review.preferences[dimension] === "cannotJudge" && dimension !== "voice"' not in source
    identifiers = re.findall(r' id="([^"]+)"', source)
    assert len(identifiers) == len(set(identifiers))
    assert '<html lang="ko">' in source and 'href="#reviewMain"' in source
    assert "event.altKey" in source and "ArrowLeft" in source and "ArrowRight" in source
    assert 'tabindex="1"' not in source and "prefers-reduced-motion" in source


def testRenderedPageKeepsPilotIdentityAndOtherReviewsOut():
    suite = pilotSuite()
    assignment = preparePanelAssignment(suite, "reviewer-page-gate", "professionalEditor")
    rendered = renderPanelReviewHtml(suite, assignment)
    hiddenValues = {suite["cases"][0]["trialSha256"], suite["cases"][0]["sourceBlindSha256"]}
    assert all(value not in rendered for value in hiddenValues)
    assert "recordedPanelReviewBatch" not in rendered and "batchSha256" not in rendered
    assert "contextFirstV1" not in rendered and "plainBrief" not in rendered


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data["cases"][0]["comparison"].update(left="변조한 글"),
        lambda data: data["cases"][0].update(assignmentCaseSha256="0" * 64),
        lambda data: data["evaluator"].update(id="다른-평가자"),
        lambda data: data["source"].update(cases=0),
    ],
)
def testAssignmentLeakAndTamperGateHasTeeth(change):
    suite = pilotSuite()
    assignment = preparePanelAssignment(suite, "reviewer-tamper-gate", "koreanExpert")
    changed = deepcopy(assignment)
    change(changed)
    with pytest.raises(ValueError):
        checkedPanelAssignment(suite, changed)


def testAssignmentReviewSchemaProjectsToNpm():
    projected = renderNpmData()
    assert "panelAssignmentReview.schema.json" in projected
    schema = json.loads(projected["panelAssignmentReview.schema.json"])
    assert schema["properties"]["kind"]["const"] == "hanlint.panelAssignmentReview"
    assert schema["properties"]["reviews"]["minItems"] == 1
    reviewItem = schema["properties"]["reviews"]["items"]
    assert reviewItem["allOf"][0]["then"]["properties"]["preferences"]["properties"]["voice"] == {"const": "cannotJudge"}
