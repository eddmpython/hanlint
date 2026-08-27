"""인라인 제어. 주석으로 규칙을 구간이나 다음 블록에서 끈다. 상투어를 인용하는 글이 첫 사례다."""

from __future__ import annotations

from hanlint import lintText
from hanlint.document import parseMarkdown

CLICHE = "핵심은 속도입니다."


def rulesOf(text: str) -> list[str]:
    return [f.rule for f in lintText(text)]


def testDisableRangeSkipsRuleInside():
    text = f"## 절\n\n<!-- hanlint-disable cliche -->\n\n{CLICHE}\n\n<!-- hanlint-enable cliche -->\n\n{CLICHE}\n"
    findings = lintText(text)
    assert [f.line for f in findings if f.rule == "cliche"] == [9]


def testDisableNextCoversOnlyNextBlock():
    text = f"## 절\n\n<!-- hanlint-disable-next cliche -->\n\n{CLICHE}\n\n{CLICHE}\n"
    assert [f.line for f in lintText(text) if f.rule == "cliche"] == [7]


def testDisableNextLineIsTheSameThing():
    text = f"## 절\n\n<!-- hanlint-disable-next-line cliche -->\n{CLICHE}\n\n{CLICHE}\n"
    assert [f.line for f in lintText(text) if f.rule == "cliche"] == [6]


def testControlWithoutNamesDisablesEverything():
    text = f"## 절\n\n<!-- hanlint-disable -->\n\n{CLICHE}\n"
    assert rulesOf(text) == []


def testUnclosedDisableRunsToEnd():
    text = f"## 절\n\n<!-- hanlint-disable cliche -->\n\n{CLICHE}\n\n{CLICHE}\n"
    assert "cliche" not in rulesOf(text)


def testControlKeepsFollowingParagraphAsProse():
    doc = parseMarkdown(f"<!-- hanlint-disable cliche -->\n{CLICHE}\n")
    assert [b.kind for b in doc.blocks] == ["html", "prose"]
    assert doc.disabled == [("cliche", 1, 2)]


def testOtherRulesStillRunInsideRange():
    text = f"## 절\n\n<!-- hanlint-disable cliche -->\n\n{CLICHE} 결과가 저장되어집니다.\n"
    rules = rulesOf(text)
    assert "cliche" not in rules and "doublePassive" in rules
