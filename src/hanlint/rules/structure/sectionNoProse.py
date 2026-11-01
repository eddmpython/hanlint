from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...document.model import LIST, PROSE
from ...fingerprint import DocumentPrint
from ..finding import SECTION, Finding
from ..registry import rule


@rule("sectionNoProse", mechanism="threshold")
def sectionNoProse(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """설명글 없이 코드, 표, 이미지만 있는 절.

    왜: 절은 제목, 시각 자료, 설명글, 그리고 설명을 돕는 예시로 짠다. 코드와 표만 쌓인 절에서는 독자가 무엇을
        보는지 모른다.
    어디서: 절은 제목, 소제목, 시각 자료, 설명글, 예시로 짠다는, 글을 검토한 사람이 정한 규칙이다.
    고치기: 코드가 하는 일을 한 문장으로 먼저 말하고 그다음에 이름을 하나씩 푼다.
    안 잡는 것: 목록만 있는 절(`더 해 볼 것`)은 목록 안에 설명이 들어 있으므로 잡지 않는다. 빈 절도 잡지 않는다.
    """
    for section in doc.bodySections:
        kinds = set(section.blockKinds)
        if not kinds or PROSE in kinds or LIST in kinds:
            continue
        yield Finding(
            "sectionNoProse",
            section.startLine,
            section.title,
            "설명글 없이 코드, 표, 이미지만 있는 절이다. 절은 제목과 시각 자료와 설명글로 짠다",
            None,
            "error",
            SECTION,
            section.index,
        )
