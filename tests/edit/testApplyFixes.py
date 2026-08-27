"""고치기 층. 조각을 원문에서 찾아 바꾸고, 못 찾거나 여럿이면 건너뛴다. 고친 뒤 같은 지적이 사라져야 한다."""

from __future__ import annotations

from hanlint import lintText
from hanlint.edit import applyFixes

DOT = "."
TEXT = (
    "## 절\n\n모든 분야에 있어서 기준이 필요합니다. 파일을 확인하세요" + DOT + " 노력하지 않으면 안 됩니다.\n\n"
    "`에 있어서` 는 번역투라고 **설명**합니다.\n"
)


def rulesOf(text: str) -> set[str]:
    return {f.rule for f in lintText(text)}


def testAppliesEveryMachineFixAndFindingsVanish():
    result = applyFixes(TEXT, lintText(TEXT))
    assert [(line, fragment, replacement) for line, fragment, replacement in result.applied] == [
        (3, "에 있어서", "에서"),
        (3, "세요" + DOT, "세요"),
        (3, "하지 않으면 안 됩니다", "해야 합니다"),
    ]
    assert result.skipped == ()
    assert "모든 분야에서 기준이 필요합니다. 파일을 확인하세요 노력해야 합니다." in result.text
    assert "`에 있어서` 는" in result.text
    before = rulesOf(TEXT)
    after = rulesOf(result.text)
    assert {"translationese", "imperativePeriod", "doubleNegative"} <= before
    assert not {"translationese", "imperativePeriod", "doubleNegative"} & after


def testSkipsWhenFragmentIsAmbiguous():
    text = "## 절\n\n모든 분야에 있어서 기준과 방식에 있어서 차이가 있습니다.\n"
    result = applyFixes(text, lintText(text))
    assert result.text == text
    assert len(result.skipped) == 2 and all("여러 번" in reason for _, _, reason in result.skipped)


def testSkipsWhenFragmentIsNotInRawText():
    text = "## 절\n\n모든 분야에 **있어서** 기준이 필요합니다.\n"
    result = applyFixes(text, lintText(text))
    assert result.text == text
    assert result.applied == () and result.skipped and "못 찾았다" in result.skipped[0][2]


def testNothingToFixKeepsTextIdentical():
    text = "## 절\n\n파일을 엽니다. 그러면 표가 생길까요? 작업 폴더에 생깁니다.\n"
    result = applyFixes(text, lintText(text))
    assert result.text == text and result.applied == () and result.skipped == ()
