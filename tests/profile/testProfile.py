"""프로파일 층. 정수 지표의 히스토그램과 백분위를 만들고, 저장해 읽고, 규칙이 그것과 견준다."""

from __future__ import annotations

import pytest

from hanlint import Config, fingerprint, lintText
from hanlint.config import PRESETS, PROFILE_OF
from hanlint.data.profiles import CAP, histogram, loadProfile, profileOf, saveProfile
from hanlint.profile import buildProfile

PLAIN = "## 절\n\n파일을 엽니다. 표가 보입니다. 열이 다섯입니다. 값을 고칩니다. 저장합니다. 닫습니다.\n"
PLAIN_TOO = "## 절\n\n폴더를 만듭니다. 파일을 옮깁니다. 이름을 바꿉니다. 목록을 봅니다. 끝냅니다. 다시 엽니다.\n"
LONG = (
    "## 절\n\n파일을 열고 표를 확인한 다음 열 다섯 개의 이름을 하나씩 읽어 두고 값을 고친 뒤 저장하고 폴더를 만들고 파일을 "
    "옮기고 이름을 바꾸고 목록을 다시 보고 끝낸 다음 다시 처음부터 열어 표가 보이면 열의 순서를 적어 두고 값을 고친 뒤 "
    "저장하고 닫고 다시 열어 확인합니다.\n"
)


def testHistogramCountsAndPercentilesAreExact():
    hist = histogram([1, 2, 2, 3, 3, 3, 10])
    assert hist.total == 7 and hist.counts == {1: 1, 2: 2, 3: 3, 10: 1}
    assert hist.percentile(50) == 3 and hist.percentile(99) == 10
    # 값이 이 이상인 몫은 천분율 정수다. 10 이상은 7 가운데 1 이라 142
    assert hist.shareAtOrAbove(10) == 142 and hist.shareAtOrAbove(1) == 1000
    assert histogram([CAP + 50]).counts == {CAP: 1}


def testBuildCountsDocumentsSentencesAndRuns():
    profile = buildProfile([fingerprint(PLAIN), fingerprint(PLAIN_TOO)])
    assert profile.documents == 2 and profile.sentences == 12
    assert profile.sentence["length"].total == 12
    assert profile.paragraph["sentenceCount"].counts == {6: 2}
    # 합니다체 열두 문장이 문단마다 한 부류로 이어진다
    assert profile.endingRuns is not None and profile.endingRuns.counts == {6: 2}
    assert profile.rates["question"]["p50"] == 0.0


def testSaveAndLoadRoundtrip(tmp_path):
    profile = buildProfile([fingerprint(PLAIN)])
    saveProfile(profile, tmp_path / "profile.json")
    loaded = loadProfile(tmp_path / "profile.json")
    assert loaded.sentence["length"].counts == profile.sentence["length"].counts
    assert loaded.kind == "custom" and loaded.label == "참조 글 1편"


def testShippedProfilesCoverEveryPresetKind():
    for preset in PRESETS:
        assert preset in PROFILE_OF
    assert profileOf("blog") is not None and profileOf("technicalDocs") is not None


def testRuleContrastsWithTheUserProfile(tmp_path):
    path = tmp_path / "profile.json"
    saveProfile(buildProfile([fingerprint(PLAIN), fingerprint(PLAIN_TOO)]), path)
    config = Config()
    config.profile = str(path)
    found = [f for f in lintText(LONG, config) if f.rule == "outsideProfile"]
    assert found and "참조 글 2편" in found[0].why and "문장 길이" in found[0].why
    assert not [f for f in lintText(PLAIN, config) if f.rule == "outsideProfile"]


def testBuildRefusesEmpty():
    with pytest.raises(ValueError, match="글이 없다"):
        buildProfile([])
