"""이음 계약. 말뭉치가 그 자리에 쓴 조사만 세고, 없는 조사는 지어내지 않는다."""

from __future__ import annotations

from pathlib import Path

import pytest

from hanlint.usage import Joints, buildIndex, jointParticles, loadIndex, readDocuments

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "fixtures" / "usage" / "joints"


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    root = tmp_path_factory.mktemp("joints")
    buildIndex("report", readDocuments(CORPUS), root)
    return loadIndex("report", root)


def testCountsTheParticleTheCorpusActuallyUsed(index):
    """`정관에서 배당` 을 쓴 글이 둘이면 `에서` 를 둘로 센다. 다른 조사는 만들지 않는다."""
    assert jointParticles(index, "정관", "배당") == (type(jointParticles(index, "정관", "배당")[0])("에서", 2),)
    assert [(joint.particle, joint.documents) for joint in jointParticles(index, "관리", "담당")] == [("를", 2)]


def testEmptyParticleMeansTheCorpusPilesThemToo(index):
    """붙여 쓴 꼴도 이음이다. `의` 사슬에서는 그 빈 조사가 `의` 를 빼는 고침이 된다."""
    assert [(joint.particle, joint.documents) for joint in jointParticles(index, "이사회", "결의")] == [("", 2)]


def testUnknownWordsAndUnseenPairsGiveNothing(index):
    """색인에 없는 낱말과, 있어도 나란히 온 적 없는 쌍은 빈 답이다."""
    assert jointParticles(index, "없는낱말", "결의") == ()
    assert jointParticles(index, "결의", "없는낱말") == ()
    assert jointParticles(index, "정관", "인력") == ()


def testTooFewDocumentsIsNotAJoint(index):
    """한 편에만 있는 꼴은 한 회사의 버릇이라 이음으로 보지 않는다."""
    assert [(joint.particle, joint.documents) for joint in jointParticles(index, "계획", "이사회")] == [("을", 1)]
    assert Joints(index).particles("계획", "이사회") == ()
    assert Joints(index, minimum=1).particles("계획", "이사회")[0].particle == "을"


def testAnswersAreRemembered(index):
    """같은 이음을 두 번 물으면 색인을 한 번만 읽는다. 한 글에서 같은 쌍이 여러 번 나온다."""
    joints = Joints(index)
    first = joints.particles("정관", "배당")
    assert joints.queries == 1
    assert joints.particles("정관", "배당") == first
    assert joints.queries == 1, "두 번째는 기억한 답이다"
    joints.particles("이사회", "결의")
    assert joints.queries == 2
