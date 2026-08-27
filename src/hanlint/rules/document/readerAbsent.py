from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule


@rule("readerAbsent")
def readerAbsent(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """의문문도 독자를 부르는 문장도 하나 없는 글.

    왜: 독자가 있는 글에는 독자를 부르는 자리가 있다. 열어 봅니다, 확인해 보세요 처럼 다음 손을 지시하는
        문장과 대신 묻는 질문이 전부 없으면 정확해도 읽히지 않는다.
    어디서: 글쓰기 스킬의 사실과 목소리 (직접 시킨다). 지문의 독자 호출 표지는 data/readerCalls.txt 와
        명령형 종결.
    고치기: 독자가 할 행동을 동사로 끝낸다. 할 수 있습니다 대신 열어 봅니다.
    안 잡는 것: 절이 하나뿐인 글. 표지 목록이 거칠어 notice 로만 낸다.
    """
    if len(doc.bodySections) < 2 or doc.questionCount > 0 or doc.readerCallCount > 0:
        return
    first = doc.sentences[0] if doc.sentences else None
    yield Finding(
        "readerAbsent",
        first.line if first else 1,
        first.text if first else "",
        "질문도 독자를 부르는 문장도 없다. 독자가 할 행동을 동사로 끝내는 문장을 한 번은 넣는다",
        None,
        NOTICE,
        DOCUMENT,
        -1,
    )
