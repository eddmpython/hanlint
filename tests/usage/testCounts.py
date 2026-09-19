"""용례 빈도표. 종류 고르기, 조회, nounPile 이 관용 연쇄를 접는 것."""

from __future__ import annotations

import pytest

from hanlint import Config, lintText
from hanlint.analysis import nounRuns
from hanlint.config import USAGE_KINDS, USAGE_OF
from hanlint.usage import attested, chainDocuments, conventional, patternDocuments, usageKindOf, usageTable

ATTESTED = "정관상 배당절차 개선방안 이행 가부"
"""사업보고서 양식의 항목 이름. 말뭉치 거의 모든 문서에 나온다."""
PILE = "가상환경 생성 후 패키지 설치 확인"


def testPresetDecidesTheKindAndConfigOverrides():
    assert usageKindOf(Config(preset="report")) == "report"
    assert usageKindOf(Config(preset="blog")) is None
    assert usageKindOf(Config(preset="blog", usageKind="report")) == "report"
    assert usageKindOf(Config(preset="report", usageKind="")) is None
    with pytest.raises(ValueError):
        Config(usageKind="novel")


def testEveryDeclaredKindHasATable():
    assert set(USAGE_OF.values()) <= set(USAGE_KINDS)
    for kind in USAGE_KINDS:
        table = usageTable(kind)
        assert table["kind"] == kind and table["documents"] > 0 and table["chains"]


def testChainKeysMatchNounRuns():
    chain = nounRuns(ATTESTED + " 항목을 적었습니다.")[0][0]
    assert " ".join(chain) == ATTESTED
    assert chainDocuments(chain, "report") >= 3
    assert attested(chain, "report", 3)
    assert not attested(nounRuns(PILE)[0][0], "report", 2)


def nounPiles(text: str, **mapping) -> list[str]:
    return [finding.quote for finding in lintText(text, Config.fromMapping(mapping)) if finding.rule == "nounPile"]


def testReportFoldsAttestedChainsOnly():
    text = f"{ATTESTED} 항목을 적었습니다.\n\n{PILE} 절차를 따릅니다.\n"
    assert nounPiles(text, preset="report") == [f"{PILE} 절차를 따릅니다."]
    assert len(nounPiles(text, preset="blog")) == 2
    assert len(nounPiles(text, preset="report", usageKind="")) == 2
    assert len(nounPiles(text, preset="report", usageMin=10_000)) == 2


def testLongerRunAroundAnAttestedChainIsStillAPile():
    assert nounPiles(f"{ATTESTED} 검토 결과를 적었습니다.\n", preset="report") == [f"{ATTESTED} 검토 결과를 적었습니다."]


CONVENTIONAL = "당사는 시장 상황에 대한 분석을 통해 대응 방안을 마련하였고 상기 계획을 이사회에서 정했습니다."
"""`에 대한`, `을 통해` 는 사업보고서 문서의 100%, `상기` 는 97% 에 나온다. `에 있어서` 는 76% 라 짚는다."""
RARE = "그 계획은 이사회에 있어서 승인되었습니다."


def dictionaryRules(text: str, **mapping) -> list[str]:
    findings = lintText(text, Config.fromMapping(mapping))
    return [f"{f.rule}:{f.quote.split()[0]}" for f in findings if f.rule in ("translationese", "hardWord")]


def testReportSkipsConventionalDictionaryEntries():
    assert dictionaryRules(CONVENTIONAL + "\n", preset="report") == []
    assert len(dictionaryRules(CONVENTIONAL + "\n", preset="blog")) == 3
    assert dictionaryRules(RARE + "\n", preset="report") == ["translationese:그"]
    assert dictionaryRules(CONVENTIONAL + "\n", preset="report", usageKind="") != []
    assert dictionaryRules(CONVENTIONAL + "\n", preset="report", usageShare=1.01) != []
    assert conventional("translationese", "에 대한", "report", 0.9)
    assert not conventional("translationese", "에 있어서", "report", 0.9)
    assert conventional("translationese", "에 있어서", "report", 0.5)
    assert patternDocuments("translationese", "없는 항목", "report") == 0


def testConfigDictionaryEntriesAreNeverConventional():
    """설정으로 더한 항목은 내장 항목과 pattern 이 같아도 접히지 않는다. 프로젝트가 스스로 넣은 낱말은 짚고 싶은 것이다."""
    mapping = {"preset": "report", "dictionary": {"translationese": [{"pattern": "에 대한", "fix": "의"}]}}
    assert dictionaryRules("시장에 대한 분석입니다.\n", **mapping) == ["translationese:시장에"]
