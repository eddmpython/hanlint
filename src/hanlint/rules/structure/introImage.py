from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...document.model import IMAGE
from ...fingerprint import DocumentPrint
from ..finding import SECTION, Finding
from ..registry import rule


@rule("introImage", mechanism="threshold")
def introImage(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """도입에 그림이 한 장을 넘는 글.

    왜: 도입은 독자를 첫 결과로 데려가는 부분이다. 그림이 쌓이면 스크롤이 길어지고, 실행할 수 있는 것이 첫 화면
        밖으로 밀려난다. 도입에서 첫 결과를 보지 못한 독자는 본문을 읽지 않고 떠난다.
    어디서: 도입은 독자가 막힌 데서 시작하고 문단 넷과 그림 한 장을 넘지 않는다는 블로그 쓰기 방식에서 왔다.
        introLong이 문단만 세므로 그림은 이 규칙이 센다. 기준값은 설정 introMaxImages(기본 1)다.
    고치기: 넘치는 그림을 그것이 설명하는 본문 절로 내린다. 대표 그림 한 장만 도입에 둔다.
    안 잡는 것: H2가 없는 글(전체가 도입이라 셀 수 없다)은 잡지 않는다. 본문 절의 그림 수는 세지 않는다.
    """
    if not doc.bodySections:
        return
    count = doc.intro.count(IMAGE)
    if count <= config.introMaxImages:
        return
    yield Finding(
        "introImage",
        doc.intro.startLine,
        doc.intro.title or "도입",
        f"도입에 그림이 {count}장이다. {config.introMaxImages}장을 넘지 않는다. 나머지는 그것을 설명하는 절로 내린다",
        None,
        "error",
        SECTION,
        doc.intro.index,
    )
