"""조사 맞추기. 낱말을 바꾸면 뒤에 붙은 조사의 꼴이 따라 바뀐다.

**왜 이 시험이 있나.** 한국어 린터가 `이슈로` 를 `쟁점로` 로 고치라고 내밀고 있었다. 그것만이 아니라
`hanlint fix` 가 `잔고가` 를 `잔액가` 로, `기스를` 을 `흠집를` 로, `해변가로` 를 `해변로` 로 **파일에
써 넣고 있었다.** 잡으라고 만든 결함을 자기가 만든 것이라 이 시험은 짝으로 둔다.
"""

from __future__ import annotations

import pytest

from hanlint.analysis.josa import finalOf, fitJosa, josaSwap

CHANGED = [
    ("쟁점", "로 알려 준다", "으로 알려 준다"),
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
    # 한글로 안 끝나면 읽는 법이 갈려 손대지 않는다
    ("API", "를 쓴다"),
    ("HTTP", "가 있다"),
    ("2024", "로 바뀐다"),
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
