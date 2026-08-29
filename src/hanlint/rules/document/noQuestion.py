from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("noQuestion", mechanism="threshold")
def noQuestion(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """절이 둘 이상인데 물음표가 한 번도 없는 글.

    왜: 물음표가 한 번도 나오지 않는 글은 독자에게 한 번도 말을 걸지 않은 글이다. 독자가 품을 의문을
        대신 묻고 다음 문장에서 답하는 자리가 있어야 읽힌다.
    어디서: 글쓰기 스킬의 사실과 목소리.
    고치기: 독자가 막힐 자리에서 한 번 묻는다. 그럼 파일은 어디에 생겼을까요? 다음 문장이 그 답이다. 독자를
        부르는 말 (열어 봅니다, 확인해 보세요, 바랍니다. 목록은 data/readerCalls.txt) 도 없으면 지적문이 그것까지
        말한다.
    안 잡는 것: 절이 하나뿐인 짧은 참고 문서. 제목의 물음표도 센다. 물음은 없는데 독자 호출은 있는 글도 잡는다
        (물음 한 번은 따로 필요하다). 독자 호출만 세던 readerAbsent 는 이 규칙의 부분집합이라 2026-08-29 본보기
        게이트에서 드러나 여기로 접었다.
    """
    if len(doc.bodySections) < 2 or doc.questionCount > 0:
        return
    first = doc.sentences[0] if doc.sentences else None
    why = "물음표가 한 번도 없다. 독자가 품을 의문을 한 번은 대신 묻고 다음 문장에서 답한다"
    if doc.readerCallCount == 0:
        why = (
            "물음표가 한 번도 없고 독자를 부르는 말도 없다. "
            "독자가 품을 의문을 한 번은 대신 묻고, 독자가 할 행동을 동사로 끝내는 문장을 넣는다"
        )
    yield Finding(
        "noQuestion",
        first.line if first else 1,
        first.text if first else "",
        why,
        None,
        "error",
        DOCUMENT,
        -1,
    )
