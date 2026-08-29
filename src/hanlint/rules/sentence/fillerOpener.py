from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule

FILLER = re.compile(r"^(다음으로|이어서|마지막에는|마지막으로)(?=[\s,])")


@rule("fillerOpener", mechanism="dictionary")
def fillerOpener(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """다음으로, 이어서, 마지막에는 으로만 잇는 문장.

    왜: 앞에서 무엇을 만들었는지 부르지 않고 순서 표지만 붙이면 독자는 무엇을 이어받는지 모른 채 다음
        행동을 읽는다.
    어디서: 글쓰기 스킬의 쉬운 말로 바로 쓰기.
    고치기: 앞 절에서 만든 파일이나 확인한 값을 이름으로 다시 부르고 다음 행동을 붙인다. link.png 는
        33픽셀입니다. 명함에 넣기에는 너무 작습니다.
    안 잡는 것: 문장 중간의 이어서. 목록 항목.
    """
    for sentence in doc.sentences:
        match = FILLER.match(sentence.text)
        if not match:
            continue
        yield Finding(
            "fillerOpener",
            sentence.line,
            sentence.text,
            f"`{match.group(1)}` 만 붙여 잇는 문장이다. 앞에서 만든 파일이나 값을 이름으로 다시 부르고 다음 행동을 붙인다",
            None,
            "error",
            SENTENCE,
            sentence.index,
        )
