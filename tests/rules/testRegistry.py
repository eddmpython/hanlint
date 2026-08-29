"""등록부가 기술서 아닌 규칙과 이름이 어긋난 규칙을 거부하는지."""

from __future__ import annotations

import pytest

from hanlint.rules import MECHANISMS, ruleDoc, ruleMechanism, ruleMechanisms, ruleNames, ruleSummary
from hanlint.rules.registry import REQUIRED_SECTIONS, rule


def testRejectsRuleWithoutSections():
    with pytest.raises(ValueError, match="기술서"):

        @rule("bogusRule", mechanism="repeat")
        def bogusRule(doc, config):
            """설명은 있지만 절이 없다."""
            return []


def testRejectsNameMismatch():
    with pytest.raises(ValueError, match="다르다"):

        @rule("someName", mechanism="repeat")
        def otherName(doc, config):
            """첫 줄.

            왜: a
            어디서: b
            고치기: c
            안 잡는 것: d
            """
            return []


def testEveryRegisteredRuleIsATechnicalNote():
    for name in ruleNames():
        doc = ruleDoc(name)
        for section in REQUIRED_SECTIONS:
            assert section in doc, f"{name} 에 {section} 이 없다"
        assert ruleSummary(name).endswith("."), f"{name} 의 첫 줄은 마침표로 끝나는 한 문장이다"


def testMechanismsAreAClosedSet():
    """규칙은 쌓여도 기제는 늘지 않는다. 여기 적힌 넷을 바꾸는 것은 등록 인자가 아니라 운영자 결정이다."""
    assert list(MECHANISMS) == ["dictionary", "repeat", "threshold", "contrast"]
    tagged = ruleMechanisms()
    assert set(tagged) == set(ruleNames())
    assert set(tagged.values()) <= set(MECHANISMS)
    for mechanism in MECHANISMS:
        assert mechanism in tagged.values(), f"규칙이 하나도 없는 기제: {mechanism}"
    assert ruleMechanism("endingRepeat") == "repeat"


def testRejectsAMechanismOutsideTheSet():
    """음성 시험. 여섯째 기제는 규칙 하나 때문에 조용히 들어오지 못한다."""
    with pytest.raises(ValueError, match="닫힌 집합 밖"):

        @rule("sixthWay", mechanism="embedding")
        def sixthWay(doc, config):
            """첫 줄.

            왜: a
            어디서: b
            고치기: c
            안 잡는 것: d
            """
            return []


def testUnknownRuleIsAKeyError():
    with pytest.raises(KeyError):
        ruleDoc("noSuchRule")
