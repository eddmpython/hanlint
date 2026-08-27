"""커밋 메시지 판정기의 양성과 음성 fixture. 판정 정본은 scripts/commitMessage.py.

통과해야 할 메시지가 통과하고, 어겨야 할 메시지가 정확한 코드로 걸리는지 본다. 코드로 단정하므로
문구가 바뀌어도 시험이 흔들리지 않는다.
"""

from __future__ import annotations

from scripts.commitMessage import checkCommitMessage, normalizeMessage

GOOD = (
    "규칙: 이중 피동을 잡는다\n"
    "\n"
    "rules/sentence/doublePassive.py 를 더하고 fixture 를 둔다. 되어지다 처럼 피동에 -어지다 를\n"
    "또 붙인 문장을 짚는다. 근거는 국립국어원 어문 규범과 004 실측이다.\n"
    "검증: pytest green. fixture 의 catch 3건 spare 3건.\n"
)


def codes(message: str) -> list[str]:
    return [v.code for v in checkCommitMessage(message)]


def testAcceptsWellFormedMessage():
    assert codes(GOOD) == []


def testAcceptsGeneratedSubjects():
    assert codes("Merge branch 'x'\n") == []
    assert codes('Revert "규칙: 무엇"\n') == []


def testNormalizeDropsCommentsAndScissors():
    raw = "# 주석\n제목: 요약입니다\n\n본문   \n------ >8 ------\ndiff 내용\n"
    assert normalizeMessage(raw) == ["제목: 요약입니다", "", "본문"]


def testRejectsEmpty():
    assert codes("\n# 주석만\n") == ["empty"]


def testRejectsTraceTerms():
    assert "traceTerm" in codes(GOOD.replace("검증:", "Co-Authored-By: x\n검증:"))
    assert "traceTerm" in codes(GOOD.replace("규칙:", "규칙 (AI):"))
    assert "traceTerm" not in codes(GOOD.replace("규칙:", "규칙 chain fail:"))


def testRejectsDashes():
    assert "dash" in codes(GOOD.replace("잡는다", "잡는다 \u2014 전부"))
    assert "dash" in codes(GOOD.replace("3건", "3\u20135건"))


def testRejectsSubjectProblems():
    assert "subjectForm" in codes(GOOD.replace("규칙: 이중 피동을 잡는다", "이중 피동을 잡는다"))
    assert "subjectPunctuation" in codes(GOOD.replace("잡는다\n", "잡는다.\n", 1))
    assert "subjectTooLong" in codes(GOOD.replace("이중 피동을 잡는다", "이중 피동을 잡는다 " * 8))
    assert "subjectNotKorean" in codes(
        GOOD.replace("규칙: 이중 피동을 잡는다", "rules: catch double passive")
    )
    assert "summaryTooThin" in codes(GOOD.replace("이중 피동을 잡는다", "수리"))
    assert "categoryTooLong" in codes(GOOD.replace("규칙:", "아주아주아주아주아주긴분류이름입니다:"))


def testRejectsBodyProblems():
    assert codes("규칙: 이중 피동을 잡는다\n") == ["bodyMissing"]
    assert "blankLineMissing" in codes(
        "규칙: 이중 피동을 잡는다\n본문 첫 줄이 바로 온다\n"
        "검증: pytest green 이고 두 줄 이상이며 여든 자를 넘기려고 길게 쓴 줄이다\n"
    )
    assert "bodyTooShort" in codes(
        "규칙: 이중 피동을 잡는다\n\n"
        "검증: pytest green 이고 여든 자를 넘기려고 아주 길게 쓴 한 줄짜리 본문이라 두 줄 규칙에 걸린다\n"
    )
    assert "bodyTooThin" in codes("규칙: 이중 피동을 잡는다\n\n짧다.\n검증: green\n")
    assert "verificationMissing" in codes(
        GOOD.replace("검증: pytest green. fixture 의 catch 3건 spare 3건.", "그리고 끝.")
    )
    assert "bodyLineTooLong" in codes(
        GOOD.replace("검증: pytest green.", "검증: pytest green. " + "가" * 100)
    )
    assert "bodyNotKorean" in codes(
        "규칙: 이중 피동을 잡는다\n\n"
        + "english only body line number one is here\n"
        + "verification: pytest green and long enough to pass the thin check\n"
    )
