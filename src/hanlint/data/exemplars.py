"""예시. 규칙마다 고치기 전과 고친 뒤의 짝.

지적은 무엇이 틀렸는지 말한다. 예시는 무엇이 맞는지 보인다. 실제 글의 지적 104건을 재어 보니 기계가
고쳐 주는 것이 0건이었다(tests/_attempts/fixReach). 모두 까닭만 받고 어떻게 쓰는지는 글쓴이 몫으로
남았다. 예시는 그 일을 돕는 부분이다.

내용은 `exemplars.toml`에 있고 여기는 그것을 읽어 자리표시자를 푸는 함수뿐이다. 자리표시자 규칙은
fixture와 같다. `{em}`은 긴 줄표, `{dot}`은 마침표다. 잘못된 글을 보여야 하는 예시인데 그 글자를 파일에
그대로 담으면 이 저장소의 쓰기 훅이 막기 때문이다. 이 파일도 같은 이유로 코드 포인트로 적는다.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from unicodedata import east_asian_width

from .load import loadToml

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
ARROW = " -> "
"""전과 후를 잇는 기호. 긴 줄표를 쓸 수 없으므로 화살표다."""
ONE_LINE_LIMIT = 96
"""한 줄 예시의 표시 폭 상한. 글자 수가 아니라 폭이다.

