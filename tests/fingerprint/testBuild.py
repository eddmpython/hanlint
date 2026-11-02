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
    # 화면 사전 (screen*) 은 인용 밖의 종결어미 `니다.` 를 정당하게 짚는다. 인용 안 상투어가 빠졌는지만 본다.
    assert [m for m in first.matches if not m.dictionary.startswith("screen")] == [] and len(first.quoted) == 2
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


def spacingMatches(text: str, config: Config | None = None) -> list[str]:
    return [m.text for s in build(text, config).sentences for m in s.matches if m.dictionary == "spacing"]


def testProtectedTermsDropOverlappingMatches():
    """protectedTerms 와 한 글자라도 겹치는 사전 매치는 지문에 넣지 않는다. 겹치지 않는 자리는 그대로 남는다."""
    text = "할수있어 앱은 볼수 없습니다.\n"
    assert spacingMatches(text) == ["할수있", "볼수 없"]
    assert spacingMatches(text, Config(protectedTerms=["할수있어"])) == ["볼수 없"]
    assert spacingMatches(text, Config(protectedTerms=["있어 앱"])) == ["볼수 없"]
    assert spacingMatches(text, Config(protectedTerms=["앱은"])) == ["할수있", "볼수 없"]


def testProtectedTermsSilenceAProjectEntryOnTheTerm():
    """돈값의 실측: protectedTerms 에 물때 를 넣어도 물때 를 짚던 자리. 항목이 무엇이든 보호한 용어 위에서는 짚지 않는다."""
    config = Config(dictionary={"spacing": [{"pattern": "물때", "fix": "물 때"}]})
    assert spacingMatches("물때는 사리 전후가 좋습니다.\n", config) == ["물때"]
    config.protectedTerms = ["물때"]
    assert spacingMatches("물때는 사리 전후가 좋습니다.\n", config) == []


def testUnlessSkipsTheEntryInThatSentenceOnly():
    """unless 가 문장 어디에든 맞으면 그 문장에서 항목이 맞지 않는다. 다른 문장은 그대로 본다."""
    config = Config(dictionary={"calqueFrame": [{"pattern": "맡겼", "unless": "(?:에게|한테)(?![가-힣])"}]})
    doc = build("발행을 맡겼습니다. 블로그팀에게 발행을 맡겼습니다.\n", config)
    found = [[m.text for m in s.matches if m.dictionary == "calqueFrame" and not m.pattern] for s in doc.sentences]
    assert found == [["맡겼"], []]


def testKeepSkipsOnlyTheOverlappingSpan():
    """keep에 맞은 곳과 겹치는 매치만 빠진다. 같은 문장의 다른 곳은 그대로 맞는다(unless는 문장 전체를 뺀다)."""
    entry = {"pattern": "자리", "keep": "그 자리에서|자리가 나", "candidates": ["위치"]}
    doc = build("그 자리에서 커서 자리를 고칩니다. 대기열에 자리가 나면 넣습니다.\n", Config(dictionary={"calqueFrame": [entry]}))
    found = [
        [(m.text, m.start, m.candidates) for m in s.matches if m.dictionary == "calqueFrame" and not m.pattern]
        for s in doc.sentences
    ]
    assert found == [[("자리", 10, ("위치",))], []]


def testDictionaryReadsListTableHeadingAndImageText():
    """사전은 목록 항목, 표 칸, 제목, 그림 설명 글도 한 줄(칸)씩 본다. 인용 블록과 인라인 코드는 보지 않는다. 그 줄은
    문장 목록에 들지 않고 index가 -1이다(2026-11-02, 캡션의 목록 줄 `2. ○○ : 항구 안쪽`이 사전 규칙을 지나갔다)."""
    config = Config(dictionary={"calqueFrame": [{"pattern": "자리"}]})
    text = (
        "## 위험한 자리\n\n- 서는 자리 보기\n1. 둘째 **자리**\n\n| 칸 | 값 |\n|---|---|\n| 심볼 자리 | `코드 자리` |\n\n"
        "![구조함 자리](a.png)\n\n> 인용 자리\n"
    )
    doc = build(text, config)
    hits = [
        (f.line, f.index, f.text)
        for f in doc.fragments
        if any(m.dictionary == "calqueFrame" and not m.pattern for m in f.matches)
    ]
    assert hits == [
        (1, -1, "위험한 자리"),
        (3, -1, "서는 자리 보기"),
        (4, -1, "둘째 자리"),
        (8, -1, "심볼 자리"),
        (10, -1, "구조함 자리"),
    ]
    assert doc.sentences == ()


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
