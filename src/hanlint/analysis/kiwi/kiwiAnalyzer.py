"""Kiwi 형태소 분석기 위의 정밀 구현.

로딩에 몇 초가 들어 처음 쓸 때 한 번만 올린다. 태그열 실측은 PRD 부록 A 에 있다.
되어진다 = 되/VV 어/EC 지/VX, 보여진다 = 보이/VV 어/EC 지/VX, 만들어진다 = 만들/VV 어/EC 지/VX (단순 피동).
"""

from __future__ import annotations

from functools import cached_property

from ...data import loadLines
from ..analyzer import Sentence
from ..tags import (
    AUXILIARY_TAG,
    CONNECTIVE_TAG,
    FOREIGN_TAG,
    GENITIVE_TAG,
    NOUN_TAGS,
    PASSIVE_CONNECTIVES,
    PASSIVE_STEM_TAGS,
)

INSTALL_HINT = "kiwipiepy 가 없다. pip install hanlint[kiwi] 로 설치하거나 --analyzer surface 를 쓴다"


class KiwiAnalyzer:
    name = "kiwi"

    @cached_property
    def kiwi(self):
        try:
            from kiwipiepy import Kiwi
        except ImportError as error:
            raise RuntimeError(INSTALL_HINT) from error
        return Kiwi()

    @cached_property
    def passiveStems(self) -> frozenset[str]:
        return frozenset(loadLines("passiveStems.txt"))

    def sentences(self, text: str) -> list[Sentence]:
        if not text.strip():
            return []
        return [Sentence(s.text, s.start, s.end) for s in self.kiwi.split_into_sents(text)]

    def tokens(self, sentence: str):
        return self.kiwi.tokenize(sentence)

    def euiCount(self, sentence: str) -> int:
        return sum(1 for token in self.tokens(sentence) if token.tag == GENITIVE_TAG)

    def longestNounRun(self, sentence: str) -> int:
        """명사 태그 연속의 최대 길이. 외국어 (SL) 가 이어지면 영어 구절 하나라 한 덩어리로 센다."""
        longest = run = 0
        previousForeign = False
        for token in self.tokens(sentence):
            if token.tag not in NOUN_TAGS:
                run = 0
                previousForeign = False
                continue
            isForeign = token.tag == FOREIGN_TAG
            if not (isForeign and previousForeign):
                run += 1
            previousForeign = isForeign
            longest = max(longest, run)
        return longest

    def doublePassives(self, sentence: str) -> list[str]:
        tokens = self.tokens(sentence)
        found: list[str] = []
        for i in range(len(tokens) - 2):
            stem, ending, auxiliary = tokens[i], tokens[i + 1], tokens[i + 2]
            isPassive = (stem.tag in PASSIVE_STEM_TAGS and stem.form == "되") or (
                stem.tag == "VV" and stem.form in self.passiveStems
            )
            if not isPassive or ending.tag != CONNECTIVE_TAG or ending.form not in PASSIVE_CONNECTIVES:
                continue
            if auxiliary.tag == AUXILIARY_TAG and auxiliary.form == "지":
                # 지 는 뒤 어미와 한 음절로 줄어들 수 있다 (되어진다). 어간 표층에 지 를 붙여 surface 와 같은 꼴로 낸다.
                found.append(sentence[stem.start : auxiliary.start] + "지")
        return found
