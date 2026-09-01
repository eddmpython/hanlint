from hanlint.guard.surface import surfaceDiff


def testCompilesProtectedAtomsFromTheContractWithoutDuplicateLists():
    contract = (
        "2026년 운영자\n"
        "[명세](https://example.invalid/spec)를 읽는다\n"
        "예산은 380,000원이고 `mora check`로 확인한다"
    )
    text = "2026년 예산은 380,000원이다. [명세](https://example.invalid/spec)는 `mora check`로 확인한다."
    assert surfaceDiff(contract, text).violationCount == 0


def testReportsBothMissingAndUndeclaredAtomsInStableOrder():
    contract = "2와 10을 `check`로 확인한다. https://example.invalid/a"
    text = "3을 `other`로 확인한다. https://example.invalid/b"
    result = surfaceDiff(contract, text)
    assert result.missingNumbers == ("10", "2")
    assert result.unexpectedNumbers == ("3",)
    assert result.missingUrls == ("https://example.invalid/a",)
    assert result.unexpectedUrls == ("https://example.invalid/b",)
    assert result.missingCode == ("check",)
    assert result.unexpectedCode == ("other",)
