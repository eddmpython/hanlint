"""원자 사실과 고정 근거 기록의 연결을 진실 판정 없이 검증한다."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import EVIDENCE_BRIEF_VERSION, WritingBrief

EVIDENCE_MEANING = (
    "ledgerValid는 근거 연결, 출처 판, 조각 해시와 라이선스가 형식상 맞는다는 뜻뿐이다. "
    "URL 존재, 인용 조각의 진위와 사실의 진실·함의를 보장하지 않는다"
)


@dataclass(frozen=True)
class EvidenceLedgerResult:
    ledgerValid: bool
    briefVersion: int | None
    briefSha256: str | None
    factEvidence: dict[str, tuple[str, ...]]
    evidenceRecords: int
    humanVerifiedRecords: int
    violations: tuple[str, ...]

    def asDict(self) -> dict:
        return {
            "version": 1,
            "kind": "hanlint.evidenceLedgerResult",
            "ledgerValid": self.ledgerValid,
            "briefVersion": self.briefVersion,
            "briefSha256": self.briefSha256,
            "factEvidence": {factId: list(evidenceIds) for factId, evidenceIds in self.factEvidence.items()},
            "evidenceRecords": self.evidenceRecords,
            "humanVerifiedRecords": self.humanVerifiedRecords,
            "violations": list(self.violations),
            "meaning": EVIDENCE_MEANING,
        }


def evidenceLedger(brief: WritingBrief | dict) -> EvidenceLedgerResult:
    """v2 brief의 근거 원장을 검증하고 사실별 연결을 결정적인 순서로 낸다."""
    if isinstance(brief, (WritingBrief, dict)):
        raw = brief.asDict() if isinstance(brief, WritingBrief) else brief
        rawVersion = raw.get("version")
        version = rawVersion if isinstance(rawVersion, int) and not isinstance(rawVersion, bool) else None
        try:
            brief = WritingBrief.fromMapping(raw)
        except (AttributeError, TypeError, ValueError) as error:
            return EvidenceLedgerResult(False, version, None, {}, 0, 0, (str(error),))
    if not isinstance(brief, WritingBrief):
        raise ValueError("evidenceLedger 입력은 WritingBrief 또는 brief JSON 객체다")
    if brief.version != EVIDENCE_BRIEF_VERSION:
        return EvidenceLedgerResult(
            False,
            brief.version,
            brief.digest,
            {},
            0,
            0,
            (f"근거 원장은 writing brief version {EVIDENCE_BRIEF_VERSION}에서만 쓴다",),
        )
    factEvidence = {fact.id: tuple(record.id for record in brief.evidence if fact.id in record.factIds) for fact in brief.facts}
    return EvidenceLedgerResult(
        True,
        brief.version,
        brief.digest,
        factEvidence,
        len(brief.evidence),
        sum(record.reviewStatus == "humanVerified" for record in brief.evidence),
        (),
    )


__all__ = ["EVIDENCE_MEANING", "EvidenceLedgerResult", "evidenceLedger"]
