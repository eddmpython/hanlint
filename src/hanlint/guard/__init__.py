"""구조화 brief와 결과 글 사이의 글자 대조. 같은 입력이면 늘 같은 결과다."""

from __future__ import annotations

from collections import Counter
from copy import copy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from unicodedata import normalize

from ..config import Config, WritingBrief
from ..document import parseMarkdown
from ..fingerprint import buildFingerprint
from ..rules import Finding, runAll
from .contract import check, contractFromText, contractFromTextV2, verifyPatch
from .receipt import (
    CHECK_MEANING,
    CHECK_MEANING_V2,
    PATCH_MEANING,
    PATCH_MEANING_V2,
    CheckResult,
    PatchResult,
    renderCheck,
)
from .surface import surfaceDiff

GUARD_MEANING = (
    "contractSatisfied는 brief에 적은 문구·숫자·링크·코드·글자 수가 맞고 hanlint 오류가 없다는 뜻뿐이다. "
    "사실 사이의 관계와 사실 여부, 빠진 뜻, 금지 주장을 바꿔 말한 글, 독자에게 쓸모 있는지와 자연스러운지는 보장하지 않는다"
)


@dataclass(frozen=True)
class GuardResult:
    briefSha256: str
    draftSha256: str
    missingRequired: tuple[str, ...]
    missingNumbers: tuple[str, ...]
    unexpectedNumbers: tuple[str, ...]
    missingUrls: tuple[str, ...]
    unexpectedUrls: tuple[str, ...]
    missingCode: tuple[str, ...]
    unexpectedCode: tuple[str, ...]
    missingLinks: tuple[str, ...]
    unexpectedLinks: tuple[str, ...]
    forbiddenHits: tuple[str, ...]
    characterCount: int
    minCharacters: int
    maxCharacters: int
    findings: tuple[Finding, ...]

    @property
    def lengthSatisfied(self) -> bool:
        return self.minCharacters <= self.characterCount <= self.maxCharacters

    @property
    def errorCount(self) -> int:
        return sum(finding.severity == "error" for finding in self.findings)

    @property
    def noticeCount(self) -> int:
        return len(self.findings) - self.errorCount

    @property
    def violationCount(self) -> int:
        surface = sum(
            len(items)
            for items in (
                self.missingRequired,
                self.missingNumbers,
                self.unexpectedNumbers,
                self.missingUrls,
                self.unexpectedUrls,
                self.missingCode,
                self.unexpectedCode,
                self.missingLinks,
                self.unexpectedLinks,
                self.forbiddenHits,
            )
        )
        return surface + (not self.lengthSatisfied) + self.errorCount

    @property
    def contractSatisfied(self) -> bool:
        return self.violationCount == 0

    def asDict(self) -> dict:
        errorRules = Counter(finding.rule for finding in self.findings if finding.severity == "error")
        return {
            "version": 1,
            "kind": "hanlint.guardResult",
            "contractSatisfied": self.contractSatisfied,
            "violationCount": self.violationCount,
            "briefSha256": self.briefSha256,
            "draftSha256": self.draftSha256,
            "surface": {
                "missingRequired": list(self.missingRequired),
                "missingNumbers": list(self.missingNumbers),
                "unexpectedNumbers": list(self.unexpectedNumbers),
                "missingUrls": list(self.missingUrls),
                "unexpectedUrls": list(self.unexpectedUrls),
                "missingCode": list(self.missingCode),
                "unexpectedCode": list(self.unexpectedCode),
                "missingLinks": list(self.missingLinks),
                "unexpectedLinks": list(self.unexpectedLinks),
                "forbiddenHits": list(self.forbiddenHits),
            },
            "length": {
                "satisfied": self.lengthSatisfied,
                "actual": self.characterCount,
                "min": self.minCharacters,
                "max": self.maxCharacters,
            },
            "lint": {
                "errorCount": self.errorCount,
                "noticeCount": self.noticeCount,
                "errorRules": dict(sorted(errorRules.items())),
                "items": [finding.asDict() for finding in self.findings],
            },
            "meaning": GUARD_MEANING,
        }


