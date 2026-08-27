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

from .load import loadToml

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
ARROW = " -> "
"""전과 후를 잇는 표지. 긴 줄표를 쓸 수 없으므로 화살표다."""
ONE_LINE_LIMIT = 46
"""한 줄 본보기의 한쪽 글자 상한. 터미널 폭에서 전과 후가 한 줄에 들어가는 길이다."""


@dataclass(frozen=True)
class Exemplar:
    rule: str
    before: str
    """그 규칙에 실제로 잡히는 글."""
    after: str
    """같은 뜻이면서 잡히지 않는 글."""
    moved: str
    """무엇이 달라졌는지 한 마디."""

    @property
    def oneLine(self) -> str:
        """한 줄로 줄인 짝. 여러 줄짜리 본보기는 눕혀서 앞부분만 보인다."""
        return shorten(self.before) + ARROW + shorten(self.after)

    def asDict(self) -> dict:
        return {"before": self.before, "after": self.after, "moved": self.moved}


def expand(text: str) -> str:
    return text.replace("{em}", EM_DASH).replace("{en}", EN_DASH).replace("{dot}", ".")


def shorten(text: str, limit: int = ONE_LINE_LIMIT) -> str:
    """한 줄로 보일 때의 꼴. 줄바꿈은 공백으로 눕히고 길면 자른다."""
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + chr(0x2026)


@cache
def exemplars() -> dict[str, Exemplar]:
    """규칙 이름 → 본보기. 규칙 하나에 본보기 하나다."""
    found: dict[str, Exemplar] = {}
    for entry in loadToml("exemplars.toml"):
        name = entry["rule"]
        if name in found:
            raise ValueError(f"본보기가 겹친다: {name}. 규칙 하나에 하나다")
        found[name] = Exemplar(name, expand(entry["before"]), expand(entry["after"]), entry["moved"])
    return found


def exemplarFor(rule: str) -> Exemplar | None:
    return exemplars().get(rule)
