"""고침 후보 계약. 말뭉치가 뒷받침하는 꼴만 내고, 고치다 새 결함을 만드는 꼴은 버린다."""

from __future__ import annotations

from pathlib import Path

import pytest

from hanlint import Config, usageCandidates
from hanlint.edit.usageCandidates import candidatesFor, keeps, sentenceTally
from hanlint.usage import Joints, buildIndex, loadIndex, readDocuments

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "fixtures" / "usage" / "joints"

PILE = "당사는 품질 관리 담당 조직 개편 계획을 세웠습니다."
CHAIN = "회사는 제1항의 규정에 따라 이사회의 결의로 주주 외의 자에게 신주를 배정합니다."
TRAP = "회사의 조직 개편 담당 인력 배치 계획은 대표의 승인을 받습니다."
"""고치면 규칙은 풀리지만 `의` 가 셋이 되는 문장. 말뭉치가 그 자리에 쓰는 조사가 `의` 뿐이다."""


def config() -> Config:
    return Config(preset="report", enforceStyle=["nounPile"])


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    root = tmp_path_factory.mktemp("candidates")
    buildIndex("report", readDocuments(CORPUS), root)
    return loadIndex("report", root)


def testNounPileGetsTheParticleTheCorpusUsesThere(index):
    """명사 쌓기 경계에 말뭉치가 쓰는 조사를 넣는다. 연쇄가 끊겨 규칙이 풀린다."""
    found = usageCandidates(PILE, config(), index=index)
    assert [finding.rule for finding in found] == ["nounPile"]
    assert [candidate.text for candidate in found[0].candidates] == [
        "당사는 품질 관리를 담당 조직 개편 계획을 세웠습니다.",
        "당사는 품질 관리 담당 조직의 개편 계획을 세웠습니다.",
        "당사는 품질 관리를 담당 조직의 개편 계획을 세웠습니다.",
    ]
    assert [candidate.why for candidate in found[0].candidates] == [
        "`관리를 담당`으로 쓴 글 2편",
        "`조직의 개편`으로 쓴 글 2편",
        "자리 2곳을 함께. `관리를 담당`으로 쓴 글 2편 / `조직의 개편`으로 쓴 글 2편",
    ]


def testEuiChainDropsTheGenitiveTheCorpusDropsThere(index):
    """말뭉치가 `이사회 결의` 로 쓰면 그 `의` 를 뺀 꼴이 후보다."""
    found = usageCandidates(CHAIN, config(), index=index)
    assert [finding.rule for finding in found] == ["euiChain"]
    assert [candidate.text for candidate in found[0].candidates] == [
        "회사는 제1항의 규정에 따라 이사회 결의로 주주 외의 자에게 신주를 배정합니다."
    ]


def testFixingOneRuleIntoAnotherIsDropped(index):
    """규칙은 풀리지만 error 가 느는 꼴은 목록에 안 남는다. 실측된 실패 (쌓기를 풀다 `의` 사슬) 를 막는 자리다."""
    joints = Joints(index)
    assert usageCandidates(TRAP, config(), index=index) == []
    before = sentenceTally(TRAP, config())
    broken = "회사의 조직의 개편 담당 인력 배치 계획은 대표의 승인을 받습니다."
    after = sentenceTally(broken, config())
    assert after.get("nounPile", 0) < before["nounPile"], "쌓기는 풀린다"
    assert after.get("euiChain", 0) > before.get("euiChain", 0), "그 대신 `의` 사슬이 생긴다"
    assert sum(after.values()) == sum(before.values()), "총수로는 갈리지 않는다. 규칙별로 봐야 걸린다"
    assert not keeps(broken, "nounPile", before, config())
    assert candidatesFor(TRAP, "nounPile", joints, config()) == ()


def testNoIndexGivesNothing(tmp_path):
    """색인이 없으면 빈 목록이다. 근거 없이 후보를 내지 않는다."""
    assert usageCandidates(PILE, config(), root=tmp_path) == []
    assert usageCandidates(PILE, Config(), root=tmp_path) == []


def testOnlyJointRulesGetCandidates(index):
    """이음으로 고칠 수 없는 규칙에는 손대지 않는다."""
    text = "이는 해당 사안에 대한 대응이 이루어지고 있는 것으로 판단됩니다."
    assert usageCandidates(text, config(), index=index) == []


def testLimitCutsTheList(index):
    assert usageCandidates(PILE, config(), index=index, limit=0) == []
