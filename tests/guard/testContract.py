import json

import pytest

from hanlint import Config, Contract, Patch, check, contractFromText, ruleNames, verifyPatch
from hanlint.guard import CHECK_MEANING, PATCH_MEANING, contractFromTextV2, renderCheck


def contract() -> Contract:
    return Contract(
        reader="배포를 결정할 운영자",
        goal="예산과 명세를 확인한다",
        facts=(
            "예산은 380,000원이다.",
            "명세는 https://example.invalid/check 에 있다.",
            "확인 명령은 `mora check`다.",
        ),
    )


def surfaceConfig() -> Config:
    return Config(disable=set(ruleNames()))


def testContractFromTextKeepsSourceOrderNormalizesAndRemovesDuplicateLines():
    text = """---
published: 2026-09-01
source: https://example.invalid/source
---

글 3은 [명세](https://example.invalid/spec)를 `mora check`로 확인한다.
published: 2026-09-01
"""
    contract = contractFromText(text, "배포를 결정할 운영자", "명세를 확인한다")
    assert contract.facts == (
        "published: 2026-09-01",
        "source: https://example.invalid/source",
        "글 3은 [명세](https://example.invalid/spec)를 `mora check`로 확인한다.",
    )
    assert check(text, contract, surfaceConfig()).surface.violationCount == 0


def testContractFromTextPrefersALineThatCoversMoreProtectedAtoms():
    text = """계획은 2026년에 시작한다.
2026년 계획의 명세는 https://example.invalid/spec 에 있다.
"""
    contract = contractFromText(text, "운영자", "계획과 명세를 확인한다")
    assert contract.facts == ("2026년 계획의 명세는 https://example.invalid/spec 에 있다.",)


def testContractFromTextRefusesToInventMeaningOrReaderAtoms():
    with pytest.raises(ValueError, match="facts를 직접 작성"):
        contractFromText("숫자와 링크가 없는 글입니다.", "독자", "내용을 읽는다")
    with pytest.raises(ValueError, match="missingNumbers=7"):
        contractFromText("예산은 3원이다.", "7명의 운영자", "예산을 확인한다")


def testCheckReturnsAStableReceiptWithoutAQualityVerdict():
    text = "예산은 400,000원이다. 명세는 https://example.invalid/check 에 있다. `mora check`로 확인한다."
    result = check(text, contract(), surfaceConfig(), "draft.md")
    data = result.asDict()
    assert data["kind"] == "hanlint.checkResult"
    assert data["surface"]["missingNumbers"] == ["380000"]
    assert data["surface"]["unexpectedNumbers"] == ["400000"]
    assert data["violationCount"] == 2
    assert data["meaning"] == CHECK_MEANING
    assert "pass" not in json.dumps(data, ensure_ascii=False).casefold()


def testVersionTwoSeparatesApprovedFactsAutomaticSurfaceAndExactOutline():
    text = """# 데이터프레임 라이브러리 2가지

## pandas

문서는 [여기](https://example.invalid/pandas)에서 보고 `import pandas`를 실행한다.

## Polars

2개 라이브러리를 비교한다.
"""
    contractV2 = contractFromTextV2(text, "데이터 도구를 고르는 개발자", "용도별 라이브러리를 비교한다")
    assert contractV2.facts == ()
    assert contractV2.outline.headings == ("pandas", "Polars")
    assert contractV2.surface.numbers == ("2",)
    assert contractV2.surface.code == ("import pandas",)
    assert contractV2.surface.links == ("https://example.invalid/pandas",)
    assert check(text, contractV2, surfaceConfig()).violationCount == 0


@pytest.mark.parametrize(
    ("body", "actual"),
    [
        ("## pandas\n\n본문", ["pandas"]),
        ("## pandas\n\n본문\n\n## DuckDB\n\n본문\n\n## Polars\n\n본문", ["pandas", "DuckDB", "Polars"]),
        ("## Polars\n\n본문\n\n## pandas\n\n본문", ["Polars", "pandas"]),
    ],
)
def testVersionTwoCatchesMissingExtraAndReorderedHeadings(body, actual):
    source = "## pandas\n\n본문\n\n## Polars\n\n본문"
    contractV2 = contractFromTextV2(source, "개발자", "비교한다")
    result = check(body, contractV2, surfaceConfig())
    assert result.outline.actual == tuple(actual)
    assert result.outline.violationCount > 0
    assert result.violationCount == result.outline.violationCount


