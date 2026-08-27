"""지문 열에서 문체 지표를 뽑는다. 프로파일을 만들 때와 견줄 때 같은 함수를 쓴다.

지표는 전부 비율이나 평균이라 글의 길이에 매이지 않는다.
"""

from __future__ import annotations

from collections import Counter
from functools import cache
from statistics import mean, pstdev

from ..data import loadLines
from ..fingerprint import ParagraphPrint, SentencePrint

ENDINGS_TRACKED = ("니다", "다", "것이다", "요")


@cache
def emphasisWords() -> tuple[str, ...]:
    return loadLines("emphasisWords.txt")


def metricsOf(sentences: tuple[SentencePrint, ...], paragraphs: tuple[ParagraphPrint, ...]) -> dict[str, float]:
    """문장 지문과 문단 지문에서 지표 사전을 만든다. 문장이 없으면 빈 사전이다."""
    if not sentences:
        return {}
    lengths = [s.length for s in sentences]
    words = max(1, sum(lengths))
    average = mean(lengths)
    std = pstdev(lengths) if len(lengths) > 1 else 0.0
    endings = Counter(s.ending for s in sentences)
    metrics = {
        "sentenceLength": average,
        "burstiness": std / average if average else 0.0,
        "commaRatio": sum(1 for s in sentences if s.commas > 0) / len(sentences),
        "questionRate": sum(1 for s in sentences if s.mood == "의문") / len(sentences),
        "readerCallRate": sum(1 for s in sentences if s.readerCall or s.mood == "명령") / len(sentences),
        "connectorDensity": sum(1 for s in sentences if s.connectorStart) * 1000 / words,
        "deixisDensity": sum(len(s.deixis) for s in sentences) * 1000 / words,
        "hedgeDensity": sum(s.hedges for s in sentences) * 1000 / words,
        "emphasisDensity": sum(sum(s.text.count(w) for w in emphasisWords()) for s in sentences) * 1000 / words,
        "causalDensity": sum(s.causal for s in sentences) * 1000 / words,
    }
    for ending in ENDINGS_TRACKED:
        metrics[f"ending:{ending}"] = endings.get(ending, 0) / len(sentences)
    if paragraphs:
        counts = [p.sentenceCount for p in paragraphs]
        metrics["paragraphSentences"] = mean(counts)
        metrics["shortParagraphRatio"] = sum(1 for c in counts if c <= 2) / len(counts)
    return metrics
