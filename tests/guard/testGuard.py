from hashlib import sha256
from unicodedata import normalize

from hanlint import WritingBrief, guardText
from hanlint.guard import GUARD_MEANING, renderGuard


def brief() -> WritingBrief:
    return WritingBrief.fromMapping(
        {
            "version": 1,
            "preset": "report",
            "reader": "결정할 운영자",
            "task": "관찰값을 읽고 다음 조치를 고른다",
            "facts": [
                {"id": "F1", "statement": "해솔 계획은 2026년 8월 31일 시작한다."},
                {"id": "F2", "statement": "예산은 380,000원이다."},
                {"id": "F3", "statement": "명세는 https://example.invalid/check 에 있다."},
                {"id": "F4", "statement": "확인 명령은 `mora check`다."},
            ],
            "mustInclude": ["해솔 계획", "380,000원", "https://example.invalid/check", "`mora check`"],
            "allowedNumbers": ["2026", "8", "31", "380000"],
            "forbidden": ["효과가 입증됐다"],
            "length": {"min": 100, "max": 500},
        }
    )


GOOD = """# 운영 결정

해솔 계획은 2026년 8월 31일 시작하며 예산은 380,000원이다. 명세는 https://example.invalid/check 에 있고,
담당자는 `mora check` 명령으로 설정을 확인한다. 이 자료만으로 효과를 단정하지 않고 다음 관찰을 결정한다.
"""


def testGuardAcceptsOnlyTheDeclaredSurfaceAndDoesNotEditText():
    source = GOOD
    result = guardText(brief(), source, path="결과.md")
    assert result.contractSatisfied and result.violationCount == 0
    assert result.errorCount == 0 and result.lengthSatisfied
    assert source == GOOD
    data = result.asDict()
    assert data["kind"] == "hanlint.guardResult" and data["meaning"] == GUARD_MEANING
    # 길이만 재면 상수 해시로 굳혀도 초록이다. draft 쪽은 값으로 못박는다 (2026-08-31).
    assert len(data["briefSha256"]) == 64
    assert data["draftSha256"] == sha256(source.encode()).hexdigest()


def testGuardReportsEveryDeterministicFailureWithoutCallingItTruth():
    bad = """# 운영 결정

해솔 계획은 2026년 8월 9일 시작한다. 자세한 값은 https://other.invalid 에서 `other run`으로 본다.
효과가 입증됐다.
"""
    result = guardText(brief(), bad)
    assert not result.contractSatisfied
    assert result.missingRequired == ("380,000원", "https://example.invalid/check", "`mora check`")
    assert result.missingNumbers == ("31", "380000") and result.unexpectedNumbers == ("9",)
    assert result.missingUrls == ("https://example.invalid/check",)
    assert result.unexpectedUrls == ("https://other.invalid",)
    assert result.missingCode == ("mora check",) and result.unexpectedCode == ("other run",)
    assert result.forbiddenHits == ("효과가 입증됐다",)
    rendered = renderGuard(result)
    assert "표면 계약 위반" in rendered and "보장하지 않는다" in rendered


def testPlainFactMayBeWrappedAsCodeWithoutBecomingAnUnexpectedFact():
    data = brief().asDict()
    data["facts"].append({"id": "F5", "statement": "보조 명령은 mora show다."})
    data["mustInclude"].append("mora show")
    expanded = WritingBrief.fromMapping(data)
    text = GOOD + "\n보조 명령은 `mora show`다.\n"
    result = guardText(expanded, text)
    assert result.unexpectedCode == ()


def testDeclaredUrlMayBecomeAMarkdownLinkWithoutChangingItsDestination():
    text = GOOD.replace(
        "https://example.invalid/check 에 있고",
        "[명세](https://example.invalid/check)에 있고",
    )
    result = guardText(brief(), text)
    assert result.missingUrls == () and result.unexpectedUrls == ()
    assert result.missingLinks == () and result.unexpectedLinks == ()


def testAnUndeclaredMarkdownLinkDestinationIsStillAContractViolation():
    text = GOOD + "\n[다른 명세](https://other.invalid/check)를 덧붙인다.\n"
    result = guardText(brief(), text)
    assert result.unexpectedUrls == ("https://other.invalid/check",)
    assert result.unexpectedLinks == ("https://other.invalid/check",)


def testNfdDraftCannotBypassAForbiddenNfcSurface():
    text = GOOD + normalize("NFD", "\n효과가 입증됐다.\n")
    result = guardText(brief(), text)
    assert result.forbiddenHits == ("효과가 입증됐다",)


def testCharacterCountIsNfcSoDecomposedHangulDoesNotInflate():
    """자모로 풀어 쓴 한글도 같은 글자 수로 센다.

    길이만 원문을 세고 나머지 표면 검사는 NFC 를 쓰던 때는 같은 글이 NFD 로 오면 글자 수가 두 배가 넘어
    길이 계약이 뒤집혔다. 실측: 13자가 27자로 세어졌다 (2026-08-31).
    """
    nfcBrief = WritingBrief.fromMapping(
        {
            "version": 1,
            "preset": "docs",
            "reader": "처음 쓰는 작성자",
            "task": "글자 수를 센다",
            "facts": [{"id": "F1", "statement": "한국어 글자 수를 센다."}],
            "mustInclude": ["글자 수"],
            "allowedNumbers": [],
            "forbidden": ["자동으로"],
            "length": {"min": 1, "max": 20},
        }
    )
    text = "한국어 글자 수를 센다.\n"
    composed = guardText(nfcBrief, normalize("NFC", text))
    decomposed = guardText(nfcBrief, normalize("NFD", text))
    assert composed.characterCount == decomposed.characterCount
    assert decomposed.characterCount <= 20


def testLengthAndMissingLinkFailuresAreReportedByValue():
    """길이 미달과 빠진 링크 목적지를 값으로 확인한다.

    있던 시험은 `lengthSatisfied` 의 참인 쪽과 `missingLinks == ()` 인 쪽만 봤다. 거짓 쪽을 아무도 안 봐서
    두 필드를 상수로 굳혀도 초록이었다 (2026-08-31).
    """
    short = "## 절\n\n해솔 계획은 짧다.\n"
    result = guardText(brief(), short)
    assert result.lengthSatisfied is False, "길이 미달을 거짓으로 내야 한다"
    assert result.characterCount == len(short)
    assert not result.contractSatisfied
    assert "380,000원" in result.missingRequired

    # brief 가 마크다운 링크 목적지를 요구하면 본문에 그 링크가 없을 때 missingLinks 가 그것을 든다
    linked = WritingBrief.fromMapping(
        {
            "version": 1,
            "preset": "report",
            "reader": "결정할 운영자",
            "task": "명세를 연다",
            "facts": [{"id": "F1", "statement": "명세는 [명세](https://example.invalid/check)에 있다."}],
            "mustInclude": ["명세"],
            "allowedNumbers": [],
            "forbidden": ["효과가 입증됐다"],
            "length": {"min": 1, "max": 500},
        }
    )
    assert guardText(linked, "## 절\n\n명세를 연다.\n").missingLinks == ("https://example.invalid/check",)
    assert guardText(linked, "## 절\n\n[명세](https://example.invalid/check)를 연다.\n").missingLinks == ()
