"""분석 결과의 모양. 숫자와 자리만 있다. 점수도 등급도 없다."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Rhythm:
    mean: float
    """문장 길이 (어절) 평균."""
    std: float
    burstiness: float
    """표준편차 / 평균. AI 글이 낮다는 신호가 있지만 점수가 아니다."""
    histogram: tuple[tuple[str, int], ...]
    """(구간 이름, 문장 수)."""


@dataclass(frozen=True)
class Density:
    """천 어절당 개수."""

    connectors: float
    deixis: float
    emphasis: float
    hedges: float
    numbers: float


@dataclass(frozen=True)
class Valley:
    paragraphIndex: int
    line: int
    previousLine: int
    overlap: float


@dataclass(frozen=True)
class SectionShape:
    index: int
    title: str
    level: int
    startLine: int
    paragraphs: int
    sentences: int
    codeBlocks: int
    images: int
    tables: int
    lists: int
    hasProse: bool


@dataclass(frozen=True)
class AuditResult:
    path: str | None
    sentenceCount: int
    paragraphCount: int
    sectionCount: int
    wordCount: int
    rhythm: Rhythm
    commaRatio: float
    """쉼표가 있는 문장의 비율."""
    endingMix: tuple[tuple[str, float], ...]
    """(종결어미 부류, 비율). 많은 순."""
    paragraphHistogram: tuple[tuple[str, int], ...]
    shortParagraphRatio: float
    """두 문장 이하 문단의 비율."""
    density: Density
    overlaps: tuple[tuple[int, float], ...]
    """(문단 index, 앞 문단과의 화제 중첩). 절의 첫 문단은 없다."""
    valleys: tuple[Valley, ...]
    sections: tuple[SectionShape, ...]
    headingLevels: tuple[int, ...]
    questionCount: int
    readerCallCount: int

    def asDict(self) -> dict:
        return asdict(self)
