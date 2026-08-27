from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint, ParagraphPrint
from ..finding import NOTICE, PARAGRAPH, Finding
from ..registry import rule


def isLinked(paragraph: ParagraphPrint) -> bool:
    """문장 사이를 잇는 표지가 하나라도 있는가. 인과 표지, 문두 접속사, 질문, 독자 호출."""
    if paragraph.causalTotal > 0:
        return True
    return any(s.connectorStart or s.mood == "의문" or s.readerCall for s in paragraph.sentences)


@rule("factListParagraph")
def factListParagraph(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """짧은 평서문 셋 이상이 잇는 말 없이 이어지는 문단.

    왜: 쉬운 낱말을 골라도 사실만 나란히 놓으면 읽히지 않는다. 독자는 낱말이 아니라 문장 사이의 이유를
        못 따라가서 멈춘다. 병합 셀은 첫 칸에만 값이 있습니다. 나머지 칸은 빈값입니다. 정렬하면 순서가
        깨집니다 는 세 문장의 관계를 독자가 세워야 한다.
    어디서: 글쓰기 스킬의 설명을 풀어 쓰기. 지문 계층이 처음 가능하게 한 규칙이다. 인과 표지 목록은
        data/causalMarkers.txt, 문두 접속사는 data/connectors.txt. 최소 문장 수는 config.factListMinSentences,
        평균 어절 상한은 config.factListMaxMeanLength.
    고치기: 문장 사이에 그래서, 때문에, 그러면 을 넣어 잇는다. 풀어 쓰면 원고는 길어지는 것이 정상이다.
    안 잡는 것: 두 문장 이하 문단. 인과 표지, 하지만, 그런데 같은 문두 접속사, 질문, 독자 호출이 하나라도
        든 문단. 평균 어절이 상한을 넘는 문단 (긴 문장은 조건과 이유를 안에 품고 있다). 실측: 004 에서
        표지만 보면 문단의 40% 가 잡혔고 읽어 보니 대부분 긴 설명문이었다. 짧고 끊기는 꼴만 남겼다. 그래도
        나열이 아닐 수 있어 notice 로만 낸다.
    """
    for paragraph in doc.paragraphs:
        if paragraph.sentenceCount < config.factListMinSentences or isLinked(paragraph):
            continue
        if paragraph.meanLength <= config.factListMaxMeanLength:
            yield Finding(
                "factListParagraph",
                paragraph.startLine,
                paragraph.sentences[0].text,
                f"문장 {paragraph.sentenceCount}개에 인과 표지가 하나도 없다. 사실만 나열한 문단일 수 있다. "
                "그래서, 때문에 로 잇는다",
                None,
                NOTICE,
                PARAGRAPH,
                paragraph.index,
            )
