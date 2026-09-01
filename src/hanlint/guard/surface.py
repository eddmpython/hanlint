"""계약 본문과 결과 글 사이의 보호 원자 차이."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from unicodedata import normalize

from ..config import numberValues
from ..data.operations import INLINE_CODE, LINK_DESTINATION, URL


def valuesOf(pattern, text: str) -> tuple[str, ...]:
    """정규식이 잡은 전체 값이나 첫 캡처 그룹의 정렬된 집합."""
    values = set()
    for match in pattern.finditer(text):
        values.add(match.group(1) if match.lastindex else match.group(0))
    return tuple(sorted(values))


@dataclass(frozen=True)
class SurfaceDiff:
    """숫자, URL, 인라인 코드, 링크 목적지의 양방향 집합 차이."""

    missingNumbers: tuple[str, ...]
    unexpectedNumbers: tuple[str, ...]
    missingUrls: tuple[str, ...]
    unexpectedUrls: tuple[str, ...]
    missingCode: tuple[str, ...]
    unexpectedCode: tuple[str, ...]
    missingLinks: tuple[str, ...]
    unexpectedLinks: tuple[str, ...]

    @property
    def violationCount(self) -> int:
        return sum(len(items) for items in self.values())

    def values(self) -> tuple[tuple[str, ...], ...]:
        return (
            self.missingNumbers,
            self.unexpectedNumbers,
            self.missingUrls,
            self.unexpectedUrls,
            self.missingCode,
            self.unexpectedCode,
            self.missingLinks,
            self.unexpectedLinks,
        )

    def asDict(self) -> dict:
        return {
            "missingNumbers": list(self.missingNumbers),
            "unexpectedNumbers": list(self.unexpectedNumbers),
            "missingUrls": list(self.missingUrls),
            "unexpectedUrls": list(self.unexpectedUrls),
            "missingCode": list(self.missingCode),
            "unexpectedCode": list(self.unexpectedCode),
            "missingLinks": list(self.missingLinks),
            "unexpectedLinks": list(self.unexpectedLinks),
        }


def surfaceDiff(contractText: str, text: str, numbers: Iterable[str] | None = None) -> SurfaceDiff:
    """계약에 선언된 보호 원자를 결과 글의 원자와 대조한다."""
    surfaceText = normalize("NFC", text)
    expectedNumbers = set(numberValues(contractText) if numbers is None else numbers)
    actualNumbers = set(numberValues(surfaceText))
    expectedUrls = set(valuesOf(URL, contractText))
    actualUrls = set(valuesOf(URL, surfaceText))
    expectedCode = set(valuesOf(INLINE_CODE, contractText))
    actualCode = set(valuesOf(INLINE_CODE, surfaceText))
    expectedLinks = set(valuesOf(LINK_DESTINATION, contractText))
    actualLinks = set(valuesOf(LINK_DESTINATION, surfaceText))
    allowedCode = expectedCode | {value for value in actualCode if value in contractText}
    allowedLinks = expectedLinks | {value for value in actualLinks if value in contractText}
    return SurfaceDiff(
        missingNumbers=tuple(sorted(expectedNumbers - actualNumbers)),
        unexpectedNumbers=tuple(sorted(actualNumbers - expectedNumbers)),
        missingUrls=tuple(sorted(expectedUrls - actualUrls)),
        unexpectedUrls=tuple(sorted(actualUrls - expectedUrls)),
        missingCode=tuple(sorted(expectedCode - actualCode)),
        unexpectedCode=tuple(sorted(actualCode - allowedCode)),
        missingLinks=tuple(sorted(expectedLinks - actualLinks)),
        unexpectedLinks=tuple(sorted(actualLinks - allowedLinks)),
    )


__all__ = ["SurfaceDiff", "surfaceDiff", "valuesOf"]
