from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import PARAGRAPH, Finding
from ..registry import rule


@rule("introLong", mechanism="threshold")
def introLong(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """첫 H2 앞의 산문 문단이 introMaxParagraphs 를 넘는 도입.

    왜: 도입은 문단 넷과 이미지 한 장을 넘지 않는다. 첫 코드 블록이나 실행할 수 있는 것이 그 안에 와야
        한다. 결핍 문단이 길어지면 그것 자체가 미룬 배경 설명이 된다.
    어디서: 글쓰기 스킬의 도입은 결핍부터. 임계는 config.introMaxParagraphs.
    고치기: 넘치는 문단을 첫 절로 내리거나 지운다. 정의 문단이면 지운다. 검색해 들어온 독자는 그것이
        무엇인지 이미 안다.
    안 잡는 것: H2 가 없는 글 (전체가 도입이라 셀 수 없다). **본문 절이 하나뿐인 글과 도입이 문단의
        절반을 넘는 글.** 둘 다 절 구조가 없는 글이지 도입이 긴 글이 아니다. 실측: 위키뉴스 단신은 본문이
        문단 나열이고 끝에 `## 출처` 하나가 붙어 H2 가 하나 있다는 이유로 기사 전체가 도입으로 세어졌다.
        제목 구조가 없는 수필은 도입 문단이 78개였다. 표본 20건의 오탐 11건이 전부 이 꼴이었다 (2026-08-31).
    """
    if len(doc.bodySections) < 2:
        return
    paragraphs = doc.intro.paragraphs
    # 도입이 글의 절반을 넘으면 긴 도입이 아니라 절이 없는 글이다.
    if len(paragraphs) * 2 > len(doc.paragraphs):
        return
    if len(paragraphs) > config.introMaxParagraphs:
        over = paragraphs[config.introMaxParagraphs]
        yield Finding(
            "introLong",
            over.startLine,
            over.sentences[0].text if over.sentences else "",
            f"도입 산문 문단이 {len(paragraphs)}개다. {config.introMaxParagraphs}개를 넘지 않는다. 첫 코드 블록이 그 안에 온다",
            None,
            "error",
            PARAGRAPH,
            over.index,
        )
