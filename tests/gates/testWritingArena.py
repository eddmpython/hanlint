"""writingArena fixture가 사람 품질 정답을 꾸미거나 블라인드 정체성을 흘리지 않게 막는다."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from scripts.buildWritingArenaPilot import render as renderPilot
from scripts.exportData import render as renderNpmData

from hanlint import checkedPanelTrialSet, preparePanelSuite

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "src" / "hanlint" / "data" / "writingArenaPilotV1.json"


def pilotData() -> dict:
    return json.loads(PILOT.read_text(encoding="utf-8"))


def testWritingArenaPilotPinsSevenGenresWithoutQualityGold():
    data = checkedPanelTrialSet(pilotData())
    assert {trial["brief"]["preset"] for trial in data["trials"]} == {
        "blog",
        "report",
        "docs",
        "guide",
        "essay",
        "fiction",
        "encyclopedia",
    }
    assert data["provenance"] == {
        "origin": "syntheticProtocolFixture",
        "license": "MIT",
        "containsExternalReferenceText": False,
        "qualityLabels": False,
    }
    assert PILOT.read_text(encoding="utf-8") == renderPilot()


def testWritingArenaBlindSuiteHidesIdentityAndKeepsEveryFixtureEligible():
    data = pilotData()
    suite = preparePanelSuite(data["trials"], data["studyId"], 20260831)
    assert suite["source"] == {
        "trials": 7,
        "eligibleCases": 7,
        "excludedCases": 0,
        "containsReferenceText": False,
    }
    shown = json.dumps(suite, ensure_ascii=False)
    for hidden in ("contextFirstV1", "plainBrief", "hanlint.protocolFixture", "candidateLeft"):
        assert hidden not in shown


def testWritingArenaSchemasProjectButProtocolFixtureDoesNot():
    projected = renderNpmData()
    assert "writingArenaPilotV1.json" not in projected
    assert {
        "panelTrialSet.schema.json",
        "panelReviewBatch.schema.json",
        "panelAssignmentReview.schema.json",
        "panelJudgePredictions.schema.json",
    } <= set(projected)


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data["provenance"].update(qualityLabels=True),
        lambda data: data["trials"][0]["candidate"].update(text="변조한 글"),
        lambda data: data.update(trialSetSha256="0" * 64),
    ],
)
def testWritingArenaDataGateHasTeeth(change):
    data = deepcopy(pilotData())
    change(data)
    with pytest.raises(ValueError):
        checkedPanelTrialSet(data)
