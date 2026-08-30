"""글쓴이가 승인한 국소 고침과 결정적 선택 조건.

내장 본보기는 규칙을 설명하지만 실제 수정 성능을 높인다는 보장이 없었다. 패치는 프로젝트에서 사람이
승인한 전후 짝만 들고, 정규화한 원문, 규칙, 프리셋, 국소 표지, 독자 상태가 모두 맞을 때 하나만
돌려준다. 점수와 유사도는 쓰지 않는다. 맞는 것이 없거나 둘 이상이면 기권한다.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from unicodedata import normalize

from .exemplars import exemplars, expand

READER_KINDS = ("recent", "known", "new", "none")
"""지적 문장 직전 독자와 그 문장 화제의 관계."""


def flatCue(text: str) -> str:
    """줄과 연속 공백 차이는 선택 조건으로 쓰지 않는다."""
    return " ".join(text.split())


def flatSentence(text: str) -> str:
    """승인 원문은 유니코드 조합과 줄, 연속 공백만 눕혀 비교한다."""
    return " ".join(normalize("NFC", text).split())


@dataclass(frozen=True)
class Patch:
    rule: str
    before: str
    after: str
    moved: str
    cue: str
    reader: str
    presets: tuple[str, ...]
    sentence: str = ""
    """마크다운 표식을 걷은 선택용 원문. 비면 before를 쓴다."""
    sourceText: str = ""
    """마크다운 표식을 보존한 선택용 원문. 비면 before를 쓴다."""

    @property
    def matchSentence(self) -> str:
        return flatSentence(self.sentence or self.before)

    @property
    def matchSourceText(self) -> str:
        return flatSentence(self.sourceText or self.before)

    def asDict(self, preset: str) -> dict:
        return {
            "before": self.before,
            "after": self.after,
            "moved": self.moved,
            "match": {
                "sourceText": self.matchSourceText,
                "sentence": self.matchSentence,
                "preset": preset,
                "cue": self.cue,
                "reader": self.reader,
            },
        }


def projectPatches(entries: object, presetNames: Iterable[str]) -> tuple[Patch, ...]:
    """설정의 `[[patches]]`를 검증한다. 선택 조건이 겹치는 승인 고침은 거부한다."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("patches 는 [[patches]] 배열이다")
    allowedKeys = {"rule", "before", "after", "moved", "sourceText", "sentence", "cue", "reader", "presets"}
    knownRules = set(exemplars())
    knownPresets = set(presetNames)
    selectors: set[tuple[str, str, str, str, str, str]] = set()
    found: list[Patch] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"patches {index}번째 항목은 표다")
        unknown = sorted(set(entry) - allowedKeys)
        if unknown:
            raise ValueError(f"patches {index}번째 항목의 모르는 키: {', '.join(unknown)}")
        values: dict[str, str] = {}
        for key in ("rule", "before", "after", "moved", "cue", "reader"):
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"patches {index}번째 항목의 {key} 는 비지 않은 문자열이다")
            values[key] = value
        rule = values["rule"]
        if rule not in knownRules:
            raise ValueError(f"patches {index}번째 항목의 모르는 규칙: {rule}")
        reader = values["reader"]
        if reader not in READER_KINDS:
            raise ValueError(f"patches {index}번째 항목의 reader 는 {', '.join(READER_KINDS)} 가운데 하나다: {reader}")
        rawPresets = entry.get("presets")
        if not isinstance(rawPresets, list) or not rawPresets or not all(isinstance(item, str) for item in rawPresets):
            raise ValueError(f"patches {index}번째 항목의 presets 는 비지 않은 문자열 배열이다")
        presets = tuple(rawPresets)
        unknownPresets = sorted(set(presets) - knownPresets)
        if unknownPresets:
            raise ValueError(f"patches {index}번째 항목의 모르는 프리셋: {', '.join(unknownPresets)}")
        if len(set(presets)) != len(presets):
            raise ValueError(f"패치의 프리셋이 겹친다: {rule}")
        cue = flatCue(values["cue"])
        before = expand(values["before"])
        after = expand(values["after"])
        rawSentence = entry.get("sentence", before)
        if not isinstance(rawSentence, str) or not rawSentence.strip():
            raise ValueError(f"patches {index}번째 항목의 sentence 는 비지 않은 문자열이다")
        sentence = flatSentence(rawSentence)
        rawSourceText = entry.get("sourceText", before)
        if not isinstance(rawSourceText, str) or not rawSourceText.strip():
            raise ValueError(f"patches {index}번째 항목의 sourceText 는 비지 않은 문자열이다")
        sourceText = flatSentence(rawSourceText)
        for preset in presets:
            selector = (rule, preset, sourceText, sentence, cue, reader)
            if selector in selectors:
                raise ValueError(f"패치 선택 조건이 겹친다: {rule} {preset} {cue} {reader}")
            selectors.add(selector)
        found.append(
            Patch(
                rule=rule,
                before=before,
                after=after,
                moved=values["moved"],
                cue=cue,
                reader=reader,
                presets=presets,
                sentence=sentence,
                sourceText=sourceText,
            )
        )
    return tuple(found)


def patchFor(
    rule: str,
    preset: str | None,
    sourceText: str,
    sentence: str,
    cue: str,
    reader: str | None,
    patches: Iterable[Patch],
) -> Patch | None:
    """원문을 포함한 모든 조건이 맞는 패치가 하나일 때만 돌려준다."""
    if not preset or reader not in READER_KINDS:
        return None
    wantedCue = flatCue(cue)
    wantedSourceText = flatSentence(sourceText)
    wantedSentence = flatSentence(sentence)
    matches = [
        patch
        for patch in patches
        if patch.rule == rule
        and preset in patch.presets
        and patch.matchSourceText == wantedSourceText
        and patch.matchSentence == wantedSentence
        and patch.cue == wantedCue
        and patch.reader == reader
    ]
    return matches[0] if len(matches) == 1 else None
