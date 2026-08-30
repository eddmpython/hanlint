"""분석 층. 문장 분리와 어절 판정을 표층 (어절과 꼬리 사전) 으로 한다. 형태소 분석기는 없다.

지문이 필요로 하는 것은 넷이다. 문장 분리 (splitSentences), 관형격 조사 의 의 자리 (euiCount, euiAdjacent), 조사
없이 이어진 명사 어절의 최장 길이 (longestNounRun), 이중 피동의 표층형 (doublePassives). 그 아래의 `grammar` 는
조사와 활용처럼 어절 판정과 무관하게 참인 한국어 형태 사실이다.

2026-08-29 까지는 형태소 분석기 (Kiwi) 를 선택으로 갈아 끼울 수 있었다. 기준 말뭉치 390편에서 둘을 대 보니 문장
분리는 표층이 낫고, 의 셈과 명사 나열은 표층이 못 세던 자리를 메워 같아졌다. 그래서 하나만 남겼다.
"""

from __future__ import annotations

from .splitSentences import Sentence, splitSentences
from .tokenize import doublePassives, doublePassiveSpans, euiAdjacent, euiCount, longestNounRun

__all__ = [
    "Sentence",
    "doublePassives",
    "doublePassiveSpans",
    "euiAdjacent",
    "euiCount",
    "longestNounRun",
    "splitSentences",
]
