from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule


@rule("promiseRecall", mechanism="reader")
def promiseRecall(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """`뒤에서 다루겠습니다`라고 미뤄 놓고, 미룬 이야기를 다시 부르는 말이 글 어디에도 없는 것.

    왜: `뒤에서 다루겠습니다`를 써 놓고 끝까지 안 나오면 나눠 설명한 것이 아니라 빠뜨린 것이다. 미룬 이야기를
        다시 다룰 때는 미뤘다는 사실을 밝히고 앞에서 쓴 이름을 다시 부른다.
    어디서: 미룬 이야기는 같은 글 안에서 다시 다룬다는 블로그 쓰기 방식에서 왔다. 이런 검사를 하는 다른 도구는
        찾지 못했다. 찾는 말 목록은 data/promiseMarkers.txt와 data/recallMarkers.txt에 있다. 미루는 말과 다시
        부르는 말은 글을 문장 순서대로 읽으며 모으고, 글을 끝까지 읽은 뒤에 따진다.
    고치기: 뒤 절에서 `앞에서 미룬 X`라고 부르며 다룬다. 다시 다루지 못할 것은 처음부터 미루지 말고 지운다.
    안 잡는 것: 다시 부르는 말이 하나라도 있는 글은 잡지 않는다. 어느 약속을 어느 말이 다시 다뤘는지는 맞춰 보지
        않는다. 찾는 말 목록으로 어림하는 규칙이라 확인 권고로만 낸다.
    """
    reader = doc.reader.final
    if not reader.promises or reader.recalls:
        return
    for line, text in reader.promises:
        yield Finding(
            "promiseRecall",
            line,
            text,
            "뒤로 미룬 이야기를 `앞에서 미룬 X`처럼 다시 부르는 문장이 글 어디에도 없다. 뒤에서 다루거나 처음부터 미루지 않는다",
            None,
            NOTICE,
            DOCUMENT,
            -1,
        )
