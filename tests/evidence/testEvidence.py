import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from hanlint import EvidenceRecord, WritingBrief, evidenceLedger, guardText, writingPacket
from hanlint.evidence import EVIDENCE_MEANING

ROOT = Path(__file__).resolve().parents[2]


def evidenceBrief() -> dict:
    firstExcerpt = "해솔 계획의 시작일은 2026년 8월 31일이다."
    secondExcerpt = "승인된 예산 합계는 380,000원이다."
    return {
        "version": 2,
        "preset": "report",
        "reader": "결정할 운영자",
        "task": "관찰값을 읽고 다음 조치를 고른다",
        "facts": [
            {"id": "F1", "statement": "해솔 계획은 2026년 8월 31일 시작한다."},
            {"id": "F2", "statement": "예산은 380,000원이다."},
        ],
        "mustInclude": ["해솔 계획", "380,000원"],
        "allowedNumbers": ["2026", "31", "380000", "8"],
        "forbidden": ["효과가 입증됐다"],
        "length": {"min": 50, "max": 500},
        "evidence": [
            {
                "id": "E1",
                "factIds": ["F1"],
                "sourceUrl": "https://example.invalid/plans/haesol",
                "revision": "rev-7f31",
                "checkedAt": None,
                "locator": "표 2, 시작일",
                "excerpt": firstExcerpt,
                "excerptSha256": sha256(firstExcerpt.encode()).hexdigest(),
                "license": "internal-approved",
                "reviewStatus": "humanVerified",
            },
            {
                "id": "E2",
                "factIds": ["F2"],
                "sourceUrl": "https://example.invalid/budgets/haesol",
                "revision": None,
                "checkedAt": "2026-08-31T03:00:00Z",
                "locator": "합계 행",
                "excerpt": secondExcerpt,
                "excerptSha256": sha256(secondExcerpt.encode()).hexdigest(),
                "license": "internal-approved",
                "reviewStatus": "unreviewed",
            },
        ],
    }


def testV2LoadsAClosedEvidenceLedgerAndKeepsFactTextSeparate():
    brief = WritingBrief.fromMapping(evidenceBrief())
    assert brief.version == 2 and len(brief.evidence) == 2
    assert isinstance(brief.evidence[0], EvidenceRecord)
    assert (
        brief.text
        == "결정할 운영자\n관찰값을 읽고 다음 조치를 고른다\n해솔 계획은 2026년 8월 31일 시작한다.\n예산은 380,000원이다."
    )
    assert brief.asDict() == evidenceBrief()
    result = evidenceLedger(brief)
    assert result.ledgerValid and result.factEvidence == {"F1": ("E1",), "F2": ("E2",)}
    assert result.humanVerifiedRecords == 1 and result.asDict()["meaning"] == EVIDENCE_MEANING
    reordered = evidenceBrief()
    reordered["evidence"].reverse()
    assert WritingBrief.fromMapping(reordered).digest == brief.digest


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data["evidence"].pop(), "근거 기록이 없는 fact"),
        (lambda data: data["evidence"][0].update(factIds=["F9"]), "없는 fact"),
        (lambda data: data["evidence"][0].update(excerpt="바뀐 조각"), "excerpt와 다르다"),
        (lambda data: data["evidence"][0].update(revision=None, checkedAt=None), "출처 판을 고정"),
        (lambda data: data["evidence"][0].update(revision="latest"), "고정 판"),
        (lambda data: data["evidence"][1].update(checkedAt="2026-02-31T03:00:00Z"), "실제 UTC"),
        (lambda data: data["evidence"][0].update(license=""), "license"),
        (lambda data: data["evidence"][0].pop("license"), "license"),
        (lambda data: data["evidence"][1].update(id="E1"), "id가 겹친다"),
    ],
)
def testRejectsMissingOrTamperedEvidence(change, message):
    data = evidenceBrief()
    change(data)
    result = evidenceLedger(data)
    assert not result.ledgerValid and message in result.violations[0]
    with pytest.raises(ValueError, match=message):
        WritingBrief.fromMapping(data)


def testV1HasNoEvidenceSurfaceAndIsReportedWithoutChangingItsContract():
    data = evidenceBrief()
    data["version"] = 1
    data.pop("evidence")
    brief = WritingBrief.fromMapping(data)
    assert "evidence" not in brief.asDict() and brief.evidence == ()
    result = evidenceLedger(brief)
    assert not result.ledgerValid and "version 2" in result.violations[0]


def testEvidenceApiRevalidatesAHandBuiltBrief():
    brief = replace(WritingBrief.fromMapping(evidenceBrief()), evidence=())
    result = evidenceLedger(brief)
    assert not result.ledgerValid and "evidence" in result.violations[0]


def testV2PacketScopesEvidenceAndGuardStillUsesOnlyFactSurface():
    brief = WritingBrief.fromMapping(evidenceBrief())
    packet = writingPacket(brief, purpose="draft")
    constraints = packet["contract"]["constraints"]
    assert packet["input"]["brief"]["evidence"] == evidenceBrief()["evidence"]
    assert any("다른 fact의 재료로 확산하지 않는다" in item for item in constraints)
    assert any("참이라는 판정이 아니다" in item for item in constraints)
    draft = "# 결정\n\n해솔 계획은 2026년 8월 31일 시작하고 예산은 380,000원이다. 운영자는 다음 조치를 고른다.\n"
    assert guardText(brief, draft).contractSatisfied


def testPublishedV2SchemaNamesTheEvidenceBoundary():
    schema = json.loads((ROOT / "src" / "hanlint" / "data" / "writingBriefV2.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["version"]["const"] == 2
    evidence = schema["properties"]["evidence"]["items"]
    assert set(evidence["required"]) == set(evidence["properties"])
    assert evidence["properties"]["reviewStatus"]["enum"] == ["unreviewed", "humanVerified"]
