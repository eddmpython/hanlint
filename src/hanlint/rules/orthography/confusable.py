from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("confusable")
def confusable(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """학생으로써, 정답을 맞추다, 나와 틀리다, 감기가 낳다 처럼 뜻이 다른 말을 바꿔 쓴 자리.

    왜: 로서/로써, 맞히다/맞추다, 다르다/틀리다, 낫다/낳다 는 소리가 같거나 비슷해 뜻이 바뀐 줄 모르고 쓴다.
        독자는 뜻으로 읽다가 걸린다.
    어디서: 국립국어원 한글 맞춤법 제57항 (구별하여 적는 말), 온라인가나다 298340, 표준국어대사전 뜻풀이.
        앞뒤 낱말로 뜻이 확정되는 자리만 사전에 뒀다 (data/confusable.toml).
    고치기: 항목마다 바른 말을 fix 로 낸다. 활용이 바뀌는 것 (틀려→달라, 낳은→나은) 은 활용까지 바꾼다.
    안 잡는 것: 앞뒤 낱말로 확정되지 않는 자리. 이로써, 그것과 다르다 처럼 이미 맞는 것. 백틱과 따옴표 안의 인용.
    """
    yield from dictionaryFindings(doc, "confusable", "confusable")
