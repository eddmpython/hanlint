"""본보기 게이트. 규칙마다 본보기가 하나 있고 그 본보기가 실제로 맞는지 본다.

본보기는 글쓴이와 AI 가 그대로 본떠 고치는 것이라 틀리면 나쁜 글을 퍼뜨린다. 그래서 세 가지를 강제한다.
`before` 는 그 규칙에 실제로 잡혀야 하고, `after` 는 잡히지 않아야 하며, 규칙과 본보기는 짝이어야 한다.

fixture 와 다른 점은 방향이다. fixture 는 규칙이 맞는지 보고 여기는 안내가 맞는지 본다. 규칙을 좁혀
`before` 가 안 잡히게 되면 본보기가 낡은 것이므로 여기가 빨갛다.
"""

from __future__ import annotations

import pytest

from hanlint.config import Config
from hanlint.data import exemplarFor, exemplars
from hanlint.rules import ruleNames
from tests.conftest import ANALYZERS, findingsOf

ALWAYS_ON = Config(preset="blog")
"""본보기는 프리셋과 무관하게 그 규칙이 켜진 상태로 잰다."""


def configFor(name: str) -> Config:
    """본보기가 도는 데 설정이 필요한 규칙만 채운다. 나머지는 기본값이다."""
    config = Config(preset="blog")
    if name == "keywordMissing":
        config.keywordField = "primaryKeyword"
    if name == "fieldEcho":
        config.endingFields = ["readerTakeaway"]
    return config


def testEveryRuleHasAnExemplar():
    rules = set(ruleNames())
    given = set(exemplars())
    assert rules - given == set(), f"본보기가 없는 규칙: {sorted(rules - given)}"
    assert given - rules == set(), f"규칙이 없는 본보기: {sorted(given - rules)}"


@pytest.mark.parametrize("name", ruleNames())
@pytest.mark.parametrize("analyzer", ANALYZERS, ids=lambda a: a.name)
def testExemplarBeforeIsCaughtAndAfterIsNot(name: str, analyzer):
    exemplar = exemplarFor(name)
    assert exemplar is not None
    config = configFor(name)
    before = [f.rule for f in findingsOf(exemplar.before, config, analyzer)]
    assert name in before, f"[{analyzer.name}] {name} 의 before 가 안 잡힌다: {exemplar.before!r} -> {before}"
    after = [f.rule for f in findingsOf(exemplar.after, config, analyzer)]
    assert name not in after, f"[{analyzer.name}] {name} 의 after 가 잡힌다: {exemplar.after!r}"


def testMovedSaysWhatChanged():
    for name, exemplar in exemplars().items():
        assert exemplar.moved.strip(), f"{name} 의 moved 가 비었다"
        assert name not in exemplar.moved, f"{name} 의 moved 가 규칙 이름을 되풀이한다. 손이 한 일을 적는다"
        assert exemplar.before != exemplar.after, f"{name} 의 before 와 after 가 같다"
