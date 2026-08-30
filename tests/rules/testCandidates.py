from __future__ import annotations

import json

from hanlint import Config, lintText
from hanlint.report import renderJson, renderText


def one(rule: str, text: str, config: Config | None = None):
    return next(finding for finding in lintText(text, config or Config()) if finding.rule == rule)


def testLongSentenceOffersMeasuredBoundaries():
    text = (
        "이 문장은 앞 사실을 길게 설명하고, 다음 사실은 주어를 다시 세워 아주 구체적으로 설명하며, "
        "마지막 사실도 독자가 한 번에 읽기 어려울 만큼 여러 낱말을 더 붙이고 끝까지 이어 갑니다."
    )
    finding = one("longSentence", text, Config(longSentenceMax=10))
    assert finding.candidates
    assert all(" | " in candidate.text for candidate in finding.candidates)


def testDanglingDeixisUsesPreviousNounAndFitsJosa():
    finding = one("danglingDeixis", "표를 만듭니다. 해당 값을 넣습니다.")
    assert any(candidate.text == "표를 넣습니다." for candidate in finding.candidates)


def testDoublePassiveKeepsInflectionAndPromotesTheApprovedEdit():
    rows = (
        ("값이 자동으로 되어집니다.", "값이 자동으로 됩니다.", "되어집", "됩"),
        ("글이 쓰여지는 중이다.", "글이 쓰이는 중이다.", "여지", "이"),
        ("글이 쓰여져 있었다.", "글이 쓰여 있었다.", "져", ""),
    )
    for source, expected, fragment, replacement in rows:
        finding = one("doublePassive", source)
        assert finding.fix == expected
        assert (finding.fragment, finding.replacement) == (fragment, replacement)
        assert finding.candidates == ()


def testDoublePassiveDoesNotPromoteAnEditInsideAQuotation():
    finding = one("doublePassive", '문서에는 "결과가 저장되어집니다."라고 적혀 있습니다.')
    assert finding.replacement is None
    assert [candidate.text for candidate in finding.candidates] == ['문서에는 "결과가 저장됩니다."라고 적혀 있습니다.']


def testLowSelectionCandidatesAreNotPublished():
    noun = one("nounPile", "가상환경 생성 후 패키지 설치 확인 절차를 따릅니다.")
    ending = one("endingRepeat", "파일을 엽니다. 값을 넣습니다. 표를 만듭니다. 화면을 봅니다.")
    assert not noun.candidates
    assert not ending.candidates


def testCandidatesAppearInJsonAndBelowExemplarsInText():
    finding = one("danglingDeixis", "표를 만듭니다. 해당 값을 넣습니다.")
    data = json.loads(renderJson({"글.md": [finding]}))
    candidate = data["files"][0]["findings"][0]["candidates"][0]
    assert candidate == {"text": "표를 넣습니다.", "why": "바로 앞 문장에 나온 명사 `표`"}
    text = renderText("글.md", [finding])
    assert text.index("본보기") < text.index("후보 (기계가 고르지 않음)")


def testRulesWithoutCandidatesOmitTheJsonField():
    finding = one("cliche", "핵심은 속도입니다.")
    data = json.loads(renderJson({"글.md": [finding]}))
    assert "candidates" not in data["files"][0]["findings"][0]
