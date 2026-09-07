from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("noQuestion", mechanism="threshold")
def noQuestion(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """절이 둘 이상인데 물음표가 한 번도 없는 글.

    왜: 물음표 부재는 관찰이지 결함의 확정이 아니다. 질문 없이 설명하는 글도 정당하므로 기본 notice다.
        질문을 요구하는 사용자의 enforceStyle 정책에서만 error로 낸다.
    어디서: 글쓰기 스킬의 사실과 목소리.
    고치기: 설명만으로 충분하면 유지한다. 질문이 필요한 자리에서만 독자의 의문을 묻고 다음 문장으로 답한다.
        물음표를 넣기 위해 이미 명확한 문장을 바꾸지 않는다.
    안 잡는 것: 절이 하나뿐인 짧은 참고 문서. 제목의 물음표도 센다. 물음은 없는데 독자 호출은 있는 글도 잡는다
        (질문 사용 여부를 사람이 판단한다). 독자 호출만 세던 readerAbsent 는 이 규칙의 부분집합이라 2026-08-29 본보기
        게이트에서 드러나 여기로 접었다.
    """
    if len(doc.bodySections) < 2 or doc.questionCount > 0:
        return
    first = doc.sentences[0] if doc.sentences else None
    why = "물음표가 한 번도 없다. 질문이 필요한 글인지 판단하고 설명만으로 충분하면 유지한다"
    if doc.readerCallCount == 0:
        why = "물음표가 한 번도 없고 독자를 부르는 말도 없다. 질문이나 독자 호출이 필요한 글인지 판단하고 충분하면 유지한다"
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
