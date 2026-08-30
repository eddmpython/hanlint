"""승인 고침에서 뜻을 추측하지 않고 재사용할 수 있는 표면 치환.

공백과 문장부호를 제외한 편집 거리가 한 글자 이내일 때만 서명이 된다. 숫자, URL, 라틴 식별자,
경로, 코드와 링크 목적지는 바꾸지 않는다. 지시어와 의미 재작성은 여기서 다루지 않고 원문 완전 일치
패치에 남긴다.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from unicodedata import normalize

KOREAN = re.compile(r"[가-힣]")
URL = re.compile(r"https?://[^\s)>]+")
NUMBER = re.compile(r"(?<![A-Za-z가-힣])[-+]?\d+(?:[.,:]\d+)*(?:%|[가-힣]+)?")
LATIN_ATOM = re.compile(r"(?<![A-Za-z0-9_])(?:[A-Za-z_][A-Za-z0-9_.:/<>-]*)(?![A-Za-z0-9_])")
PATH_ATOM = re.compile(r"(?<!\w)(?:[\w.-]+/)+[\w.-]+|(?<!\w)[\w-]+\.[A-Za-z0-9]{1,8}(?!\w)")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
LINK_DESTINATION = re.compile(r"\[[^\]]*]\(([^)]+)\)")
HTML_TAG = re.compile(r"<[^>\n]+>")
DEICTIC_FRAGMENT = re.compile(r"이것|그것|저것|이러한|그러한|해당|이는|그는|그녀|그들")
SURFACE_CHARACTER = re.compile(r"[가-힣A-Za-z0-9]")
BOUNDARY = frozenset(" \t\r\n,.;:!?()[]{}<>\"'“”‘’…·/\\|+=*")
MAX_FRAGMENT_CHARACTERS = 32
MAX_SURFACE_EDIT_DISTANCE = 1


def protectedAtoms(text: str) -> tuple[str, ...]:
    """치환 전후에 같은 다중집합으로 남아야 하는 사실 표면."""
    found = []
    for pattern, label in (
        (URL, "url"),
        (NUMBER, "number"),
        (LATIN_ATOM, "latin"),
        (PATH_ATOM, "path"),
        (INLINE_CODE, "code"),
        (LINK_DESTINATION, "link"),
    ):
        for match in pattern.finditer(text):
            value = match.group(1) if match.lastindex else match.group(0)
            found.append(f"{label}:{value}")
    return tuple(sorted(found))


def protectedSpans(text: str) -> tuple[tuple[int, int], ...]:
    """국소 치환이 들어가면 안 되는 마크다운과 HTML 자리."""
    spans = []
    for pattern in (INLINE_CODE, URL, HTML_TAG):
        spans.extend((match.start(), match.end()) for match in pattern.finditer(text))
    spans.extend((match.start(1), match.end(1)) for match in LINK_DESTINATION.finditer(text))
    return tuple(sorted(set(spans)))


def protectedTermAtoms(text: str, terms: Iterable[str]) -> tuple[str, ...]:
    """사용자가 고유명사나 제품명으로 잠근 표면의 다중집합."""
    found = []
    for term in terms:
        cursor = 0
        while term:
            at = text.find(term, cursor)
            if at < 0:
                break
            found.append(term)
            cursor = at + len(term)
    return tuple(sorted(found))


def startBoundary(text: str, at: int) -> int:
    while at > 0 and text[at - 1] not in BOUNDARY:
        at -= 1
    return at


def endBoundary(text: str, at: int) -> int:
    while at < len(text) and text[at] not in BOUNDARY:
        at += 1
    return at


def changedFragment(before: str, after: str) -> tuple[str, str]:
    """공통 앞뒤를 걷고 바뀐 자리의 단어 경계까지 넓힌다."""
    prefix = 0
    limit = min(len(before), len(after))
    while prefix < limit and before[prefix] == after[prefix]:
        prefix += 1
    suffix = 0
    remaining = min(len(before) - prefix, len(after) - prefix)
    while suffix < remaining and before[len(before) - suffix - 1] == after[len(after) - suffix - 1]:
        suffix += 1
    beforeEnd = endBoundary(before, len(before) - suffix)
    afterEnd = endBoundary(after, len(after) - suffix)
    start = startBoundary(before, prefix)
    return before[start:beforeEnd].strip(), after[start:afterEnd].strip()


def editDistance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for leftIndex, leftCharacter in enumerate(left, start=1):
        current = [leftIndex]
        for rightIndex, rightCharacter in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[rightIndex] + 1,
                    previous[rightIndex - 1] + (leftCharacter != rightCharacter),
                )
            )
        previous = current
    return previous[-1]


def surfaceSkeleton(text: str) -> str:
    return "".join(SURFACE_CHARACTER.findall(text))


@dataclass(frozen=True)
class SurfaceOperation:
    before: str
    after: str
    presets: tuple[str, ...]

    def asDict(self, preset: str, sourceText: str, result: str) -> dict:
        return {
            "kind": "surfaceSubstitution",
            "before": self.before,
            "after": self.after,
            "sourceText": sourceText,
            "result": result,
            "match": {
                "preset": preset,
                "unique": True,
                "wordBoundary": True,
                "protectedFacts": True,
            },
        }


@dataclass(frozen=True)
class AppliedOperation:
    operation: SurfaceOperation
    sourceText: str
    result: str

    def asDict(self, preset: str) -> dict:
        return self.operation.asDict(preset, self.sourceText, self.result)


def operationFromApproval(
    before: str,
    after: str,
    presets: Iterable[str] = (),
    protectedTerms: Iterable[str] = (),
) -> SurfaceOperation | None:
    """승인 전후 전체에서 기계가 보증할 수 있는 표면 치환 하나를 추출한다."""
    before = normalize("NFC", before)
    after = normalize("NFC", after)
    protectedTerms = tuple(protectedTerms)
    if protectedAtoms(before) != protectedAtoms(after) or protectedTermAtoms(before, protectedTerms) != protectedTermAtoms(
        after, protectedTerms
    ):
        return None
    beforeFragment, afterFragment = changedFragment(before, after)
    beforeSkeleton = surfaceSkeleton(beforeFragment)
    afterSkeleton = surfaceSkeleton(afterFragment)
    if (
        not beforeFragment
        or not afterFragment
        or beforeFragment == afterFragment
        or len(beforeFragment) > MAX_FRAGMENT_CHARACTERS
        or len(afterFragment) > MAX_FRAGMENT_CHARACTERS
        or len(beforeSkeleton) < 2
        or len(afterSkeleton) < 2
        or editDistance(beforeSkeleton, afterSkeleton) > MAX_SURFACE_EDIT_DISTANCE
        or DEICTIC_FRAGMENT.search(beforeFragment)
        or DEICTIC_FRAGMENT.search(afterFragment)
        or any(term in beforeFragment or term in afterFragment for term in protectedTerms)
        or protectedAtoms(beforeFragment)
        or protectedAtoms(afterFragment)
        or before.count(beforeFragment) != 1
    ):
        return None
    return SurfaceOperation(beforeFragment, afterFragment, tuple(presets))


def projectOperations(entries: object, presetNames: Iterable[str]) -> tuple[SurfaceOperation, ...]:
    """설정의 `[[operations]]`를 검증한다. 같은 프리셋과 전 조각의 결과가 갈리면 거부한다."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("operations 는 [[operations]] 배열이다")
    knownPresets = set(presetNames)
    selectors: set[tuple[str, str]] = set()
    found = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"operations {index}번째 항목은 표다")
        unknown = sorted(set(entry) - {"before", "after", "presets"})
        if unknown:
            raise ValueError(f"operations {index}번째 항목의 모르는 키: {', '.join(unknown)}")
        before = entry.get("before")
        after = entry.get("after")
        if not isinstance(before, str) or not before.strip() or before != before.strip():
            raise ValueError(f"operations {index}번째 항목의 before 는 양끝 공백 없는 문자열이다")
        if not isinstance(after, str) or not after.strip() or after != after.strip():
            raise ValueError(f"operations {index}번째 항목의 after 는 양끝 공백 없는 문자열이다")
        rawPresets = entry.get("presets")
        if not isinstance(rawPresets, list) or not rawPresets or not all(isinstance(item, str) for item in rawPresets):
            raise ValueError(f"operations {index}번째 항목의 presets 는 비지 않은 문자열 배열이다")
        presets = tuple(rawPresets)
        unknownPresets = sorted(set(presets) - knownPresets)
        if unknownPresets:
            raise ValueError(f"operations {index}번째 항목의 모르는 프리셋: {', '.join(unknownPresets)}")
        if len(set(presets)) != len(presets):
            raise ValueError(f"operation의 프리셋이 겹친다: {before}")
        operation = operationFromApproval(before, after, presets)
        if operation is None or operation.before != before or operation.after != after:
            raise ValueError(f"operations {index}번째 항목은 안전한 표면 치환이 아니다: {before} -> {after}")
        for preset in presets:
            selector = (preset, before)
            if selector in selectors:
                raise ValueError(f"operation 선택 조건이 겹친다: {preset} {before}")
            selectors.add(selector)
        found.append(operation)
    return tuple(found)


