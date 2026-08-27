"""문형. 빈칸이 있는 문장 틀.

본보기가 고친 사례 하나라면 문형은 그 사례를 다시 쓸 수 있는 틀이다. 한국 글쓰기 책들이 공통으로 드는
조언은 대부분 금지 규칙으로 담기지 않는다 (실측은 tests/_attempts/koreanStyleBooks). `것을 이름으로
바꾸라` 는 다섯 편에서 75건이 걸리는데 표본이 전부 정당했다. 그 조언들은 판정이 아니라 교정자의 눈이다.
틀로는 담긴다.

정본은 `patterns.toml` 이고 여기는 그것을 읽는 함수뿐이다. 게이트 (`tests/gates/testPatterns.py`) 가
문형마다 `example` 이 error 0 으로 통과하고 `instead` 가 `avoids` 의 규칙에 잡히는지 매번 확인한다.
**통과가 보장된 틀** 이라는 것이 이 층의 값이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from .load import loadToml


@dataclass(frozen=True)
class Pattern:
    name: str
    form: str
    """빈칸이 있는 틀. 빈칸은 중괄호다."""
    when: str
    """이 틀을 꺼내는 자리."""
    example: str
    """그 틀로 실제로 쓴 문장. hanlint 를 통과한다."""
    instead: str
    """같은 자리에 흔히 쓰는 문장. avoids 의 규칙에 잡힌다."""
    avoids: tuple[str, ...]
    source: str

    def asDict(self) -> dict:
        return {
            "name": self.name,
            "form": self.form,
            "when": self.when,
            "example": self.example,
            "instead": self.instead,
            "avoids": list(self.avoids),
            "source": self.source,
        }


@cache
def patterns() -> tuple[Pattern, ...]:
    found = []
    seen = set()
    for entry in loadToml("patterns.toml"):
        name = entry["name"]
        if name in seen:
            raise ValueError(f"문형 이름이 겹친다: {name}")
        seen.add(name)
        found.append(
            Pattern(
                name=name,
                form=entry["form"],
                when=entry["when"],
                example=entry["example"],
                instead=entry["instead"],
                avoids=tuple(entry["avoids"]),
                source=entry["source"],
            )
        )
    return tuple(found)


def patternsAvoiding(rule: str) -> tuple[Pattern, ...]:
    """그 규칙을 피하는 문형들. 지적을 받은 자리에서 무엇으로 다시 쓸지 고를 때 쓴다."""
    return tuple(pattern for pattern in patterns() if rule in pattern.avoids)
