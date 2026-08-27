"""두 분석기가 같은 인터페이스에서 같은 판정을 내는지. kiwi 는 설치됐을 때만 돈다."""

from __future__ import annotations

import pytest

from hanlint.analysis import SurfaceAnalyzer, makeAnalyzer
from hanlint.analysis.surface.splitSentences import splitSentences


def analyzers():
    yield SurfaceAnalyzer()
    try:
        import kiwipiepy  # noqa: F401
    except ImportError:
        return
    yield makeAnalyzer("kiwi")


@pytest.fixture(params=list(analyzers()), ids=lambda a: a.name)
def analyzer(request):
    return request.param


def testSplitsOnTerminalPunctuation():
    text = "첫 문장입니다. 둘째 문장이죠! 셋째는 물음표로 끝날까요? 넷째"
    sentences = splitSentences(text)
    assert [s.text for s in sentences] == ["첫 문장입니다.", "둘째 문장이죠!", "셋째는 물음표로 끝날까요?", "넷째"]
    assert [text[s.start : s.end] for s in sentences] == [s.text for s in sentences]


def testKeepsQuotedPeriodAndAbbreviation():
    assert [s.text for s in splitSentences('그는 "안녕." 하고 말했다. 다음 문장.')] == ['그는 "안녕." 하고 말했다.', "다음 문장."]
    assert [s.text for s in splitSentences("예: e.g. 이런 것. 다음.")] == ["예: e.g. 이런 것.", "다음."]
    assert [s.text for s in splitSentences("값은 3.5 초다. 다음.")] == ["값은 3.5 초다.", "다음."]


def testOffsetsSurviveNewlines():
    text = "첫 줄의 문장.\n둘째 줄의 문장."
    sentences = splitSentences(text)
    assert text[sentences[1].start :] == "둘째 줄의 문장."


def testEuiCount(analyzer):
    assert analyzer.euiCount("사용자의 요구에 대한 개발자의 답변이다.") == 2
    assert analyzer.euiCount("의미가 있는 의사 결정이다.") == 0
    assert analyzer.euiCount("사용자의 요구를 개발자가 답한다.") == 1


def testLongestNounRun(analyzer):
    assert analyzer.longestNounRun("가상환경 생성 후 패키지 설치 확인 절차를 따른다.") >= 5
    assert analyzer.longestNounRun("파이썬 데이터프레임 라이브러리 여섯 가지를 소개한다.") < 5
    assert analyzer.longestNounRun("가상환경을 만든 뒤 패키지가 설치됐는지 확인한다.") < 5


def testCommaListIsNotANounPile():
    surface = SurfaceAnalyzer()
    assert surface.longestNounRun("순서는 pandas, Polars, DuckDB, PyArrow, Dask, Ibis 이고 뒤로 갈수록") < 5


def testDoublePassives(analyzer):
    assert analyzer.doublePassives("이 값은 자동으로 되어진다.") == ["되어지"]
    assert analyzer.doublePassives("문제가 보여진다.") == ["보여지"]
    assert analyzer.doublePassives("그 이름은 잊혀진 지 오래다.") == ["잊혀지"]
    assert analyzer.doublePassives("파일이 만들어진다.") == []
    assert analyzer.doublePassives("문제가 보인다.") == []


def testUnknownAnalyzerNameIsAnError():
    with pytest.raises(ValueError):
        makeAnalyzer("mecab")
