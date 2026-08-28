"""지적의 fragment 를 원문에서 찾아 replacement 로 바꾼다.

지적의 인용문은 마크다운 표식을 걷은 문장이라 원문과 글자가 다를 수 있다. 그래서 문장 전체가 아니라 바꿀 조각
(fragment) 을 지적이 있는 문단 (지적 줄부터 다음 빈 줄까지) 에서 찾는다. 그 안에 조각이 정확히 한 번 있을 때만
바꾸고, 없거나 여럿이면 이유를 남기고 건너뛴다. 바꾸는 순서는 뒤에서부터라 앞의 오프셋이 흔들리지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..analysis.josa import josaSwap
from ..rules import Finding


@dataclass(frozen=True)
class FixResult:
    text: str
    applied: tuple[tuple[int, str, str], ...]
    """(줄, 조각, 바꾼 것). 원문 순서."""
    skipped: tuple[tuple[int, str, str], ...]
    """(줄, 조각, 이유)."""


def lineOffsets(text: str) -> list[int]:
    offsets = [0]
    for index, char in enumerate(text):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def windowOf(text: str, offsets: list[int], line: int) -> tuple[int, int]:
    """1 부터 세는 줄 번호의 지적이 조각을 찾을 [시작, 끝). 그 줄부터 다음 빈 줄 직전까지다."""
    startIndex = max(0, min(line - 1, len(offsets) - 1))
    start = offsets[startIndex]
    end = len(text)
    for index in range(startIndex + 1, len(offsets)):
        lineStart = offsets[index]
        lineEnd = offsets[index + 1] - 1 if index + 1 < len(offsets) else len(text)
        if not text[lineStart:lineEnd].strip():
            end = lineStart
            break
    return start, end


def occurrences(haystack: str, needle: str) -> list[int]:
    found = []
    at = haystack.find(needle)
    while at >= 0:
        found.append(at)
        at = haystack.find(needle, at + 1)
    return found


def applyFixes(text: str, findings: list[Finding]) -> FixResult:
    offsets = lineOffsets(text)
    edits: list[tuple[int, int, str, str]] = []
    lineAt: dict[int, int] = {}
    skipped: list[tuple[int, str, str]] = []
    seen: set[tuple[int, str, str]] = set()
    for finding in findings:
        if finding.replacement is None or not finding.fragment:
            continue
        start, end = windowOf(text, offsets, finding.line)
        found = occurrences(text[start:end], finding.fragment)
        if not found:
            skipped.append(
                (finding.line, finding.fragment, "원문에서 조각을 못 찾았다. 마크다운 표식 안에 있을 수 있다. 손으로 고친다")
            )
            continue
        if len(found) > 1:
            skipped.append((finding.line, finding.fragment, "같은 조각이 여러 번이라 자리를 정하지 못했다. 손으로 고친다"))
            continue
        at = start + found[0]
        fragment, replacement = finding.fragment, finding.replacement
        # 낱말을 바꾸면 뒤에 붙은 조사의 꼴이 따라 바뀐다. 실측: `잔고가` 를 `잔액가` 로,
        # `기스를` 을 `흠집를` 로, `해변가로` 를 `해변로` 로 파일에 써 넣고 있었다.
        swap = josaSwap(replacement, text[at + len(fragment) :])
        if swap is not None:
            fragment, replacement = fragment + swap[0], replacement + swap[1]
        key = (at, fragment, replacement)
        if key in seen:
            continue
        seen.add(key)
        lineAt[at] = finding.line
        edits.append((at, at + len(fragment), replacement, fragment))

    edits.sort(key=lambda e: e[0], reverse=True)
    applied: list[tuple[int, int, str, str]] = []
    result = text
    lastStart: int | None = None
    for start, end, replacement, fragment in edits:
        if lastStart is not None and end > lastStart:
            skipped.append((lineAt[start], fragment, "다른 고침과 자리가 겹친다. 다시 돌리면 고쳐진다"))
            continue
        result = result[:start] + replacement + result[end:]
        applied.append((start, lineAt[start], fragment, replacement))
        lastStart = start
    applied.sort()
    skipped.sort(key=lambda s: s[0])
    return FixResult(result, tuple((line, fragment, replacement) for _, line, fragment, replacement in applied), tuple(skipped))
