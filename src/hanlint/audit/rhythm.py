"""문장 길이의 분포, 쉼표 비율, 종결어미 분포, 문단 길이 분포."""

from __future__ import annotations

from collections import Counter
from statistics import mean, pstdev

from ..fingerprint import ParagraphPrint, SentencePrint
from .shape import Rhythm

LENGTH_BUCKETS = ((1, 5, "1~5"), (6, 10, "6~10"), (11, 15, "11~15"), (16, 20, "16~20"), (21, 30, "21~30"), (31, 10**9, "31~"))
PARAGRAPH_BUCKETS = ((1, 1, "1"), (2, 2, "2"), (3, 4, "3~4"), (5, 6, "5~6"), (7, 10**9, "7~"))


def bucketize(values: list[int], buckets) -> tuple[tuple[str, int], ...]:
    counts = []
    for low, high, label in buckets:
        counts.append((label, sum(1 for v in values if low <= v <= high)))
    return tuple(counts)


def rhythmOf(sentences: tuple[SentencePrint, ...]) -> Rhythm:
    lengths = [s.length for s in sentences]
    if not lengths:
        return Rhythm(0.0, 0.0, 0.0, bucketize([], LENGTH_BUCKETS))
    average = mean(lengths)
    std = pstdev(lengths) if len(lengths) > 1 else 0.0
    return Rhythm(average, std, std / average if average else 0.0, bucketize(lengths, LENGTH_BUCKETS))


def commaRatioOf(sentences: tuple[SentencePrint, ...]) -> float:
    if not sentences:
        return 0.0
    return sum(1 for s in sentences if s.commas > 0) / len(sentences)


def endingMixOf(sentences: tuple[SentencePrint, ...]) -> tuple[tuple[str, float], ...]:
    if not sentences:
        return ()
    counts = Counter(s.ending for s in sentences)
    total = len(sentences)
    return tuple((ending, count / total) for ending, count in counts.most_common())


def paragraphHistogramOf(paragraphs: tuple[ParagraphPrint, ...]) -> tuple[tuple[str, int], ...]:
    return bucketize([p.sentenceCount for p in paragraphs], PARAGRAPH_BUCKETS)
