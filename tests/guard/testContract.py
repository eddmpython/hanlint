import json

import pytest

from hanlint import Config, Contract, Patch, check, ruleNames, verifyPatch
from hanlint.guard import CHECK_MEANING, PATCH_MEANING


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


def testPatchMappingIsClosedAndDeterministicallyHashed():
    data = {"reason": "missingNumbers", "before": "금액", "after": "예산"}
    patch = Patch.fromMapping(data)
    assert patch.digest == Patch.fromMapping({key: data[key] for key in reversed(data)}).digest
    with pytest.raises(ValueError, match="모르는 키"):
        Patch.fromMapping({**data, "score": 1})
    with pytest.raises(ValueError, match="달라야"):
        Patch.fromMapping({"reason": "x", "before": "같다", "after": "같다"})