def testTextReceiptKeepsFullHeadingsAndNamesTheNextAction():
    source = "## 아주 긴 데이터프레임 라이브러리 제목을 자르지 않는다\n\n본문"
    contractV2 = contractFromTextV2(source, "개발자", "비교한다")
    receipt = renderCheck(check(source, contractV2, surfaceConfig()))
    assert "계약 위반 없음" in receipt
    assert "아주 긴 데이터프레임 라이브러리 제목을 자르지 않는다" in receipt
    assert "다음:" in receipt


def testPatchMustNameAndReduceAnExistingViolation():
    text = "예산은 400,000원이다. 명세는 https://example.invalid/check 에 있다. `mora check`로 확인한다."
    patch = Patch("unexpectedNumbers", "400,000", "380,000")
    result = verifyPatch(text, patch, contract(), surfaceConfig())
    assert result.verified
    assert result.resultText.startswith("예산은 380,000원")
    assert result.asDict()["reason"] == {
        "name": "unexpectedNumbers",
        "before": 1,
        "after": 0,
        "reduced": True,
    }
    assert result.asDict()["meaning"] == PATCH_MEANING


@pytest.mark.parametrize(
    ("patch", "matchCount", "reasonBefore"),
    [
        (Patch("missingNumbers", "예산은", "금액은"), 1, 1),
        (Patch("unexpectedNumbers", "없다", "있다"), 0, 1),
        (Patch("unexpectedNumbers", "다.", "다!"), 3, 1),
        (Patch("unknownRule", "400,000", "380,000"), 1, 0),
    ],
)
def testPatchRejectsUnreducedReasonsMissingTargetsAndAmbiguousTargets(patch, matchCount, reasonBefore):
    text = "예산은 400,000원이다. 명세는 https://example.invalid/check 에 있다. `mora check`로 확인한다."
    result = verifyPatch(text, patch, contract(), surfaceConfig())
    assert not result.verified
    assert result.matchCount == matchCount
    assert result.reasonBefore == reasonBefore


def testPatchRejectsANewProtectedAtomViolation():
    text = "예산은 400,000원이다. 명세는 https://example.invalid/check 에 있다. `mora check`로 확인한다."
    patch = Patch("unexpectedNumbers", "400,000", "500,000")
    result = verifyPatch(text, patch, contract(), surfaceConfig())
    assert not result.verified
    assert result.newSurfaceIssues == (("unexpectedNumbers", "500000"),)


def testVersionTwoPatchRejectsANewOutlineViolation():
    source = "3개를 비교한다.\n\n## pandas\n\n본문\n\n## Polars\n\n본문"
    contractV2 = contractFromTextV2("2개를 비교한다." + source[source.index("\n\n") :], "개발자", "비교한다")
    patch = Patch("unexpectedNumbers", "3개를 비교한다.\n\n## pandas", "2개를 비교한다.\n\n## DuckDB")
    result = verifyPatch(source, patch, contractV2, surfaceConfig())
    assert not result.verified
    assert result.reasonReduced
    assert result.newContractIssues == (("outline", "1:pandas:DuckDB"),)
    assert result.asDict()["newContractIssues"] == [{"kind": "outline", "value": "1:pandas:DuckDB"}]


def testPatchMappingIsClosedAndDeterministicallyHashed():
    data = {"reason": "missingNumbers", "before": "금액", "after": "예산"}
    patch = Patch.fromMapping(data)
    assert patch.digest == Patch.fromMapping({key: data[key] for key in reversed(data)}).digest
    with pytest.raises(ValueError, match="모르는 키"):
        Patch.fromMapping({**data, "score": 1})
    with pytest.raises(ValueError, match="달라야"):
        Patch.fromMapping({"reason": "x", "before": "같다", "after": "같다"})
