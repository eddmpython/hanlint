"""분석 층의 넷. 문장 분리, 의 의 자리, 명사 어절 연속, 이중 피동의 표층형."""

from __future__ import annotations

from hanlint.analysis import doublePassives, euiAdjacent, euiCount, longestNounRun, splitSentences


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


def testEuiCount():
    assert euiCount("사용자의 요구에 대한 개발자의 답변이다.") == 2
    assert euiCount("의미가 있는 의사 결정이다.") == 0
    assert euiCount("사용자의 요구를 개발자가 답한다.") == 1
    # 영문, 숫자, 닫는 괄호 뒤의 의 도 관형격이다. 실측: 말뭉치에서 형태소 분석기와 갈리던 자리 (2026-08-29)
    assert euiCount("파드의 컨테이너에 256MiB의 메모리 요청량과 API의 응답이 있다.") == 3
    assert euiCount("L7(HTTP)의 보안 정책과 여러 대의 서버를 본다.") == 2


def testEuiAdjacent():
    assert euiAdjacent("회사의 팀의 결정이다.")
    assert not euiAdjacent("회사의 결정과 팀의 의견이다.")
    # 정의 는 의 로 끝나는 명사라 앞 어절이 될 수 없다
    assert not euiAdjacent("사용자 정의 리소스의 컨트롤러 역할을 하는 API의 클라이언트다.")


def testLongestNounRun():
    assert longestNounRun("가상환경 생성 후 패키지 설치 확인 절차를 따른다.") >= 5
    assert longestNounRun("파이썬 데이터프레임 라이브러리 여섯 가지를 소개한다.") < 5
    assert longestNounRun("가상환경을 만든 뒤 패키지가 설치됐는지 확인한다.") < 5
    assert longestNounRun("순서는 pandas, Polars, DuckDB, PyArrow, Dask, Ibis 이고 뒤로 갈수록") < 5


def testQuantitiesAdverbsAndCopulaDoNotPile():
    # 실측: 말뭉치 390편에서 표층만 명사 다섯으로 본 63문장의 세 부류 (2026-08-29)
    assert (
        longestNounRun("2012년 11월 29일 4시에 발사가 예정되었던 나로호는 발사 전 16분 즈음인 오후 3시 44분경 이상이 감지되었다.")
        < 5
    )
    assert longestNounRun("성능 저하 및 클러스터 안정성 저하로 이어질 수 있었습니다.") < 5
    assert longestNounRun("쿠버네티스 커맨드 라인 도구인 kubectl 을 사용한다.") < 5
    assert longestNounRun("외국인 노동자 채용 절차 안내 문서를 읽는다.") >= 5
    assert longestNounRun("파드를 삭제하면 바인딩 되어있던 서비스 어카운트 토큰 역시 만료된다.") < 5


def testDoublePassives():
    assert doublePassives("이 값은 자동으로 되어진다.") == ["되어지"]
    assert doublePassives("문제가 보여진다.") == ["보여지"]
    assert doublePassives("그 이름은 잊혀진 지 오래다.") == ["잊혀지"]
    assert doublePassives("파일이 만들어진다.") == []
    assert doublePassives("문제가 보인다.") == []
