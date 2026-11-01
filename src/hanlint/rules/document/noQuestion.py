from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("noQuestion", mechanism="threshold")
def noQuestion(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """절이 둘 이상인데 물음표가 한 번도 없는 글.

    왜: 물음표가 없다는 것은 관찰한 사실일 뿐 잘못이라는 뜻이 아니다. 질문 없이 설명하는 글도 바른 글이므로 기본은
        확인 권고다. 질문을 요구하는 사용자가 설정 enforceStyle에 이 규칙을 넣었을 때만 오류로 낸다.
    어디서: 독자가 품을 물음을 글이 먼저 묻고 답한다는 쓰기 방식에서 왔다.
    고치기: 설명만으로 충분하면 그대로 둔다. 질문이 필요한 곳에서만 독자의 의문을 묻고 다음 문장으로 답한다.
        물음표를 넣으려고 이미 분명한 문장을 바꾸지 않는다.
    안 잡는 것: 절이 하나뿐인 짧은 참고 문서는 잡지 않는다. 제목의 물음표도 센다. 물음은 없는데 독자에게 말을 거는
        문장은 있는 글도 잡는다(질문을 쓸지는 사람이 판단한다). 독자에게 말을 거는 문장만 세던 규칙 readerAbsent는 이
        규칙이 잡는 것에 모두 들어 있어 이 규칙으로 합쳤다.
    """
    if len(doc.bodySections) < 2 or doc.questionCount > 0:
        return
    first = doc.sentences[0] if doc.sentences else None
    why = "물음표가 한 번도 없다. 질문이 필요한 글인지 판단하고, 설명만으로 충분하면 그대로 둔다"
    if doc.readerCallCount == 0:
        why = (
            "물음표가 한 번도 없고 독자에게 말을 거는 문장도 없다. 질문이나 독자에게 말을 거는 문장이 필요한 글인지 "
            "판단하고, 설명만으로 충분하면 그대로 둔다"
        )
    yield Finding(
        "noQuestion",
        first.line if first else 1,
        first.text if first else "",
        why,
        None,
        "error" if "noQuestion" in config.enforceStyle else "notice",
        DOCUMENT,
        -1,
    )
