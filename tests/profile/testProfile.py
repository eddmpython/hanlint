"""프로파일 층. 분포를 만들고, 저장해 읽고, 벗어난 글을 짚는다."""

from __future__ import annotations

from hanlint import Config, analyzerFor
from hanlint.document import parseMarkdown
from hanlint.fingerprint import buildFingerprint
from hanlint.profile import buildProfile, compareToProfile, loadProfile, saveProfile

PLAIN = "## 절\n\n파일을 엽니다. 표가 보입니다. 열이 다섯입니다. 값을 고칩니다. 저장합니다. 닫습니다.\n"
PLAIN_TOO = "## 절\n\n폴더를 만듭니다. 파일을 옮깁니다. 이름을 바꿉니다. 목록을 봅니다. 끝냅니다. 다시 엽니다.\n"
QUESTIONS = "## 절\n\n왜 열까요? 무엇이 보일까요? 몇 열일까요? 고칠까요? 저장할까요? 닫을까요?\n"


def fingerprintOf(text: str):
    config = Config()
    return buildFingerprint(parseMarkdown(text), analyzerFor(config), config)


def referenceProfile():
    return buildProfile([fingerprintOf(PLAIN), fingerprintOf(PLAIN_TOO)])


def testBuildCountsDocumentsAndMetrics():
    profile = referenceProfile()
    assert profile.documentCount == 2
    assert profile.stats["questionRate"] == (0.0, 0.0)
    assert profile.stats["sentenceLength"][0] > 0
    assert profile.stats["paragraphSentences"] == (6.0, 0.0)


def testSaveAndLoadRoundtrip(tmp_path):
    profile = referenceProfile()
    saveProfile(profile, tmp_path / "profile.json")
    assert loadProfile(tmp_path / "profile.json") == profile


def testCompareFlagsQuestionHeavyText():
    deviations = compareToProfile(fingerprintOf(QUESTIONS), referenceProfile())
    flagged = [d for d in deviations if d.metric == "questionRate"]
    assert flagged and all(d.z > 0 for d in flagged)
    assert {d.scope for d in flagged} == {"document", "section"}
    assert "질문 비율" in flagged[0].describe()


def testCompareSparesReferenceText():
    assert compareToProfile(fingerprintOf(PLAIN), referenceProfile()) == []


def testBuildRefusesEmpty():
    try:
        buildProfile([])
    except ValueError as error:
        assert "글이 없다" in str(error)
    else:
        raise AssertionError("빈 목록을 받아들였다")
