"""화제어 집합. 조사를 뗀 명사 어절의 근사.

임베딩 없이 문단 사이의 화제 중첩을 재기 위한 것이다 (TextTiling 의 어휘 중첩). 동사와 어미로 끝나는
어절, 불용어, 한 글자는 뺀다. 노이즈가 있어도 두 문단이 같은 동사를 공유하는 일은 드물어 중첩 비교에는
쓸 만하다.
"""

from __future__ import annotations

import re
from functools import cache

from ..analysis.surface.tokenize import stripJosa, tailOf, words
from ..data import loadLines

WORD = re.compile(r"^[가-힣A-Za-z][가-힣A-Za-z0-9]*$")


@cache
def stopwords() -> frozenset[str]:
    return frozenset(loadLines("stopwords.txt"))


def topicsOf(text: str) -> frozenset[str]:
    found: set[str] = set()
    for word in words(text):
        core = stripJosa(word.core)
        if not WORD.match(core) or core in stopwords():
            continue
        # 한 글자는 조사가 붙어 있던 것만 명사로 본다 (표를, 값이, 열은). 홀로 선 한 글자는 잡음이다.
        if len(core) < 2 and core == word.core:
            continue
        if tailOf(core, "verbTails.txt"):
            continue
        found.add(core.lower())
    return frozenset(found)


def overlap(a: frozenset[str], b: frozenset[str]) -> float:
    """자카드 유사도. 둘 다 비어 있으면 0."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
