"""용례 빈도표. 종류 고르기, 조회, nounPile 이 관용 연쇄를 접는 것."""

from __future__ import annotations

import pytest

from hanlint import Config, lintText
from hanlint.analysis import nounRuns
from hanlint.config import USAGE_KINDS, USAGE_OF
from hanlint.usage import attested, chainDocuments, usageKindOf, usageTable

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
