"""조사 맞추기. 낱말을 바꾸면 뒤에 붙은 조사의 꼴이 따라 바뀐다.

**왜 이 시험이 있나.** 한국어 린터가 `이슈로` 를 `쟁점로` 로 고치라고 내밀고 있었다. 그것만이 아니라
`hanlint fix` 가 `잔고가` 를 `잔액가` 로, `기스를` 을 `흠집를` 로, `해변가로` 를 `해변로` 로 **파일에
써 넣고 있었다.** 잡으라고 만든 결함을 자기가 만든 것이라 이 시험은 짝으로 둔다.
"""

from __future__ import annotations

import pytest

from hanlint.analysis.grammar.josa import digitFinal, finalOf, fitJosa, josaSwap

CHANGED = [
    ("쟁점", "로 알려 준다", "으로 알려 준다"),
    # 숫자는 한자어로 읽어 센다. 10 은 십이라 ㅂ 받침이고 2026 은 이천이십육이라 ㄱ 받침이다
    ("10", "로 간다", "으로 간다"),
    ("3", "로 간다", "으로 간다"),
    ("2026", "로 간다", "으로 간다"),
    ("100", "가 크다", "이 크다"),
    ("잔액", "가 부족하다", "이 부족하다"),
    ("흠집", "를 본다", "을 본다"),
    ("해변", "가 넓다", "이 넓다"),
    ("막일", "가 힘들다", "이 힘들다"),
    ("구역", "를 나눈다", "을 나눈다"),
    ("쟁점", "와 답", "과 답"),
    ("쟁점", "라고 한다", "이라고 한다"),
    ("이슈", "이라고 한다", "라고 한다"),
    ("이슈", "으로 알려 준다", "로 알려 준다"),
]
"""(바꾼 낱말, 뒤에 오던 글, 나와야 할 글). 두 방향 다 본다."""

KEPT = [
    ("이슈", "로 알려 준다"),
    ("노하우", "를 씁니다"),
    ("인프라", "가 필요하다"),
    ("서울", "로 간다"),
    ("실행", "으로 간다"),
    ("쟁점", "이 있다"),
    # 조사가 아니라 더 긴 낱말의 앞머리다
    ("쟁점", "이유가 있다"),
    ("해변", "가로 갑니다"),
    ("쟁점", "로그를 본다"),
    # 로마자는 발음에 따라 갈린다 (SQL 은 에스큐엘로도 시퀄로도 읽는다). 세어서 확정되지 않아 안 만든 자리다
    ("API", "를 쓴다"),
    ("HTTP", "가 있다"),
    # 숫자는 읽는 법이 정해져 있다. 이천이십사라 받침이 없다
    ("2024", "로 바뀐다"),
    ("2", "로 바뀐다"),
    ("7", "로 간다"),
    # 뒤에 조사가 없다
    ("쟁점", ""),
    ("쟁점", " 하나를 고른다"),
]
"""바꾸면 안 되는 자리. 고쳐야 할 자리를 놓치는 쪽이 멀쩡한 문장을 망가뜨리는 쪽보다 낫다."""


@pytest.mark.parametrize(("word", "following", "wanted"), CHANGED)
def testJosaFollowsTheNewWord(word: str, following: str, wanted: str):
    assert fitJosa(word, following) == wanted
    assert josaSwap(word, following) is not None


@pytest.mark.parametrize(("word", "following"), KEPT)
def testJosaLeavesWhatItShould(word: str, following: str):
    assert fitJosa(word, following) == following
    assert josaSwap(word, following) is None


def testRieulIsTheExceptionForRo():
    """`으로` 만 ㄹ 받침을 없는 것처럼 다룬다. `서울로` 는 맞고 `서울으로` 는 틀리다."""
    assert fitJosa("서울", "으로 간다") == "로 간다"
    assert fitJosa("서울", "이 크다") == "이 크다"


def testFinalOfReadsTheLastSyllable():
    assert finalOf("쟁점") != 0
    assert finalOf("이슈") == 0
    assert finalOf("API") is None
    assert finalOf("") is None


# (숫자, 어떻게 읽나, 받침이 있나). 끝자리만 보면 20 을 이십이 아니라 영으로 읽어 틀린다.
NUMBERS = [
    ("0", "영", True),
    ("1", "일", True),
    ("2", "이", False),
    ("3", "삼", True),
    ("6", "육", True),
    ("9", "구", False),
    ("10", "십", True),
    ("20", "이십", True),
    ("16", "십육", True),
    ("100", "백", True),
    ("1000", "천", True),
    ("10000", "만", True),
    ("100000", "십만", True),
    ("100000000", "억", True),
    ("2024", "이천이십사", False),
    ("2026", "이천이십육", True),
]


@pytest.mark.parametrize(("number", "reading", "hasFinal"), NUMBERS)
def testNumbersAreReadTheKoreanWay(number: str, reading: str, hasFinal: bool):
    """`으로` 를 고르려면 숫자를 읽어야 한다. 끝자리만 보면 20 이 십으로 안 끝나는 줄 안다."""
    assert bool(digitFinal(number)) is hasFinal, reading
    assert finalOf(number) == finalOf(reading), reading
    assert fitJosa(number, "로 간다") == fitJosa(reading, "로 간다"), reading


def testLatinIsNotDecidedByCounting():
    """로마자는 발음에 달렸고 발음은 세어서 확정되지 않는다. 안 만든 자리이지 미룬 자리가 아니다."""
    assert finalOf("SQL") is None
    assert fitJosa("SQL", "를 쓴다") == "를 쓴다"
    assert fitJosa("SQL", "을 쓴다") == "을 쓴다"
