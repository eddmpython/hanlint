"""절 지문. H2 하나가 여는 절의 모양."""

from __future__ import annotations

from dataclasses import dataclass

from .paragraphPrint import ParagraphPrint


@dataclass(frozen=True)
class SectionPrint:
    index: int
    title: str
    """도입 절은 빈 문자열."""
    level: int
    """H2 면 2, 도입이면 0."""
    startLine: int
    paragraphs: tuple[ParagraphPrint, ...]
    blockKinds: tuple[str, ...]
    """절 안 블록 종류를 순서대로."""
    topics: frozenset[str]

    @property
    def isIntro(self) -> bool:
        return self.level == 0

    @property
    def hasProse(self) -> bool:
        return bool(self.paragraphs)

    def count(self, kind: str) -> int:
        return sum(1 for k in self.blockKinds if k == kind)