def guardText(
    brief: WritingBrief | dict,
    text: str,
    config: Config | None = None,
    path: str | None = None,
) -> GuardResult:
    """글을 바꾸지 않고 구조화 brief에 적은 문구·숫자·링크·코드와 hanlint 오류를 대조한다."""
    if isinstance(brief, dict):
        brief = WritingBrief.fromMapping(brief)
    if not isinstance(brief, WritingBrief):
        raise ValueError("brief는 WritingBrief나 brief JSON 객체여야 한다")
    selectedConfig = copy(config) if config is not None else Config()
    selectedConfig.preset = brief.preset
    findings = tuple(runAll(buildFingerprint(parseMarkdown(text, path=path), selectedConfig), selectedConfig))
    surfaceText = normalize("NFC", text)
    atomDiff = surfaceDiff(brief.text, text, brief.allowedNumbers)
    return GuardResult(
        briefSha256=brief.digest,
        draftSha256=sha256(text.encode()).hexdigest(),
        missingRequired=tuple(literal for literal in brief.mustInclude if literal not in surfaceText),
        missingNumbers=atomDiff.missingNumbers,
        unexpectedNumbers=atomDiff.unexpectedNumbers,
        missingUrls=atomDiff.missingUrls,
        unexpectedUrls=atomDiff.unexpectedUrls,
        missingCode=atomDiff.missingCode,
        unexpectedCode=atomDiff.unexpectedCode,
        missingLinks=atomDiff.missingLinks,
        unexpectedLinks=atomDiff.unexpectedLinks,
        forbiddenHits=tuple(literal for literal in brief.forbidden if literal in surfaceText),
        # NFC로 세지 않으면 한글 한 글자가 자모 두세 개로 세어져 길이 계약이 뒤집힌다. 나머지 글자 검사는
        # 모두 surfaceText를 쓰는데 여기만 원문을 쓰고 있었다(2026-08-31).
        characterCount=len(surfaceText),
        minCharacters=brief.minCharacters,
        maxCharacters=brief.maxCharacters,
        findings=findings,
    )


def guardFile(
    brief: WritingBrief | dict,
    path: str | Path,
    config: Config | None = None,
) -> GuardResult:
    path = Path(path)
    return guardText(brief, path.read_text(encoding="utf-8"), config, str(path))


def renderGuard(result: GuardResult) -> str:
    status = "brief 조건 충족" if result.contractSatisfied else f"brief 조건 위반 {result.violationCount}건"
    lines = [status]
    labels = (
        ("빠진 필수 문구", result.missingRequired),
        ("빠진 숫자", result.missingNumbers),
        ("요구 밖 숫자", result.unexpectedNumbers),
        ("빠진 URL", result.missingUrls),
        ("요구 밖 URL", result.unexpectedUrls),
        ("빠진 코드", result.missingCode),
        ("요구 밖 코드", result.unexpectedCode),
        ("빠진 링크 목적지", result.missingLinks),
        ("요구 밖 링크 목적지", result.unexpectedLinks),
        ("금지 주장", result.forbiddenHits),
    )
    lines.extend(f"- {label}: {', '.join(items)}" for label, items in labels if items)
    if not result.lengthSatisfied:
        lines.append(f"- 글자 수: {result.characterCount:,}자. 허용 범위 {result.minCharacters:,}~{result.maxCharacters:,}자")
    if result.errorCount:
        rules = Counter(finding.rule for finding in result.findings if finding.severity == "error")
        lines.append("- hanlint 오류: " + ", ".join(f"{rule} {count}" for rule, count in sorted(rules.items())))
    if result.noticeCount:
        lines.append(f"- 확인 권고: {result.noticeCount}건")
    lines.extend(["", GUARD_MEANING])
    return "\n".join(lines)


__all__ = [
    "CHECK_MEANING",
    "CHECK_MEANING_V2",
    "GUARD_MEANING",
    "PATCH_MEANING",
    "PATCH_MEANING_V2",
    "CheckResult",
    "GuardResult",
    "PatchResult",
    "check",
    "contractFromText",
    "contractFromTextV2",
    "guardFile",
    "guardText",
    "renderGuard",
    "renderCheck",
    "verifyPatch",
]
