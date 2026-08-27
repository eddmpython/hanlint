from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import PARAGRAPH, Finding
from ..registry import rule


@rule("introLong")
def introLong(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """첫 H2 앞의 산문 문단이 introMaxParagraphs 를 넘는 도입.

    왜: 도입은 문단 넷과 이미지 한 장을 넘지 않는다. 첫 코드 블록이나 실행할 수 있는 것이 그 안에 와야
        한다. 결핍 문단이 길어지면 그것 자체가 미룬 배경 설명이 된다.
    어디서: 글쓰기 스킬의 도입은 결핍부터. 임계는 config.introMaxParagraphs.
    고치기: 넘치는 문단을 첫 절로 내리거나 지운다. 정의 문단이면 지운다. 검색해 들어온 독자는 그것이
        무엇인지 이미 안다.
    안 잡는 것: H2 가 없는 글. 전체가 도입이라 셀 수 없다.
    """
    if not doc.bodySections:
        return
    paragraphs = doc.intro.paragraphs
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
