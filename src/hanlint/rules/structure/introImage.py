from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...document.model import IMAGE
from ...fingerprint import DocumentPrint
from ..finding import SECTION, Finding
from ..registry import rule


@rule("introImage", mechanism="threshold")
def introImage(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """도입에 그림이 introMaxImages 보다 많은 글.

    왜: 도입은 독자를 첫 결과로 데려가는 구간이다. 그림이 쌓이면 스크롤이 길어지고, 실행할 수 있는 것이
        첫 화면 밖으로 밀려난다. 도입에서 밀린 독자는 본문을 안 읽는다.
    어디서: cinch 의 전역 blog-writing 스킬, 도입은 결핍부터. 도입은 문단 넷과 이미지 한 장을 넘지 않는다.
        introLong 이 문단만 세므로 그림은 이 규칙이 센다. 임계는 config.introMaxImages.
    고치기: 넘치는 그림을 그것이 설명하는 본문 절로 내린다. 대표 그림 한 장만 도입에 둔다.
    안 잡는 것: H2 가 없는 글 (전체가 도입이라 셀 수 없다). 본문 절의 그림 수는 세지 않는다.
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
