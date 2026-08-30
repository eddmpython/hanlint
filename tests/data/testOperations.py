from hanlint.data.operations import (
    SurfaceOperation,
    applyOperation,
    operationFor,
    operationFromApproval,
    projectOperations,
    protectedAtoms,
)


def renderOperation() -> SurfaceOperation:
    operation = operationFromApproval("첫 렌더 결과입니다.", "첫 렌더링 결과입니다.", ("docs",))
    assert operation is not None
    return operation


def testApprovalBecomesOneBoundedSurfaceOperation():
    operation = renderOperation()
    assert (operation.before, operation.after, operation.presets) == ("렌더", "렌더링", ("docs",))
    assert applyOperation("두 번째 렌더 결과입니다.", operation) == "두 번째 렌더링 결과입니다."


def testApplicationAbstainsAtWordProtectedAndAmbiguousPositions():
    operation = renderOperation()
    assert applyOperation("프리렌더 결과입니다.", operation) is None
    assert applyOperation("이미 렌더링 결과입니다.", operation) is None
    assert applyOperation("렌더 뒤 렌더 결과입니다.", operation) is None
    assert applyOperation("`렌더` 결과입니다.", operation) is None
    assert applyOperation("https://example.com/렌더 결과입니다.", operation) is None
    assert applyOperation("[문서](https://example.com/렌더) 결과입니다.", operation) is None


def testExtractionRejectsMeaningAndProtectedFactChanges():
    assert operationFromApproval("이것은 결과입니다.", "이는 결과입니다.", ("docs",)) is None
    assert operationFromApproval("2개가 있습니다.", "3개가 있습니다.", ("docs",)) is None
    assert operationFromApproval("`run`을 씁니다.", "`runs`를 씁니다.", ("docs",)) is None
    assert operationFromApproval("주소는 https://a.example 입니다.", "주소는 https://b.example 입니다.") is None
    assert operationFromApproval("원인을 확인합니다.", "결과에 따라 다시 확인합니다.") is None
    assert operationFromApproval("서울 지점입니다.", "서을 지점입니다.", ("docs",), ("서울",)) is None
    assert protectedAtoms("v2의 `run`은 https://a.example/x.py를 씁니다.")


def testSelectionRequiresOneApplicableConfiguredOperation():
    first = renderOperation()
    second = SurfaceOperation("결과입니다", "결괏값입니다", ("docs",))
    assert operationFor("렌더 결과입니다.", "docs", (first,)) is not None
    assert operationFor("렌더 결과입니다.", "blog", (first,)) is None
    assert operationFor("렌더 결과입니다.", "docs", (first,), ("렌더",)) is None
    assert operationFor("렌더 결과입니다.", "docs", (first, second)) is None


def testProjectOperationsValidateSafetyAndSelectors():
    entry = {"before": "여러가지", "after": "여러 가지", "presets": ["blog"]}
    operations = projectOperations([entry], ("blog", "docs"))
    assert applyOperation("여러가지 방법입니다.", operations[0]) == "여러 가지 방법입니다."
    for invalid in (
        [entry, entry],
        [{**entry, "presets": []}],
        [{**entry, "presets": ["unknown"]}],
        [{**entry, "before": "이것은", "after": "이는"}],
        [{**entry, "before": "버전 2", "after": "버전 3"}],
        [{**entry, "extra": True}],
    ):
        try:
            projectOperations(invalid, ("blog", "docs"))
        except ValueError:
            pass
        else:
            raise AssertionError(invalid)
