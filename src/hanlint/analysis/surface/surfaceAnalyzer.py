"""의존성 0 분석기. 인터페이스 넷을 표층 근사로 채운다."""

from __future__ import annotations

from ..analyzer import Sentence
from . import tokenize
from .splitSentences import splitSentences


class SurfaceAnalyzer:
    name = "surface"

    def sentences(self, text: str) -> list[Sentence]:
        return splitSentences(text)

    def euiCount(self, sentence: str) -> int:
        return tokenize.euiCount(sentence)

    def longestNounRun(self, sentence: str) -> int:
        return tokenize.longestNounRun(sentence)

    def doublePassives(self, sentence: str) -> list[str]:
        return tokenize.doublePassives(sentence)
