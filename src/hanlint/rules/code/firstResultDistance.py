from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...document.model import CODE, IMAGE, TABLE
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, PARAGRAPH, Finding
from ..registry import rule

RESULT_KINDS = (CODE, IMAGE, TABLE)


@rule("firstResultDistance", mechanism="threshold")
def firstResultDistance(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """첫 코드나 표나 그림이 나오기 전에 산문 문단이 4개를 넘는 글.

    왜: 따라 하러 온 독자는 실행할 것이 나올 때까지 배경을 읽는다. 문단이 넷을 넘으면 읽다가 떠난다.
    어디서: 실제 블로그 글 하나에서 셋째 문단까지 숫자가 하나도 없어 사람 평가자가 짚었다. 도입은 독자가 막힌 데서
        시작하고 첫 코드 블록이 도입 안에 온다는 쓰기 방식에서 왔다. 기준값은 설정 firstResultMaxParagraphs(기본 4)다.
    고치기: 첫 실행할 것을 앞으로 당기거나 그 앞의 문단을 뒤로 보낸다.
    안 잡는 것: 코드도 표도 그림도 없는 글(참고 문서)은 잡지 않는다. introLong이 도입만 보는 것과 달리 이 규칙은 절을
        넘어 센다. 확인 권고로만 낸다.
    """
    firstResult = next((b for b in doc.blocks if b.kind in RESULT_KINDS), None)
    if firstResult is None:
        return
    before = [p for p in doc.paragraphs if p.startLine < firstResult.startLine]
    if len(before) > config.firstResultMaxParagraphs:
        over = before[config.firstResultMaxParagraphs]
        yield Finding(
            "firstResultDistance",
            over.startLine,
            over.sentences[0].text if over.sentences else "",
            f"첫 코드나 표까지 산문 문단이 {len(before)}개다. {config.firstResultMaxParagraphs}개 안에 실행할 것이 온다",
            None,
            NOTICE,
            PARAGRAPH,
            over.index,
        )
