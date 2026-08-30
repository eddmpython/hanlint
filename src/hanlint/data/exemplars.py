"""본보기. 규칙마다 고치기 전과 후의 짝.

지적은 무엇이 틀렸는지 말한다. 본보기는 무엇이 맞는지 보인다. 실측 (tests/_attempts/fixReach) 에서 실제
글의 지적 104건 가운데 기계가 고쳐 주는 것이 0건이었다. 100%가 이유만 받고 어떻게 쓰는지는 글쓴이
몫으로 남았다. 그 빈자리를 메우는 층이다.

정본은 `exemplars.toml` 이고 여기는 그것을 읽어 자리표시자를 푸는 함수뿐이다. 자리표시자 규약은
fixture 와 같다. `{em}` 은 긴 줄표, `{dot}` 은 마침표다. 결함을 보여야 하는 자리인데 결함을 파일에
글자 그대로 담으면 이 저장소의 쓰기 훅이 막기 때문이다. 이 파일도 같은 이유로 코드 포인트로 적는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from unicodedata import east_asian_width

from .load import loadToml

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
ARROW = " -> "
"""전과 후를 잇는 표지. 긴 줄표를 쓸 수 없으므로 화살표다."""
ONE_LINE_LIMIT = 96
"""한 줄 본보기의 표시 폭 상한. 글자 수가 아니라 폭이다.

한글은 칸을 둘 먹는다. 처음에 글자 46으로 두고 `한 줄에 들어가는 길이` 라고 적었는데 한글 46자는
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
    """비어 있으면 기본 본보기, 값이 있으면 그 프리셋에서 고르는 문맥 본보기."""

    @property
    def twoLines(self) -> tuple[str, str]:
        """전과 후를 제 줄씩. 한글은 칸을 둘 먹어 한 줄에 둘 다 담으면 답인 `후` 가 먼저 잘린다."""
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
    """터미널이 먹는 칸 수. 한중일 글자는 둘, 나머지는 하나다."""
    return sum(2 if east_asian_width(ch) in "WF" else 1 for ch in text)


def shorten(text: str, limit: int = ONE_LINE_LIMIT) -> str:
    """한 줄로 보일 때의 꼴. 줄바꿈은 공백으로 눕히고 폭이 넘치면 자른다."""
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
    """기본과 문맥 본보기를 모두 읽는다. 같은 규칙에서 프리셋 조건이 겹치면 거부한다."""
    found: list[Exemplar] = []
    defaults: set[str] = set()
    contexts: dict[str, set[str]] = {}
    for entry in loadToml("exemplars.toml"):
        name = entry["rule"]
        presets = tuple(entry.get("presets", ()))
        if not presets:
            if name in defaults:
                raise ValueError(f"기본 본보기가 겹친다: {name}")
            defaults.add(name)
        else:
            overlap = contexts.setdefault(name, set()) & set(presets)
            if overlap:
                raise ValueError(f"문맥 본보기의 프리셋이 겹친다: {name} {', '.join(sorted(overlap))}")
            contexts[name].update(presets)
        found.append(Exemplar(name, expand(entry["before"]), expand(entry["after"]), entry["moved"], presets))
    return tuple(found)


@cache
def exemplars() -> dict[str, Exemplar]:
    """규칙 이름 → 기본 본보기. 기존 호출자가 규칙마다 한 개를 훑을 때 쓴다."""
    return {exemplar.rule: exemplar for exemplar in allExemplars() if not exemplar.presets}


def exemplarFor(rule: str, preset: str | None = None) -> Exemplar | None:
    if preset:
        for exemplar in allExemplars():
            if exemplar.rule == rule and preset in exemplar.presets:
                return exemplar
    return exemplars().get(rule)
