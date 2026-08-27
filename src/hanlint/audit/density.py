"""천 어절당 밀도. 연결어, 지시어, 강조 낱말, 헤지, 수치."""

from __future__ import annotations

from functools import cache

from ..data import loadLines
from ..fingerprint import SentencePrint
from .shape import Density


@cache
def emphasisWords() -> tuple[str, ...]:
    return loadLines("emphasisWords.txt")


def countEmphasis(text: str) -> int:
    return sum(text.count(word) for word in emphasisWords())


def densityOf(sentences: tuple[SentencePrint, ...], wordCount: int) -> Density:
    if not wordCount:
        return Density(0.0, 0.0, 0.0, 0.0, 0.0)
    scale = 1000 / wordCount
    return Density(
        connectors=sum(1 for s in sentences if s.connectorStart) * scale,
        deixis=sum(len(s.deixis) for s in sentences) * scale,
        emphasis=sum(countEmphasis(s.text) for s in sentences) * scale,
        hedges=sum(s.hedges for s in sentences) * scale,
        numbers=sum(s.numbers for s in sentences) * scale,
    )
