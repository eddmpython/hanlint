"""분석 부분. 문장 분리와 어절 판정을 글자 모양(어절과 꼬리 사전)만으로 한다. 형태소 분석기는 없다.

글 분석에 필요한 것은 넷이다. 문장 분리(splitSentences), 관형격 조사 `의`의 위치(euiCount, euiAdjacent), 조사
없이 이어진 명사 어절의 최장 길이(longestNounRun), 이중 피동의 글자 모양(doublePassives). 그 아래의 `grammar`는
조사와 활용처럼 어절 판정과 무관하게 참인 한국어 형태 사실이다.

2026-08-29까지는 형태소 분석기(Kiwi)를 선택으로 갈아 끼울 수 있었다. 기준 말뭉치 390편에서 둘을 비교해 보니 문장
분리는 글자 모양만 보는 방식이 낫고, `의` 세기와 명사 나열은 그 방식이 못 세던 경우를 보충해 같아졌다. 그래서 하나만 남겼다.
"""

from __future__ import annotations

from .splitSentences import Sentence, splitSentences
from .tokenize import doublePassives, doublePassiveSpans, euiAdjacent, euiCount, longestNounRun, nounRuns

__all__ = [
    "Sentence",
    "doublePassives",
    "doublePassiveSpans",
    "euiAdjacent",
    "euiCount",
    "longestNounRun",
    "nounRuns",
    "splitSentences",
]
