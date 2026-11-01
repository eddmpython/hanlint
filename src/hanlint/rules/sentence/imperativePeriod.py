from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule

IMPERATIVE_PERIOD = re.compile(r"(세요|십시오|합시다|봅시다|하자|해라|라)\.(?=\s|$)")


@rule("imperativePeriod", mechanism="dictionary")
def imperativePeriod(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """명령형과 청유형 뒤의 마침표.

    왜: 한글 맞춤법은 명령·청유 문장 끝에도 마침표를 쓴다. 이 규칙은 `세요`, `십시오`, `합시다`, `해라`를 마침표
        없이 끝내는 블로그 표기 방침이다. 한 글 안에서 기준이 갈리면 독자가 부호를 읽느라 멈춘다. blog와 guide
        프리셋에서만 켜고, 다른 종류의 글은 enforceStyle에 넣어 켠다.
    어디서: 블로그 글쓰기 방침. eddmpython의 발행 검사가 같은 규칙을 정규식으로 막는다.
    고치기: 마침표를 지운다. `hanlint fix`가 고친다.
    안 잡는 것: 평서형 뒤의 마침표. 따옴표 안의 명령문은 문장 부호 규칙이 달라 보지 않는다.
    """
    for sentence in doc.sentences:
        match = IMPERATIVE_PERIOD.search(sentence.text)
        if not match:
            continue
        yield Finding(
            "imperativePeriod",
            sentence.line,
            sentence.text,
            f"명령·청유 문장 끝(`{match.group(1)}`)에 마침표를 붙이지 않는 표기 방침이다",
            sentence.text[: match.start()] + match.group(1) + sentence.text[match.end() :],
            "error",
            SENTENCE,
            sentence.index,
            match.group(0),
            match.group(1),
        )
