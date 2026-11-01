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


@rule("factListParagraph", mechanism="threshold")
def factListParagraph(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """짧은 평서문 셋 이상이 접속사 없이 이어지는 문단.

    왜: 쉬운 단어를 골라도 사실만 나란히 놓으면 읽히지 않는다. 독자는 단어가 아니라 문장 사이의 까닭을 못
        따라가서 멈춘다. `병합 셀은 첫 칸에만 값이 있습니다. 나머지 칸은 빈값입니다. 정렬하면 순서가 깨집니다.`는
        세 문장의 관계를 독자가 세워야 한다.
    어디서: 설명을 풀어 쓴다는 블로그 쓰기 방식에서 왔다. 인과 접속사 목록은 data/causalMarkers.txt, 문장
        첫머리 접속사 목록은 data/connectors.txt에 있다. 최소 문장 수는 설정 factListMinSentences(기본 3), 평균
        어절 수의 상한은 설정 factListMaxMeanLength(기본 8)다.
    고치기: 문장 사이에 `그래서`, `때문에`, `그러면`을 넣어 잇는다. 풀어 쓰면 글이 길어지는 것이 정상이다.
    안 잡는 것: 두 문장 이하인 문단은 잡지 않는다. 인과 접속사, `하지만`이나 `그런데` 같은 문장 첫머리 접속사,
        질문, 독자에게 말을 거는 문장이 하나라도 든 문단도 잡지 않는다. 평균 어절 수가 상한을 넘는 문단도 잡지
        않는다(긴 문장은 조건과 이유를 안에 품고 있다). 실제 글 하나에서 접속사만 보자 문단의 40%가 잡혔고, 읽어
        보니 대부분 긴 설명문이었다. 그래서 짧은 문장이 끊겨 이어지는 문단만 잡는다. 그래도 나열이 아닐 수 있어
        경고로만 낸다.
    """
    for paragraph in doc.paragraphs:
        if paragraph.sentenceCount < config.factListMinSentences or isLinked(paragraph):
            continue
        if paragraph.meanLength <= config.factListMaxMeanLength:
            yield Finding(
                "factListParagraph",
                paragraph.startLine,
                paragraph.sentences[0].text,
                f"문장 {paragraph.sentenceCount}개에 인과 접속사가 하나도 없다. 사실만 나열한 문단일 수 있다. "
                "`그래서`, `때문에`로 잇는다",
                None,
                NOTICE,
                PARAGRAPH,
                paragraph.index,
            )
