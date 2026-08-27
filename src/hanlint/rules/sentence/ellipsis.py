from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule

# 괄호 안의 점 셋 (`OVER (...)`, `EXTRACT(month FROM ...)`) 은 인라인 코드의 생략 표기라 뺀다.
ELLIPSIS = re.compile(r"(?<![(\[])(…|\.{3,})(?![)\]])")


@rule("ellipsis")
def ellipsis(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """말줄임표.

    왜: 말끝을 흐리면 독자가 결론을 받아 가지 못한다. 설명글의 독자는 답을 찾으러 왔다.
    어디서: 글쓰기 스킬의 사실과 목소리.
    고치기: 문장을 끝까지 쓴다. 모르면 모른다고 쓴다.
    안 잡는 것: 코드 블록 안의 점 셋. 괄호 안의 점 셋 (인라인 코드의 생략 표기). 산문만 본다.
    """
    for sentence in doc.sentences:
        if ELLIPSIS.search(sentence.text):
            yield Finding(
                "ellipsis",
                sentence.line,
                sentence.text,
                "말줄임표로 말끝을 흐리면 독자가 결론을 받아 가지 못한다. 문장을 끝까지 쓴다",
                None,
                "error",
                SENTENCE,
                sentence.index,
            )
