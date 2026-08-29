from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("headingSkip", mechanism="threshold")
def headingSkip(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """제목 수준을 건너뛴 자리. H2 다음에 H4 가 오거나 글이 H3 으로 시작하는 것.

    왜: 목차가 계층을 잃는다. 화면 낭독기와 목차 생성기가 건너뛴 수준에서 길을 잃고, 독자는 어느 절
        아래인지 모른다.
    어디서: markdownlint 계열의 헤딩 레벨 검사. Wikipedia Signs of AI writing 4.10 (헤더 남용).
    고치기: 한 수준씩 내려간다. frontmatter 의 title 이 H1 이므로 본문은 H2 부터 시작한다.
    안 잡는 것: 올라가는 것 (H4 다음 H2). 절이 끝나고 새 절이 시작하는 정상 흐름이다.
    """
    previous = 1 if doc.frontmatter.get("title") else None
    for level, text, line in doc.headings:
        if previous is not None and level > previous + 1:
            yield Finding(
                "headingSkip",
                line,
                text,
                f"H{previous} 다음에 H{level} 이 온다. 한 수준씩 내려간다",
                None,
                "error",
                DOCUMENT,
                -1,
            )
        previous = level
