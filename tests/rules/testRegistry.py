"""등록부가 기술서 아닌 규칙과 이름이 어긋난 규칙을 거부하는지."""

from __future__ import annotations

import pytest

from hanlint.rules import ruleDoc, ruleNames, ruleSummary
from hanlint.rules.registry import REQUIRED_SECTIONS, rule


def testRejectsRuleWithoutSections():
    with pytest.raises(ValueError, match="기술서"):

        @rule("bogusRule")
        def bogusRule(doc, config):
            """설명은 있지만 절이 없다."""
            return []


def testRejectsNameMismatch():
    with pytest.raises(ValueError, match="다르다"):

        @rule("someName")
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


def testUnknownRuleIsAKeyError():
    with pytest.raises(KeyError):
        ruleDoc("noSuchRule")
