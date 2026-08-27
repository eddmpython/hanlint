"""문형 게이트. 틀이 실제로 통과하는지, 그 틀이 대신하는 문장이 실제로 잡히는지 본다.

문형은 글쓴이와 기계가 그대로 채워 쓰는 것이라 틀린 틀은 나쁜 글을 퍼뜨린다. 게다가 이 층이 파는 것은
**통과가 보장된 틀** 이라 그 보장이 매번 확인돼야 한다. 규칙을 넓혀 example 이 잡히게 되면 여기가 빨갛고,
규칙을 좁혀 instead 가 안 잡히게 되면 그때도 빨갛다.
"""

from __future__ import annotations

import pytest

from hanlint.config import Config
from hanlint.data import patterns, patternsAvoiding
from hanlint.rules import ruleNames
from tests.conftest import ANALYZERS, findingsOf

BLOG = Config(preset="blog")
"""문형은 프리셋과 무관하게 규칙이 전부 켜진 상태로 잰다."""


def testPatternsExist():
    assert len(patterns()) >= 8, "문형이 너무 적다. 글쓰기의 표준 자리를 덮지 못한다"


def testAvoidedRulesExist():
    known = set(ruleNames())
    for pattern in patterns():
        assert pattern.avoids, f"{pattern.name} 이 어느 규칙을 피하는지 안 적었다"
        unknown = [rule for rule in pattern.avoids if rule not in known]
        assert not unknown, f"{pattern.name} 의 avoids 에 없는 규칙이 있다: {unknown}"


def testFormHasSlots():
    for pattern in patterns():
        assert "{" in pattern.form and "}" in pattern.form, f"{pattern.name} 의 form 에 빈칸이 없다. 틀이 아니라 문장이다"
        assert pattern.when.strip(), f"{pattern.name} 이 언제 쓰는지 안 적었다"
        assert pattern.source.strip(), f"{pattern.name} 이 어디서 왔는지 안 적었다"


@pytest.mark.parametrize("pattern", patterns(), ids=lambda p: p.name)
@pytest.mark.parametrize("analyzer", ANALYZERS, ids=lambda a: a.name)
def testExamplePassesAndInsteadIsCaught(pattern, analyzer):
    found = [f.rule for f in findingsOf(pattern.example, BLOG, analyzer) if f.severity == "error"]
    assert not found, f"[{analyzer.name}] {pattern.name} 의 example 이 잡힌다: {found}"
    caught = {f.rule for f in findingsOf(pattern.instead, BLOG, analyzer)}
    missing = [rule for rule in pattern.avoids if rule not in caught]
    assert not missing, f"[{analyzer.name}] {pattern.name} 의 instead 가 {missing} 에 안 잡힌다: {caught}"


def testLookupByRule():
    assert patternsAvoiding("nounPile"), "nounPile 을 피하는 문형이 없다"
    assert not patternsAvoiding("noSuchRule")
