"""프로파일 층. 분포를 만들고, 저장해 읽고, 벗어난 글을 짚는다. 바닥값이 사소한 차이를 짚지 않게 한다."""

from __future__ import annotations

from hanlint import Config
from hanlint.document import parseMarkdown
from hanlint.fingerprint import buildFingerprint
from hanlint.profile import buildProfile, compareToProfile, loadProfile, saveProfile

PLAIN = "## 절\n\n파일을 엽니다. 표가 보입니다. 열이 다섯입니다. 값을 고칩니다. 저장합니다. 닫습니다.\n"
PLAIN_TOO = "## 절\n\n폴더를 만듭니다. 파일을 옮깁니다. 이름을 바꿉니다. 목록을 봅니다. 끝냅니다. 다시 엽니다.\n"
LONG = (
    "## 절\n\n파일을 열고 표를 확인한 다음 열 다섯 개의 이름을 하나씩 읽어 두고 값을 고친 뒤 저장합니다. "
    "폴더를 만들고 파일을 옮기고 이름을 바꾸고 목록을 다시 보고 끝낸 다음 다시 처음부터 엽니다. "
    "표가 보이면 열의 순서를 적어 두고 값을 고친 뒤 저장하고 닫고 다시 열어 확인합니다. "
    "이름을 바꾼 파일을 목록에서 찾아 열고 표를 확인하고 값을 고치고 저장합니다. "
    "그다음 폴더를 정리하고 파일을 옮기고 목록을 다시 보고 끝냅니다.\n"
)


def fingerprintOf(text: str):
    config = Config()
    return buildFingerprint(parseMarkdown(text), config)


def referenceProfile():
    return buildProfile([fingerprintOf(PLAIN), fingerprintOf(PLAIN_TOO)])


def testBuildCountsDocumentsAndMetrics():
    profile = referenceProfile()
    assert profile.documentCount == 2
    assert profile.stats["questionRate"] == (0.0, 0.0)
    assert profile.stats["sentenceLength"][0] > 0
    assert profile.stats["paragraphSentences"] == (6.0, 0.0)
    assert "causalDensity" not in profile.stats


def testSaveAndLoadRoundtrip(tmp_path):
    profile = referenceProfile()
    saveProfile(profile, tmp_path / "profile.json")
    assert loadProfile(tmp_path / "profile.json") == profile


def testCompareFlagsLongSentenceText():
    deviations = compareToProfile(fingerprintOf(LONG), referenceProfile())
    flagged = [d for d in deviations if d.metric == "sentenceLength"]
    assert flagged and all(d.z > 0 for d in flagged)
    assert {d.scope for d in flagged} == {"document", "section"}
    assert "문장 길이" in flagged[0].describe()


def testCompareSparesReferenceText():
    assert compareToProfile(fingerprintOf(PLAIN), referenceProfile()) == []


def testFloorKeepsTinyDifferencesQuiet():
    almost = "## 절\n\n파일을 엽니다. 표가 보입니다. 열이 다섯입니다. 값을 고칩니다. 저장합니다. 닫아요.\n"
    deviations = compareToProfile(fingerprintOf(almost), referenceProfile())
    assert all(not d.metric.startswith("ending:") for d in deviations)


def testBuildRefusesEmpty():
    try:
        buildProfile([])
    except ValueError as error:
        assert "글이 없다" in str(error)
    else:
        raise AssertionError("빈 목록을 받아들였다")
