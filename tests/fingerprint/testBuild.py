from hanlint.config import Config
from hanlint.document import parseMarkdown
from hanlint.fingerprint import buildFingerprint
from hanlint.fingerprint.markers import endingOf, moodOf
from hanlint.fingerprint.topics import overlap, topicsOf
from hanlint.rules import runAll

SAMPLE = """---
title: 제목
---

이 글은 여섯 가지를 소개합니다. 그래서 파일을 엽니다. 파일은 어디에 생겼을까요?

## 첫 절

`sales.csv` 를 읽습니다. 이것으로 표가 만들어집니다.
둘째 줄의 문장입니다.

```python
print(1)
```

그리고 값을 넣습니다. 그리고 확인해 봅니다.

## 둘째 절

다섯 가지가 같은 답을 돌려줬습니다. 뒤에서 자세히 다루겠습니다.
"""


def build(text: str = SAMPLE, config: Config | None = None):
    return buildFingerprint(parseMarkdown(text), config)


def testSentencesCarryLinesAndIndexes():
    doc = build()
    texts = [s.text for s in doc.sentences]
    assert texts[0] == "이 글은 여섯 가지를 소개합니다."
    assert [s.line for s in doc.sentences[:3]] == [5, 5, 5]
    assert texts[3] == "sales.csv 를 읽습니다."
    assert doc.sentences[5].text == "둘째 줄의 문장입니다."
    assert doc.sentences[5].line == 10
    assert [s.index for s in doc.sentences] == list(range(len(doc.sentences)))


def testParagraphsAndSections():
    doc = build()
    assert [s.title for s in doc.sections] == ["", "첫 절", "둘째 절"]
    first = doc.sections[1]
    assert [p.sentenceCount for p in first.paragraphs] == [3, 2]
    assert first.paragraphs[0].overlapWithPrevious is None
    assert first.paragraphs[1].followsProseDirectly is False
    assert first.count("code") == 1
    assert doc.intro.isIntro and doc.bodySections[0].title == "첫 절"


def testMarkersAreCounted():
    doc = build()
    intro = doc.intro.paragraphs[0]
    assert intro.causalTotal == 1
    assert doc.sentences[1].connectorStart == "그래서"
    assert doc.sentences[2].mood == "의문"
    assert doc.questionCount == 1
    assert doc.sentences[3].deixis == ()
    assert doc.sentences[4].text.startswith("이것으로") and doc.sentences[4].deixis == ("이것으로",)
    assert doc.readerCallCount >= 1
    assert doc.countPromises[0][:2] == (6, "가지") and doc.countPromises[1][:2] == (5, "가지")
    assert doc.reader.final.promises and doc.reader.final.promises[0][1].startswith("뒤에서")
    assert doc.reader.final.recalls == ()


def testDictionaryMatchesLandInSentence():
    doc = build("핵심은 속도입니다. 모든 분야에 있어서 기준이 필요합니다.\n")
    assert doc.sentences[0].matches[0].dictionary == "cliches"
    match = doc.sentences[1].matches[0]
    assert match.dictionary == "translationese" and match.fix == "에서"


def testQuotedSpansSkipDictionaryAndDeixis():
    doc = build(
        'AI 가 자주 쓰는 표현은 `핵심은`, "결국 중요한 것은" 처럼 지웁니다. 「이것」 은 지시어입니다. 핵심은 속도입니다.\n'
    )
    first = doc.sentences[0]
    assert first.matches == () and len(first.quoted) == 2
    assert doc.sentences[1].deixis == () and doc.sentences[1].quoted
    assert doc.sentences[2].matches[0].text == "핵심은" and doc.sentences[2].quoted == ()


def testCodeSpanFollowsEmphasisAndLinks():
    doc = build("**굵게** [링크](https://x) `a b` 뒤 `핵심은` 끝.\n")
    sentence = doc.sentences[0]
    assert sentence.text == "굵게 링크 a b 뒤 핵심은 끝."
    assert sentence.quoted == ((6, 9), (12, 15))
    assert sentence.matches == ()


def testConfigDictionaryExtends():
    config = Config(dictionary={"cliches": ["우리의 여정"]})
    doc = build("우리의 여정이 시작됩니다.\n", config)
    assert doc.sentences[0].matches[0].text == "우리의 여정"


def testEndingsAndMood():
    assert endingOf("파일을 엽니다.") == "니다"
    assert endingOf("파일을 연다.") == "다"
    assert endingOf("그것이 답일 것입니다.") == "것이다"
    assert endingOf("열어 보세요") == "명령"
    assert endingOf("열까요?") == "의문"
    assert endingOf("열죠.") == "죠"
    assert endingOf("`코드`") == "없음"
    assert moodOf("열까요?", "의문") == "의문"
    assert moodOf("열어 보세요", "명령") == "명령"
    assert moodOf("엽니다.", "니다") == "평서"


def testTopicsAndOverlap():
    a = topicsOf("파일을 열어 sales.csv 표를 만듭니다.")
    b = topicsOf("표에 열이 다섯 있고 파일은 크다.")
    assert "파일" in a and "표" in a and "만듭니다" not in a
    assert 0 < overlap(a, b) < 1
    assert overlap(frozenset(), a) == 0.0


def testQuoteSpansSurviveSentenceSplitInsideTheQuote():
    """따옴표 안에서 문장이 잘려도 두 조각이 모두 인용 구간을 든다.

    문장 안에서 따옴표 쌍을 재던 때는 `TERMINAL` 이 물음표 뒤 공백에서 잘라 조각마다 따옴표가 하나씩만
    남았고 쌍이 안 잡혀 인용 예외가 통째로 풀렸다. ellipsis 표본 20건 가운데 10건이 이 결함이었고
    deixis 와 이중 피동과 사전 규칙도 같은 예외를 쓴다 (2026-08-31).
    """
    doc = build("“네가 탄 곡조는 누구의 것인데? 대단히 듣기 좋던데…”\n")
    assert len(doc.sentences) == 2, "물음표 뒤에서 두 문장으로 잘려야 이 시험이 뜻이 있다"
    assert all(sentence.quoted for sentence in doc.sentences), "잘린 두 조각이 모두 인용 구간을 들어야 한다"
    # 인용 안의 말줄임표는 표기이지 글쓴이의 말끝 흐리기가 아니다
    assert not [finding for finding in runAll(doc, Config()) if finding.rule == "ellipsis"]
