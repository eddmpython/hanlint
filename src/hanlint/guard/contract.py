"""Reader Contract 검사와 이유가 붙은 국소 Patch 검증."""

from __future__ import annotations

from collections import Counter
from copy import copy
from dataclasses import dataclass
from hashlib import sha256

from ..config import Config, Contract, Patch
from ..document import parseMarkdown
from ..fingerprint import buildFingerprint
from ..rules import Finding, runAll
from .surface import SurfaceDiff, factLines, surfaceDiff

CHECK_MEANING = (
    "violationCount는 선언한 보호 원자와 hanlint error의 수다. "
    "facts의 관계와 진실, 빠진 의미, 독자 효용과 자연스러움은 검증하지 않는다"
)
PATCH_MEANING = (
    "verified는 정확히 한 자리를 바꾸고 명시한 기존 위반을 줄이며 새 보호 원자 위반과 새 error를 "
    "만들지 않았다는 뜻뿐이다. 수정문의 의미와 진실, 자연스러움은 승인하지 않는다"
)


@dataclass(frozen=True)
class CheckResult:
    """같은 Contract와 글에서 항상 같은 JSON을 내는 검사 영수증."""

    contractSha256: str
    draftSha256: str
    surface: SurfaceDiff
    findings: tuple[Finding, ...]

    @property
    def errorCount(self) -> int:
        return sum(finding.severity == "error" for finding in self.findings)

    @property
    def noticeCount(self) -> int:
        return len(self.findings) - self.errorCount

    @property
    def violationCount(self) -> int:
        return self.surface.violationCount + self.errorCount

    def asDict(self) -> dict:
        errorRules = Counter(finding.rule for finding in self.findings if finding.severity == "error")
        return {
            "version": 1,
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
            "meaning": CHECK_MEANING,
        }


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
    newSurfaceIssues: tuple[tuple[str, str], ...]
    newErrors: tuple[Finding, ...]
    resultText: str | None

    @property
    def reasonReduced(self) -> bool:
        return self.reasonBefore > 0 and self.reasonAfter is not None and self.reasonAfter < self.reasonBefore

    @property
    def violationCount(self) -> int:
        return (self.matchCount != 1) + (not self.reasonReduced) + len(self.newSurfaceIssues) + len(self.newErrors)

    @property
    def verified(self) -> bool:
        return self.violationCount == 0

    def asDict(self) -> dict:
        return {
            "version": 1,
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
            "newSurfaceIssues": [{"kind": kind, "value": value} for kind, value in self.newSurfaceIssues],
            "newErrors": [finding.asDict() for finding in self.newErrors],
            "meaning": PATCH_MEANING,
        }


def contractFromText(text: str, reader: str, goal: str) -> Contract:
    """원문의 보호 표면을 모두 덮는 version 1 Contract 초안을 만든다."""
    contract = Contract(reader, goal, factLines(text))
    result = surfaceDiff(contract.text, text)
    missing = []
    for kind in ("missingNumbers", "missingUrls", "missingCode", "missingLinks"):
        missing.extend(f"{kind}={value}" for value in getattr(result, kind))
    if missing:
        raise ValueError("reader 또는 goal이 원문에 없는 보호 원자를 넣었다: " + ", ".join(missing))
    if result.violationCount:
        issues = [f"{kind}={value}" for kind, values in result.asDict().items() for value in values]
        raise RuntimeError("계약 초안이 원문의 보호 표면을 모두 담지 못했다: " + ", ".join(issues))
    return contract


def check(
    text: str,
    contract: Contract | dict,
    config: Config | None = None,
    path: str | None = None,
) -> CheckResult:
    """글을 바꾸지 않고 Reader Contract 보호 원자와 hanlint 지적을 계산한다."""
    if isinstance(contract, dict):
        contract = Contract.fromMapping(contract)
    if not isinstance(contract, Contract):
        raise ValueError("contract 는 Contract 또는 contract JSON 객체다")
    selectedConfig = copy(config) if config is not None else Config()
    findings = tuple(runAll(buildFingerprint(parseMarkdown(text, path=path), selectedConfig), selectedConfig))
    return CheckResult(
        contractSha256=contract.digest,
        draftSha256=sha256(text.encode()).hexdigest(),
        surface=surfaceDiff(contract.text, text),
        findings=findings,
    )


def surfaceIssues(result: CheckResult) -> set[tuple[str, str]]:
    return {(kind, value) for kind, values in result.surface.asDict().items() for value in values}


def reasonCount(result: CheckResult, reason: str) -> int:
    surface = result.surface.asDict()
    if reason in surface:
        return len(surface[reason])
    return sum(finding.rule == reason for finding in result.findings)


def errorSignature(finding: Finding) -> tuple[str, str]:
    return finding.rule, finding.quote


def addedErrors(before: CheckResult, after: CheckResult) -> tuple[Finding, ...]:
    remaining = Counter(errorSignature(finding) for finding in before.findings if finding.severity == "error")
    added = []
    for finding in after.findings:
        if finding.severity != "error":
            continue
        signature = errorSignature(finding)
        if remaining[signature]:
            remaining[signature] -= 1
        else:
            added.append(finding)
    return tuple(added)


def verifyPatch(
    text: str,
    patch: Patch | dict,
    contract: Contract | dict,
    config: Config | None = None,
    path: str | None = None,
) -> PatchResult:
    """원문은 바꾸지 않고 정확 Patch의 근거 감소와 새 위반 부재를 검증한다."""
    if isinstance(patch, dict):
        patch = Patch.fromMapping(patch)
    if not isinstance(patch, Patch):
        raise ValueError("patch 는 Patch 또는 patch JSON 객체다")
    if isinstance(contract, dict):
        contract = Contract.fromMapping(contract)
    if not isinstance(contract, Contract):
        raise ValueError("contract 는 Contract 또는 contract JSON 객체다")
    beforeResult = check(text, contract, config, path)
    matchCount = text.count(patch.before)
    reasonBefore = reasonCount(beforeResult, patch.reason)
    if matchCount != 1:
        return PatchResult(
            contractSha256=contract.digest,
            sourceSha256=beforeResult.draftSha256,
            patchSha256=patch.digest,
            resultSha256=None,
            reason=patch.reason,
            matchCount=matchCount,
            reasonBefore=reasonBefore,
            reasonAfter=None,
            newSurfaceIssues=(),
            newErrors=(),
            resultText=None,
        )
    resultText = text.replace(patch.before, patch.after, 1)
    afterResult = check(resultText, contract, config, path)
    newSurface = tuple(sorted(surfaceIssues(afterResult) - surfaceIssues(beforeResult)))
    return PatchResult(
        contractSha256=contract.digest,
        sourceSha256=beforeResult.draftSha256,
        patchSha256=patch.digest,
        resultSha256=afterResult.draftSha256,
        reason=patch.reason,
        matchCount=matchCount,
        reasonBefore=reasonBefore,
        reasonAfter=reasonCount(afterResult, patch.reason),
        newSurfaceIssues=newSurface,
        newErrors=addedErrors(beforeResult, afterResult),
        resultText=resultText,
    )


__all__ = [
    "CHECK_MEANING",
    "PATCH_MEANING",
    "CheckResult",
    "PatchResult",
    "check",
    "contractFromText",
    "verifyPatch",
]
