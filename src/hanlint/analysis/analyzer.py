"""분석기 인터페이스. 지문 생성이 필요로 하는 넷만 드러낸다.

- `sentences(text)` 문장 분리. 각 문장의 원문 안 오프셋을 준다
- `euiCount(sentence)` 관형격 조사 `의` 의 수
- `longestNounRun(sentence)` 조사 없이 이어진 명사의 최장 개수
- `doublePassives(sentence)` 이중 피동으로 잡힌 표층형 목록

이보다 낮은 수준 (형태소 태그) 은 드러내지 않는다. 그래야 surface 와 kiwi 가 같은 규칙을 돌린다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Sentence:
    text: str
    start: int
    """분석에 넣은 문자열 안의 시작 오프셋."""
    end: int


class Analyzer(Protocol):
    name: str

    def sentences(self, text: str) -> list[Sentence]: ...

    def euiCount(self, sentence: str) -> int: ...

    def longestNounRun(self, sentence: str) -> int: ...

    def doublePassives(self, sentence: str) -> list[str]: ...
