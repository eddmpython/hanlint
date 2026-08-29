from __future__ import annotations

import re
from collections.abc import Iterator
from functools import cache

from ...config import Config
from ...data import loadLines
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule
from ..shared import codeBlocksOf


@cache
def platformApis() -> tuple[tuple[re.Pattern[str], str, str], ...]:
    found = []
    for line in loadLines("platformApis.txt"):
        pattern, platform, alternative = line.split("\t")
        found.append((re.compile(pattern), platform, alternative))
    return tuple(found)


@rule("platformApi", mechanism="dictionary")
def platformApi(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """한 운영체제에서만 도는 API 나 경로를 쓴 코드.

    왜: 다른 운영체제 독자는 답까지 다 구해 놓고 그 줄에서 AttributeError 로 멈춘다. 글쓴이 컴퓨터에서는 돌아서
        글쓴이는 모른다.
    어디서: 실측. 블로그 004 의 peak_wset 이 윈도우에서만 나와 사람 평가자가 집었다. 목록은 data/platformApis.txt.
    고치기: 그 줄이 어느 운영체제 전용인지 적고 대안을 준다. 또는 이식 가능한 API 로 바꾼다.
    안 잡는 것: 목록에 없는 API. 산문 안의 언급. notice 로만 낸다.
    """
    for block in codeBlocksOf(doc):
        if block.isOutput:
            continue
        for line, code in block.lines:
            for pattern, platform, alternative in platformApis():
                if pattern.search(code):
                    yield Finding(
                        "platformApi",
                        line,
                        code.strip(),
                        f"`{pattern.pattern}` 은 {platform} 전용이다. 다른 운영체제 독자는 여기서 멈춘다. {alternative}",
                        None,
                        NOTICE,
                        DOCUMENT,
                        block.index,
                    )
                    break
