from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule


@rule("promiseRecall", mechanism="contrast")
def promiseRecall(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """뒤에서 다루겠습니다 라고 미뤄 놓고 앞에서 미룬 것을 부르는 표지가 글 어디에도 없는 것.

    왜: 뒤에서 다루겠습니다 를 써 놓고 끝까지 안 나오면 정보 배분이 아니라 누락이다. 회수할 때는 미뤘다는
        사실을 밝히고 앞에서 쓴 이름을 다시 부른다.
    어디서: 글쓰기 스킬의 무엇을 빼는가 (미룬 것은 같은 글 안에서 회수한다). 이런 검사를 하는 선행 도구가
        없다 (조사 결과). 표지 목록은 data/promiseMarkers.txt 와 recallMarkers.txt.
    고치기: 뒤 절에서 앞에서 미룬 X 로 부르며 다룬다. 회수하지 못할 것은 애초에 미루지 말고 지운다.
    안 잡는 것: 회수 표지가 하나라도 있는 글. 어느 약속을 어느 회수가 갚았는지는 대조하지 않는다.
        표지 근사라 notice 로만 낸다.
    """
    if not doc.promises or doc.recalls:
        return
    for line, text in doc.promises:
        yield Finding(
            "promiseRecall",
            line,
            text,
            "뒤로 미룬 것을 앞에서 미룬 것으로 다시 부르는 자리가 글 어디에도 없다. 회수하거나 미루지 않는다",
            None,
            NOTICE,
            DOCUMENT,
            -1,
        )