def wordCharacter(character: str) -> bool:
    return bool(character) and (character.isalnum() or character == "_")


def operationPositions(
    text: str,
    operation: SurfaceOperation,
    protectedTerms: Iterable[str] = (),
) -> list[int]:
    positions = []
    blocked = list(protectedSpans(text))
    for term in protectedTerms:
        cursor = 0
        while term:
            at = text.find(term, cursor)
            if at < 0:
                break
            blocked.append((at, at + len(term)))
            cursor = at + len(term)
    cursor = 0
    while True:
        at = text.find(operation.before, cursor)
        if at < 0:
            return positions
        end = at + len(operation.before)
        left = text[at - 1] if at > 0 else ""
        right = text[end] if end < len(text) else ""
        touchesWord = (
            wordCharacter(operation.before[0])
            and wordCharacter(left)
            or wordCharacter(operation.before[-1])
            and wordCharacter(right)
        )
        insideProtected = any(at < blockedEnd and end > blockedStart for blockedStart, blockedEnd in blocked)
        if not touchesWord and not insideProtected:
            positions.append(at)
        cursor = at + 1


def applyOperation(text: str, operation: SurfaceOperation, protectedTerms: Iterable[str] = ()) -> str | None:
    """단어 경계를 지킨 한 자리에서만 치환하고 보호 원자가 달라지면 기권한다."""
    protectedTerms = tuple(protectedTerms)
    positions = operationPositions(text, operation, protectedTerms)
    if len(positions) != 1:
        return None
    at = positions[0]
    end = at + len(operation.before)
    changed = text[:at] + operation.after + text[end:]
    factsPreserved = protectedAtoms(text) == protectedAtoms(changed)
    termsPreserved = protectedTermAtoms(text, protectedTerms) == protectedTermAtoms(changed, protectedTerms)
    return changed if factsPreserved and termsPreserved else None


def operationFor(
    sourceText: str,
    preset: str | None,
    operations: Iterable[SurfaceOperation],
    protectedTerms: Iterable[str] = (),
) -> AppliedOperation | None:
    """현재 프리셋과 원문에서 적용 결과가 하나일 때만 돌려준다."""
    if not preset:
        return None
    protectedTerms = tuple(protectedTerms)
    matches = []
    for operation in operations:
        if preset not in operation.presets:
            continue
        result = applyOperation(sourceText, operation, protectedTerms)
        if result is not None:
            matches.append(AppliedOperation(operation, sourceText, result))
    return matches[0] if len(matches) == 1 else None
