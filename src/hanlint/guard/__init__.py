"""구조화 brief와 결과 글 사이의 결정적 표면 계약."""

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
from .contract import CHECK_MEANING, PATCH_MEANING, CheckResult, PatchResult, check, contractFromText, verifyPatch
from .surface import surfaceDiff

GUARD_MEANING = (
    "contractSatisfied는 명시한 표면과 자동 error가 맞는다는 뜻뿐이다. "
    "원자 사실의 관계와 진실, 빠진 의미, 금지 주장의 바꿔 말하기, 독자 효용과 자연스러움은 보장하지 않는다"
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
    """글을 바꾸지 않고 구조화 brief의 결정적 표면과 hanlint error를 대조한다."""
    if isinstance(brief, dict):
        brief = WritingBrief.fromMapping(brief)
    if not isinstance(brief, WritingBrief):
        raise ValueError("brief 는 WritingBrief 또는 brief JSON 객체다")
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
        # NFC 로 세지 않으면 한글 한 글자가 자모 두세 개로 세어져 길이 계약이 뒤집힌다. 나머지 표면 검사는
        # 전부 surfaceText 를 쓰는데 여기만 원문을 쓰고 있었다 (2026-08-31).
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
    status = "표면 계약 충족" if result.contractSatisfied else f"표면 계약 위반 {result.violationCount}건"
    lines = [status]
    labels = (
        ("빠진 필수 표면", result.missingRequired),
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
        lines.append(f"- 글자 수: {result.characterCount}자. 허용 범위 {result.minCharacters}~{result.maxCharacters}자")
    if result.errorCount:
        rules = Counter(finding.rule for finding in result.findings if finding.severity == "error")
        lines.append("- hanlint error: " + ", ".join(f"{rule} {count}" for rule, count in sorted(rules.items())))
    if result.noticeCount:
        lines.append(f"- 확인할 notice: {result.noticeCount}건")
    lines.extend(["", GUARD_MEANING])
    return "\n".join(lines)


__all__ = [
    "CHECK_MEANING",
    "GUARD_MEANING",
    "PATCH_MEANING",
    "CheckResult",
    "GuardResult",
    "PatchResult",
    "check",
    "contractFromText",
    "guardFile",
    "guardText",
    "renderGuard",
    "verifyPatch",
]
