from hanlint import learnText


def candidateFor(rule: str, before: str, after: str):
    return [candidate for candidate in learnText(before, after) if candidate.rule == rule]


def testLearnsAResolvedOneToOneSentence():
    candidates = candidateFor("translationese", "설계에 대한 이해가 필요합니다.", "설계를 알아야 합니다.")
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.before == "설계에 대한 이해가 필요합니다."
    assert candidate.after == "설계를 알아야 합니다."
    assert candidate.beforeLine == 1 and candidate.afterLines == (1,)
    assert candidate.sentence == candidate.before
    assert candidate.cue == "에 대한" and candidate.reader == "new"
    assert candidate.presets == ("blog",)


def testLearnsOneSentenceSplitIntoSeveral():
    candidates = candidateFor(
        "translationese",
        "설계에 대한 이해가 필요합니다.",
        "설계를 알아야 합니다. 예제를 직접 실행합니다.",
    )
    assert len(candidates) == 1
    assert candidates[0].after == "설계를 알아야 합니다. 예제를 직접 실행합니다."
    assert candidates[0].afterLines == (1,)


def testSkipsWhenTheSameRuleRemains():
    assert (
        candidateFor(
            "translationese",
            "설계에 대한 이해가 필요합니다.",
            "새 설계에 대한 이해가 필요합니다.",
        )
        == []
    )


def testSkipsAmbiguousManyToManyRewrite():
    before = "설계에 대한 이해가 필요합니다. 결과를 기록합니다."
    after = "설계를 알아야 합니다. 결과는 표에 적습니다. 담당자가 검토합니다."
    assert candidateFor("translationese", before, after) == []


def testSkipsAnUnchangedSentenceThatOnlyMoved():
    bad = "설계에 대한 이해가 필요합니다."
    other = "결과를 기록합니다."
    assert candidateFor("translationese", f"{bad} {other}", f"{other} {bad}") == []


def testKeepsApprovedInlineMarkdownSeparateFromMatchSentence():
    candidates = candidateFor(
        "cliche",
        "핵심은 `make_qr`입니다.",
        "`make_qr`가 QR코드를 만듭니다.",
    )
    assert len(candidates) == 1
    assert candidates[0].before == "핵심은 `make_qr`입니다."
    assert candidates[0].after == "`make_qr`가 QR코드를 만듭니다."
    assert candidates[0].sentence == "핵심은 make_qr입니다."
