"""어휘 분포. 어절 수, 낱말 종류 수, 종류 대 어절 비, 영문 어절 비율, 자주 쓴 말, 문두 접속사. 점수는 없다.

고유어와 한자어의 구분은 사전이 없어 하지 않는다. 영문 어절 비율이 외래어와 식별자의 근사다.
"""

from __future__ import annotations

from collections import Counter

from ..analysis.tokenize import stripJosa, words
from ..fingerprint import SentencePrint
from .shape import Lexicon

TOP_WORDS = 8


def lexiconOf(sentences: tuple[SentencePrint, ...]) -> Lexicon:
    cores: list[str] = []
    foreign = 0
    for sentence in sentences:
        for word in words(sentence.text):
            if not word.core:
                continue
            cores.append(stripJosa(word.core).lower())
            if word.core.isascii():
                foreign += 1
    counts = Counter(topic for sentence in sentences for topic in sentence.topics)
    tokens = len(cores)
    return Lexicon(
        tokens=tokens,
        types=len(set(cores)),
        typeTokenRatio=(len(set(cores)) / tokens) if tokens else 0.0,
        foreignRatio=(foreign / tokens) if tokens else 0.0,
        topWords=tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:TOP_WORDS]),
    )


def connectorMixOf(sentences: tuple[SentencePrint, ...]) -> tuple[tuple[str, int], ...]:
    """문두 접속부사별 횟수. 많은 순."""
    counts = Counter(s.connectorStart for s in sentences if s.connectorStart)
    return tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
