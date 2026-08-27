from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("noQuestion")
def noQuestion(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """절이 둘 이상인데 물음표가 한 번도 없는 글.

    왜: 물음표가 한 번도 나오지 않는 글은 독자에게 한 번도 말을 걸지 않은 글이다. 독자가 품을 의문을
        대신 묻고 다음 문장에서 답하는 자리가 있어야 읽힌다.
    어디서: 글쓰기 스킬의 사실과 목소리.
    고치기: 독자가 막힐 자리에서 한 번 묻는다. 그럼 파일은 어디에 생겼을까요? 다음 문장이 그 답이다.
    안 잡는 것: 절이 하나뿐인 짧은 참고 문서. 제목의 물음표도 센다.
    """
    if len(doc.bodySections) < 2 or doc.questionCount > 0:
        return
    first = doc.sentences[0] if doc.sentences else None
    yield Finding(
        "noQuestion",
        first.line if first else 1,
        first.text if first else "",
        "물음표가 한 번도 없다. 독자가 품을 의문을 한 번은 대신 묻고 다음 문장에서 답한다",
        None,
        "error",
        DOCUMENT,
        -1,
    )
