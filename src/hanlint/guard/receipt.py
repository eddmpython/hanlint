"""Reader Contract 검사와 Patch 검증의 결정적 영수증."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ..rules import Finding
from .outline import DocumentSummary, OutlineDiff
from .surface import SurfaceDiff

CHECK_MEANING = (
    "violationCount는 선언한 보호 원자와 hanlint error의 수다. "
    "facts의 관계와 진실, 빠진 의미, 독자 효용과 자연스러움은 검증하지 않는다"
)
CHECK_MEANING_V2 = (
    "violationCount는 선언한 보호 원자, 제목 구조와 hanlint error의 수다. "
    "facts의 관계와 진실, 빠진 의미, 독자 효용과 자연스러움은 검증하지 않는다"
)
PATCH_MEANING = (
    "verified는 정확히 한 자리를 바꾸고 명시한 기존 위반을 줄이며 새 보호 원자 위반과 새 error를 "
    "만들지 않았다는 뜻뿐이다. 수정문의 의미와 진실, 자연스러움은 승인하지 않는다"
)
PATCH_MEANING_V2 = (
    "verified는 정확히 한 자리를 바꾸고 명시한 기존 위반을 줄이며 새 보호 원자 위반, 새 제목 구조 위반과 "
    "새 error를 만들지 않았다는 뜻뿐이다. 수정문의 의미와 진실, 자연스러움은 승인하지 않는다"
)


@dataclass(frozen=True)
class CheckResult:
    """같은 Contract와 글에서 항상 같은 JSON을 내는 검사 영수증."""

    contractSha256: str
    draftSha256: str
    surface: SurfaceDiff
    findings: tuple[Finding, ...]
    contractVersion: int
    outline: OutlineDiff | None
    document: DocumentSummary | None

    def __post_init__(self) -> None:
        if self.contractVersion not in (1, 2):
            raise ValueError(f"check result contractVersion 은 1 또는 2다: {self.contractVersion}")
        hasStructure = self.outline is not None and self.document is not None
        if hasStructure != (self.contractVersion == 2):
            raise ValueError("version 2 check result만 outline과 document를 함께 가진다")

    @property
    def errorCount(self) -> int:
        return sum(finding.severity == "error" for finding in self.findings)

    @property
    def noticeCount(self) -> int:
        return len(self.findings) - self.errorCount

    @property
    def violationCount(self) -> int:
        outlineCount = self.outline.violationCount if self.outline is not None else 0
        return self.surface.violationCount + outlineCount + self.errorCount

    def asDict(self) -> dict:
        errorRules = Counter(finding.rule for finding in self.findings if finding.severity == "error")
        result = {
            "version": self.contractVersion,
            "kind": "hanlint.checkResult",
            "violationCount": self.violationCount,
            "contractSha256": self.contractSha256,
            "draftSha256": self.draftSha256,
            "surface": self.surface.asDict(),
            "lint": {
                "errorCount": self.errorCount,
                "noticeCount": self.noticeCount,
                "errorRules": dict(sorted(errorRules.items())),
                "items": [finding.asDict() for finding in self.findings],
            },
            "meaning": CHECK_MEANING if self.contractVersion == 1 else CHECK_MEANING_V2,
        }
        if self.contractVersion == 2:
            result["outline"] = self.outline.asDict()
            result["document"] = self.document.asDict()
        return result


@dataclass(frozen=True)
class PatchResult:
    """Patch가 한정된 기계 검증을 만족했는지 남기는 영수증."""

    contractSha256: str
    sourceSha256: str
    patchSha256: str
    resultSha256: str | None
    reason: str
    matchCount: int
    reasonBefore: int
    reasonAfter: int | None
    newContractIssues: tuple[tuple[str, str], ...]
    newErrors: tuple[Finding, ...]
    resultText: str | None
    contractVersion: int

    def __post_init__(self) -> None:
        if self.contractVersion not in (1, 2):
            raise ValueError(f"patch result contractVersion 은 1 또는 2다: {self.contractVersion}")

    @property
    def newSurfaceIssues(self) -> tuple[tuple[str, str], ...]:
        """version 1 공개 속성과 기존 호출자를 위한 보호 표면 위반."""
        return tuple(issue for issue in self.newContractIssues if issue[0] != "outline")

    @property
    def reasonReduced(self) -> bool:
        return self.reasonBefore > 0 and self.reasonAfter is not None and self.reasonAfter < self.reasonBefore

    @property
    def violationCount(self) -> int:
        return (self.matchCount != 1) + (not self.reasonReduced) + len(self.newContractIssues) + len(self.newErrors)

    @property
    def verified(self) -> bool:
        return self.violationCount == 0

    def asDict(self) -> dict:
        result = {
            "version": self.contractVersion,
            "kind": "hanlint.patchResult",
            "verified": self.verified,
            "violationCount": self.violationCount,
            "contractSha256": self.contractSha256,
            "sourceSha256": self.sourceSha256,
            "patchSha256": self.patchSha256,
            "resultSha256": self.resultSha256,
            "matchCount": self.matchCount,
            "reason": {
                "name": self.reason,
                "before": self.reasonBefore,
                "after": self.reasonAfter,
                "reduced": self.reasonReduced,
            },
            "newErrors": [finding.asDict() for finding in self.newErrors],
            "meaning": PATCH_MEANING if self.contractVersion == 1 else PATCH_MEANING_V2,
        }
        issueKey = "newSurfaceIssues" if self.contractVersion == 1 else "newContractIssues"
        result[issueKey] = [{"kind": kind, "value": value} for kind, value in self.newContractIssues]
        newErrors = result.pop("newErrors")
        meaning = result.pop("meaning")
        result["newErrors"] = newErrors
        result["meaning"] = meaning
        return result


def renderCheck(result: CheckResult) -> str:
    """사람이 결론, 근거, 다음 행동 순서로 읽는 검사 영수증."""
    status = "계약 위반 없음" if result.violationCount == 0 else f"계약 위반 {result.violationCount}건"
    lines = [status]
    labels = (
        ("빠진 숫자", result.surface.missingNumbers),
        ("계약 밖 숫자", result.surface.unexpectedNumbers),
        ("빠진 URL", result.surface.missingUrls),
        ("계약 밖 URL", result.surface.unexpectedUrls),
        ("빠진 코드", result.surface.missingCode),
        ("계약 밖 코드", result.surface.unexpectedCode),
        ("빠진 링크 목적지", result.surface.missingLinks),
        ("계약 밖 링크 목적지", result.surface.unexpectedLinks),
    )
    lines.extend(f"- {label}: {', '.join(items)}" for label, items in labels if items)
    if result.outline is not None:
        state = "일치" if result.outline.matches else f"어긋남 {result.outline.violationCount}곳"
        lines.append(f"- 구조: H{result.outline.level} {len(result.outline.actual)}개, {state}")
        for mismatch in result.outline.mismatches:
            expected = mismatch.expected if mismatch.expected is not None else "없음"
            actual = mismatch.actual if mismatch.actual is not None else "없음"
            lines.append(f"  {mismatch.position}. 기대 `{expected}`, 실제 `{actual}`")
    if result.document is not None:
        lines.append(
            f"- 글: 문장 {result.document.sentenceCount}, 문단 {result.document.paragraphCount}, "
            f"절 {result.document.sectionCount}"
        )
        for index, section in enumerate(result.document.sections, start=1):
            lines.append(
                f"  {index}. {section.heading} ({section.line}행, 문단 {section.paragraphCount}, 코드 {section.codeBlockCount})"
            )
    lines.append(f"- lint: error {result.errorCount}, notice {result.noticeCount}")
    if result.errorCount:
        rules = Counter(finding.rule for finding in result.findings if finding.severity == "error")
        lines.append("  " + ", ".join(f"{rule} {count}" for rule, count in sorted(rules.items())))
    if result.violationCount:
        lines.append("\n다음: 계약과 글 가운데 틀린 쪽을 바로잡고 같은 check를 다시 실행한다")
    elif result.noticeCount:
        lines.append("\n다음: notice를 읽고 고칠지 유지할지 판단한 뒤 사람과 LLM 평가로 넘어간다")
    else:
        lines.append("\n다음: 세어서 잡히는 계약 위반이 없다. 사람과 LLM 평가로 넘어간다")
    lines.extend(["", CHECK_MEANING if result.contractVersion == 1 else CHECK_MEANING_V2])
    return "\n".join(lines)


__all__ = [
    "CHECK_MEANING",
    "CHECK_MEANING_V2",
    "PATCH_MEANING",
    "PATCH_MEANING_V2",
    "CheckResult",
    "PatchResult",
    "renderCheck",
]