한글은 한 글자가 두 칸이다. 처음에 글자 46으로 두고 `한 줄에 들어가는 길이`라고 적었는데 한글 46자는
92칸이고 전과 후를 한 줄에 이으면 176칸이라 어느 터미널에도 안 들어갔다. 단위가 틀렸던 것이다.
그래서 전과 후를 각자 제 줄에 두고 한 줄은 96칸으로 잰다."""


@dataclass(frozen=True)
class Exemplar:
    rule: str
    before: str
    """그 규칙에 실제로 잡히는 글."""
    after: str
    """같은 뜻이면서 잡히지 않는 글."""
    moved: str
    """무엇이 달라졌는지 한 마디."""
    presets: tuple[str, ...] = ()
    """비어 있으면 기본 예시, 값이 있으면 그 프리셋에서 고르는 문맥 예시."""

    @property
    def twoLines(self) -> tuple[str, str]:
        """전과 후를 한 줄씩. 한글은 한 글자가 두 칸이라 한 줄에 둘 다 담으면 답인 `후`가 먼저 잘린다."""
        return shorten(self.before), shorten(self.after)

    @property
    def shortened(self) -> bool:
        """어느 한쪽이라도 잘렸나. 잘렸으면 전문이 어디 있는지 알려야 한다."""
        return isShortened(self.before) or isShortened(self.after)

    def asDict(self) -> dict:
        return {"before": self.before, "after": self.after, "moved": self.moved}


def expand(text: str) -> str:
    return text.replace("{em}", EM_DASH).replace("{en}", EN_DASH).replace("{dot}", ".")


def displayWidth(text: str) -> int:
    """터미널에서 차지하는 칸 수. 한중일 글자는 둘, 나머지는 하나다."""
    return sum(2 if east_asian_width(ch) in "WF" else 1 for ch in text)


def shorten(text: str, limit: int = ONE_LINE_LIMIT) -> str:
    """한 줄로 보일 때의 모양. 줄바꿈은 공백으로 바꾸고 폭이 넘치면 자른다."""
    flat = " ".join(text.split())
    if displayWidth(flat) <= limit:
        return flat
    kept: list[str] = []
    used = 0
    for ch in flat:
        step = 2 if east_asian_width(ch) in "WF" else 1
        if used + step > limit - 1:
            break
        kept.append(ch)
        used += step
    return "".join(kept) + chr(0x2026)


def isShortened(text: str) -> bool:
    return displayWidth(" ".join(text.split())) > ONE_LINE_LIMIT


@cache
def allExemplars() -> tuple[Exemplar, ...]:
    """기본 예시와 문맥 예시를 모두 읽는다. 같은 규칙에서 프리셋 조건이 겹치면 거부한다."""
    found: list[Exemplar] = []
    defaults: set[str] = set()
    contexts: dict[str, set[str]] = {}
    for entry in loadToml("exemplars.toml"):
        name = entry["rule"]
        presets = tuple(entry.get("presets", ()))
        if not presets:
            if name in defaults:
                raise ValueError(f"기본 예시가 겹친다: {name}")
            defaults.add(name)
        else:
            overlap = contexts.setdefault(name, set()) & set(presets)
            if overlap:
                raise ValueError(f"문맥 예시의 프리셋이 겹친다: {name} {', '.join(sorted(overlap))}")
            contexts[name].update(presets)
        found.append(Exemplar(name, expand(entry["before"]), expand(entry["after"]), entry["moved"], presets))
    return tuple(found)


@cache
def exemplars() -> dict[str, Exemplar]:
    """규칙 이름 → 기본 예시. 기존 호출자가 규칙마다 한 개를 훑을 때 쓴다."""
    return {exemplar.rule: exemplar for exemplar in allExemplars() if not exemplar.presets}


def projectExemplars(entries: object, presetNames: Iterable[str]) -> tuple[Exemplar, ...]:
    """설정의 `[[exemplars]]`를 검증해 예시로 바꾼다.

    프로젝트 안에서는 같은 규칙과 선택 조건이 하나뿐이어야 한다. 내장 예시와 겹치는 것은 덮어쓰기로
    정해 두었으므로 허용한다.
    """
    if not isinstance(entries, (list, tuple)):
        raise ValueError("exemplars는 [[exemplars]] 배열이어야 한다")
    allowedKeys = {"rule", "before", "after", "moved", "presets"}
    knownRules = set(exemplars())
    knownPresets = set(presetNames)
    defaults: set[str] = set()
    contexts: dict[str, set[str]] = {}
    found: list[Exemplar] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"exemplars {index}번째 항목은 표여야 한다")
        unknown = sorted(set(entry) - allowedKeys)
        if unknown:
            raise ValueError(f"exemplars {index}번째 항목의 모르는 키: {', '.join(unknown)}")
        values: dict[str, str] = {}
        for key in ("rule", "before", "after", "moved"):
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"exemplars {index}번째 항목의 {key} 값은 비지 않은 문자열이어야 한다")
            values[key] = value
        rule = values["rule"]
        if rule not in knownRules:
            raise ValueError(f"exemplars {index}번째 항목의 모르는 규칙: {rule}")
        rawPresets = entry.get("presets", [])
        if not isinstance(rawPresets, list) or not all(isinstance(item, str) for item in rawPresets):
            raise ValueError(f"exemplars {index}번째 항목의 presets는 문자열 배열이어야 한다")
        presets = tuple(rawPresets)
        unknownPresets = sorted(set(presets) - knownPresets)
        if unknownPresets:
            raise ValueError(f"exemplars {index}번째 항목의 모르는 프리셋: {', '.join(unknownPresets)}")
        if len(set(presets)) != len(presets):
            raise ValueError(f"프로젝트 예시의 프리셋이 겹친다: {rule}")
        if not presets:
            if rule in defaults:
                raise ValueError(f"프로젝트 기본 예시가 겹친다: {rule}")
            defaults.add(rule)
        else:
            overlap = contexts.setdefault(rule, set()) & set(presets)
            if overlap:
                raise ValueError(f"프로젝트 예시의 프리셋이 겹친다: {rule} {', '.join(sorted(overlap))}")
            contexts[rule].update(presets)
        found.append(Exemplar(rule, expand(values["before"]), expand(values["after"]), values["moved"], presets))
    return tuple(found)


def exemplarFor(rule: str, preset: str | None = None, customExemplars: Iterable[Exemplar] = ()) -> Exemplar | None:
    custom = tuple(customExemplars)
    if preset:
        for exemplar in custom:
            if exemplar.rule == rule and preset in exemplar.presets:
                return exemplar
        for exemplar in allExemplars():
            if exemplar.rule == rule and preset in exemplar.presets:
                return exemplar
    for exemplar in custom:
        if exemplar.rule == rule and not exemplar.presets:
            return exemplar
    return exemplars().get(rule)
