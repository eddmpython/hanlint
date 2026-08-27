"""문단 지문. 문장 지문의 합과 앞 문단과의 관계."""

from __future__ import annotations

from dataclasses import dataclass

from .sentencePrint import SentencePrint


@dataclass(frozen=True)
class ParagraphPrint:
    index: int
    """글 안 산문 문단 순서."""
    blockIndex: int
    sectionIndex: int
    startLine: int
    endLine: int
    sentences: tuple[SentencePrint, ...]
    meanLength: float
    lengthStd: float
    causalTotal: int
    deixisTotal: int
    topics: frozenset[str]
    overlapWithPrevious: float | None
    """같은 절 안 바로 앞 산문 문단과의 화제 중첩 (자카드). 절의 첫 문단이면 None."""
    followsProseDirectly: bool
    """바로 앞 블록도 산문인가. 코드나 표가 끼면 False. 조각남을 셀 때 연속의 기준이다."""

    @property
    def sentenceCount(self) -> int:
        return len(self.sentences)

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.sentences)
