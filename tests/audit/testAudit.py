from hanlint import auditText

SAMPLE = """## 첫 절

파일을 엽니다. 파일에 값을, 조심해서, 넣습니다. 그러면 표가 생깁니다.

고양이가 웁니다. 고양이는 배가 고픕니다.

```python
print(1)
```

## 둘째 절

값을 저장합니다. 저장한 값은 어디에 남을까요? 작업 폴더입니다.
"""


def testCountsAndShapes():
    audit = auditText(SAMPLE)
    assert audit.sentenceCount == 8
    assert audit.paragraphCount == 3
    assert audit.sectionCount == 2
    assert audit.questionCount == 1
    assert [s.title for s in audit.sections] == ["첫 절", "둘째 절"]
    assert audit.sections[0].codeBlocks == 1 and audit.sections[0].paragraphs == 2
    assert audit.headingLevels == (2, 2)


def testRhythmAndRatios():
    audit = auditText(SAMPLE)
    assert audit.rhythm.mean > 0 and audit.rhythm.burstiness >= 0
    assert sum(count for _, count in audit.rhythm.histogram) == audit.sentenceCount
    assert 0 < audit.commaRatio < 1
    assert abs(sum(ratio for _, ratio in audit.endingMix) - 1.0) < 1e-9
    assert audit.endingMix[0][0] == "니다"
    assert sum(count for _, count in audit.paragraphHistogram) == audit.paragraphCount


def testDensityIsPerThousandWords():
    audit = auditText(SAMPLE)
    assert audit.density.connectors > 0
    assert audit.density.emphasis == 0.0


def testValleysFindTopicBreak():
    audit = auditText(SAMPLE)
    assert [v.line for v in audit.valleys] == [5]
    assert audit.overlaps[0][1] == 0.0


def testEmptyDocument():
    audit = auditText("")
    assert audit.sentenceCount == 0 and audit.rhythm.mean == 0.0 and audit.commaRatio == 0.0
    assert audit.asDict()["sentenceCount"] == 0
